import asyncio
import logging
import pytz
from datetime import datetime
import aio_pika
import json

from config import ROOM_IDS, get_routing_key, EXCHANGES, RABBITMQ_CONFIG
from sensors_simulator import SensorSimulator

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AsyncSensorPublisher:
    def __init__(self, room_id, exchange):
        self.room_id = room_id
        self.simulator = SensorSimulator(room_id)
        self.exchange = exchange

    def _get_time(self):
        now = datetime.now(pytz.timezone("Asia/Bangkok"))
        return int(now.timestamp()), now.isoformat()

    async def publish(self, routing_key, payload):
        try:
            await self.exchange.publish(
                aio_pika.Message(body=json.dumps(payload).encode()),
                routing_key=routing_key
            )
            logger.info(f"[Publisher] [{self.room_id}] Published to '{routing_key}': {payload['data']}")
        except Exception as e:
            logger.error(f"[Publisher] [{self.room_id}] Failed to publish to '{routing_key}': {e}")

    async def publish_iaq(self):
        while True:
            ts, dt_str = self._get_time()
            # Call generate_iaq_data() without extra arguments
            data = self.simulator.generate_iaq_data()
            routing_key = get_routing_key(self.room_id, "iaq")
            payload = {"room_id": self.room_id, "data": data}
            await self.publish(routing_key, payload)
            await asyncio.sleep(60)

    async def publish_presence(self):
        while True:
            ts, dt_str = self._get_time()
            # Call generate_presence_data() without extra arguments
            data = self.simulator.generate_presence_data()
            routing_key = get_routing_key(self.room_id, "presence")
            payload = {"room_id": self.room_id, "data": data}
            await self.publish(routing_key, payload)
            await asyncio.sleep(1)

    async def publish_power(self):
        while True:
            ts, dt_str = self._get_time()
            # Call generate_power_data() without extra arguments
            data = self.simulator.generate_power_data()
            routing_key = get_routing_key(self.room_id, "power")
            payload = {"room_id": self.room_id, "data": data}
            await self.publish(routing_key, payload)
            await asyncio.sleep(60)

    async def start(self):
        logger.info(f"[Publisher] Started publishing threads for room: {self.room_id}")
        await asyncio.gather(
            self.publish_iaq(),
            self.publish_presence(),
            self.publish_power()
        )

async def main():
    try:
        logger.info("[Publisher] Connecting to RabbitMQ...")
        connection = await aio_pika.connect_robust(
            host=RABBITMQ_CONFIG["host"],
            port=RABBITMQ_CONFIG["port"],
            login=RABBITMQ_CONFIG["user"],
            password=RABBITMQ_CONFIG["password"],
            virtualhost=RABBITMQ_CONFIG["vhost"]
        )

        async with connection:
            channel = await connection.channel()
            logger.info("[Publisher] ✅ Connected to RabbitMQ.")

            # Declare the topic exchange for sensor data
            exchange = await channel.declare_exchange(
                EXCHANGES["sensor_data"],
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            logger.info(f"[Publisher] Exchange '{EXCHANGES['sensor_data']}' declared.")

            # Start publishers for each room
            publishers = [AsyncSensorPublisher(room_id, exchange) for room_id in ROOM_IDS]
            await asyncio.gather(*(pub.start() for pub in publishers))

    except Exception as e:
        logger.error(f"[Publisher] ❌ Error during publishing setup: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[Publisher] ⛔ Keyboard interrupt received. Stopping publishers...")
    finally:
        logger.info("[Publisher] 🔁 Shutting down... Done.")
