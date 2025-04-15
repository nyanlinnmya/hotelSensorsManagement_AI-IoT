import asyncio
import aio_pika
import json
import logging
from datetime import datetime, timedelta
from collections import deque

from config import ROOM_IDS, EXCHANGES, RABBITMQ_CONFIG
from sensors_subscriber import SensorSubscriber
from database_writer import SupabaseWriter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OccupancyAgent")


class RoomContextManager:
    def __init__(self):
        self.context = {}

    def _init_room(self, room_id):
        if room_id not in self.context:
            self.context[room_id] = {
                "co2_history": deque(maxlen=10),
                "last_presence_state": None,
                "last_presence_time": None,
                "last_occupancy_state": None,
                "last_occupied_time": None
            }

    def update_presence(self, room_id, presence_state, timestamp):
        self._init_room(room_id)
        self.context[room_id]["last_presence_state"] = presence_state
        self.context[room_id]["last_presence_time"] = timestamp
        if presence_state == "occupied":
            self.context[room_id]["last_occupied_time"] = timestamp

    def update_co2(self, room_id, co2_value, timestamp):
        self._init_room(room_id)
        self.context[room_id]["co2_history"].append((timestamp, co2_value))

    def get_co2_slope(self, room_id):
        history = self.context[room_id]["co2_history"]
        if len(history) < 2:
            return 0.0
        (t1, v1), (t2, v2) = history[0], history[-1]
        dt_minutes = (t2 - t1) / 60  # timestamps are in seconds
        if dt_minutes == 0:
            return 0.0
        return (v2 - v1) / dt_minutes

    def get_last_state(self, room_id):
        return self.context[room_id].get("last_occupancy_state", None)

    def set_last_state(self, room_id, state):
        self.context[room_id]["last_occupancy_state"] = state

    def last_presence_seconds_ago(self, room_id, now_ts):
        last = self.context[room_id].get("last_presence_time", None)
        if not last:
            return None
        return now_ts - last


class OccupancyDetectionAgent:
    def __init__(self, occupancy_exchange: aio_pika.Exchange):
        self.exchange = occupancy_exchange
        self.subscriber = SensorSubscriber()
        self.supabase_writer = SupabaseWriter()
        self.context_manager = RoomContextManager()

    def detect_occupancy(self, room_id: str, message: dict) -> bool | None:
        timestamp = message["timestamp"]
        co2 = float(message.get("co2", 0))
        hour = datetime.fromtimestamp(timestamp).hour

        presence_state = message.get("presence_state")

        if presence_state:
            self.context_manager.update_presence(room_id, presence_state, timestamp)

        if "co2" in message:
            self.context_manager.update_co2(room_id, co2, timestamp)

        slope = self.context_manager.get_co2_slope(room_id)
        seconds_since_presence = self.context_manager.last_presence_seconds_ago(room_id, timestamp)
        last_state = self.context_manager.get_last_state(room_id)

        logger.info(
            f"[SensorData] Room={room_id} | Presence={presence_state} | CO₂={co2} | Slope={slope:.2f} | Hour={hour}"
        )

        if presence_state == "occupied":
            decision = True
        elif presence_state == "passive":
            if co2 > 700 or slope > 1.0:
                decision = True
            elif hour >= 22 or hour < 8:
                if co2 > 650:
                    decision = True
                else:
                    decision = last_state
            else:
                decision = last_state
        elif presence_state == "unoccupied":
            if co2 > 800 or slope > 2.0:
                decision = True
            elif co2 < 600 and slope < 0:
                decision = False
            elif seconds_since_presence is not None and seconds_since_presence < 300:
                decision = True
            else:
                decision = last_state
        else:
            decision = last_state

        self.context_manager.set_last_state(room_id, decision)
        return decision

    async def handle_message(self, message: aio_pika.IncomingMessage):
        async with message.process(ignore_processed=True):
            try:
                routing_key = message.routing_key
                logger.info(f"[OccupancyAgent] Received from {routing_key}")
                raw_body = message.body.decode()
                parsed = json.loads(raw_body)

                room_id = parsed.get("room_id")
                sensor_data = parsed.get("data", {})
                sensor_type = routing_key.split(".")[-1]

                mock_method = type("Method", (), {"routing_key": routing_key})
                mock_props = type("Props", (), {})()

                output = self.subscriber.sensor_callback(
                    ch=None,
                    method=mock_method,
                    properties=mock_props,
                    body=json.dumps({
                        "room_id": room_id,
                        "data": sensor_data
                    }).encode()
                )

                if not output:
                    return

                decision = self.detect_occupancy(room_id, output)
                if decision is None:
                    logger.info(f"[OccupancyAgent] No clear decision for {room_id}. Holding last state.")
                    return

                payload = {
                    "room_id": room_id,
                    "timestamp": output["timestamp"],
                    "is_occupied": decision,
                    "datapoint": sensor_type
                }

                await self.exchange.publish(
                    aio_pika.Message(body=json.dumps(payload).encode()),
                    routing_key=f"{room_id}.occupancy"
                )
                logger.info(f"[Publish] Room={room_id} | Occupied={decision} | Source={sensor_type} | Payload={payload}")

                self.supabase_writer.upsert_room_state(
                    room_id=room_id,
                    is_occupied=decision,
                    datapoint=sensor_type,
                    health_status="healthy"
                )

            except Exception as e:
                logger.error(f"[OccupancyAgent] ❌ Error processing message: {e}")


async def main():
    logger.info("[OccupancyAgent] Connecting to RabbitMQ...")

    connection = await aio_pika.connect_robust(
        host=RABBITMQ_CONFIG["host"],
        port=RABBITMQ_CONFIG["port"],
        login=RABBITMQ_CONFIG["user"],
        password=RABBITMQ_CONFIG["password"],
        virtualhost=RABBITMQ_CONFIG["vhost"]
    )

    async with connection:
        channel = await connection.channel()
        logger.info("[OccupancyAgent] ✅ Connected to RabbitMQ.")

        sensor_exchange = await channel.declare_exchange(
            EXCHANGES["sensor_data"], aio_pika.ExchangeType.TOPIC, durable=True
        )
        occupancy_exchange = await channel.declare_exchange(
            EXCHANGES["occupancy"], aio_pika.ExchangeType.TOPIC, durable=True
        )

        agent = OccupancyDetectionAgent(occupancy_exchange)

        for room_id in ROOM_IDS:
            for sensor_type in ["iaq", "presence"]:
                routing_key = f"{room_id}.{sensor_type}"
                queue_name = f"{room_id}_{sensor_type}_occupancy_queue"

                queue = await channel.declare_queue(queue_name, durable=True)
                await queue.bind(sensor_exchange, routing_key=routing_key)
                await queue.consume(agent.handle_message)

        logger.info("[OccupancyAgent] 🟢 Waiting for sensor data...")
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[OccupancyAgent] 🔴 Stopped by user.")