import asyncio
import aio_pika
import json
import logging
from config import ROOM_IDS, EXCHANGES, RABBITMQ_CONFIG
from sensors_subscriber import SensorSubscriber
from database_writer import TimescaleDBWriter, SupabaseWriter

# -----------------------------
# GLOBAL THRESHOLDS
# -----------------------------
THRESHOLDS = {
    "temperature": {"min": 18.0, "max": 27.0},
    "humidity": {"min": 30.0, "max": 65.0},
    "co2": {"min": 400, "max": 1500},
    "power_kw_power_meter": {"min": 3.0, "max": 10.0},
    "sensitivity": {"min": 50.0},
    "presence_state": {"allowed": ["occupied", "unoccupied", "passive"]},
    "online_status": {"allowed": ["online"]}
}

# -----------------------------
# LOGGING
# -----------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FaultAgent")

# -----------------------------
# ACTIVE TASK TRACKER
# -----------------------------
active_tasks = set()

class FaultDetectionAgent:
    def __init__(self, fault_exchange: aio_pika.Exchange):
        self.fault_exchange = fault_exchange
        self.subscriber = SensorSubscriber()
        self.db_writer = TimescaleDBWriter()
        self.supabase_writer = SupabaseWriter()

    def detect_faults(self, message: dict) -> tuple[list[str], list[str]]:
        faults = []
        datapoints = []

        for key, rule in THRESHOLDS.items():
            if key not in message:
                continue

            value = message.get(key)
            if value == "null" or value is None:
                faults.append(f"{key} is missing or null.")
                datapoints.append(key)
                continue

            try:
                if "min" in rule and float(value) < rule["min"]:
                    faults.append(f"{key} below min: {value} < {rule['min']}")
                    datapoints.append(key)
                if "max" in rule and float(value) > rule["max"]:
                    faults.append(f"{key} above max: {value} > {rule['max']}")
                    datapoints.append(key)
                if "allowed" in rule and value not in rule["allowed"]:
                    faults.append(f"{key} value not allowed: {value}")
                    datapoints.append(key)
            except Exception as e:
                faults.append(f"{key} invalid value: {value} ({e})")
                datapoints.append(key)

        return faults, list(set(datapoints))  # unique datapoints

    async def handle_message(self, message: aio_pika.IncomingMessage):
        task = asyncio.current_task()
        active_tasks.add(task)

        try:
            async with message.process(ignore_processed=True):
                routing_key = message.routing_key
                logger.info(f"[FaultAgent] Received from {routing_key}")
                raw_body = message.body.decode()
                parsed = json.loads(raw_body)

                room_id = parsed.get("room_id")
                sensor_data = parsed.get("data", {})
                sensor_type = routing_key.split(".")[-1]

                # Mock method/props for SensorSubscriber
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

                try:
                    self.supabase_writer.upsert_sensor_data(output["device_id"], output)
                except Exception as e:
                    logger.error(f"[FaultAgent] ❌ Failed to upsert Supabase room_sensors: {e}")


                if not output:
                    return

                # Insert each sensor datapoint into TimescaleDB
                for key, value in output.items():
                    if key in ["temperature", "humidity", "co2", "power_kw_power_meter", "presence_state", "sensitivity", "online_status"]:
                        try:
                            self.db_writer.insert_sensor_data({
                                "timestamp": output["timestamp"],
                                "datetime": output["datetime"],
                                "device_id": output["device_id"],
                                "datapoint": key,
                                "value": str(value)
                            })
                            logger.info(f"[FaultAgent] 📥 Inserted: device={output['device_id']} | {key}={value}")
                        except Exception as e:
                            logger.error(f"[FaultAgent] ❌ Failed to insert {key} for {output['device_id']}: {e}")

                # Detect faults and publish alert if needed
                faults, datapoints = self.detect_faults(output)
                if faults:
                    payload = {
                        "room_id": room_id,
                        "timestamp": output["timestamp"],
                        "faults": faults,
                        "datapoint": ", ".join(datapoints)
                    }
                    await self.fault_exchange.publish(
                        aio_pika.Message(body=json.dumps(payload).encode()),
                        routing_key=f"{room_id}.fault"
                    )
                    logger.warning(f"[FaultAgent] 🚨 Fault alert sent: {payload}")
                else:
                    logger.info(f"[FaultAgent] ✅ No faults detected for {room_id}")

        except Exception as e:
            logger.error(f"[FaultAgent] ❌ Error processing message: {e}")
        finally:
            active_tasks.discard(task)

async def main():
    logger.info("[FaultAgent] Connecting to RabbitMQ...")

    connection = await aio_pika.connect_robust(
        host=RABBITMQ_CONFIG["host"],
        port=RABBITMQ_CONFIG["port"],
        login=RABBITMQ_CONFIG["user"],
        password=RABBITMQ_CONFIG["password"],
        virtualhost=RABBITMQ_CONFIG["vhost"]
    )

    async with connection:
        channel = await connection.channel()
        logger.info("[FaultAgent] ✅ Connected to RabbitMQ.")

        sensor_exchange = await channel.declare_exchange(
            EXCHANGES["sensor_data"], aio_pika.ExchangeType.TOPIC, durable=True
        )
        fault_exchange = await channel.declare_exchange(
            EXCHANGES["fault_alerts"], aio_pika.ExchangeType.TOPIC, durable=True
        )

        agent = FaultDetectionAgent(fault_exchange)

        # Declare and bind queues for each room and sensor
        for room_id in ROOM_IDS:
            for sensor_type in ["iaq", "power", "presence"]:
                routing_key = f"{room_id}.{sensor_type}"
                queue_name = f"{room_id}_{sensor_type}_fault_queue"

                queue = await channel.declare_queue(queue_name, durable=True)
                await queue.bind(sensor_exchange, routing_key=routing_key)
                await queue.consume(agent.handle_message)

        logger.info("[FaultAgent] 🟢 Waiting for sensor data...")

        try:
            await asyncio.Future()  # keep alive
        except asyncio.CancelledError:
            logger.info("[FaultAgent] 🔁 Cancel signal received. Cancelling tasks...")
            for task in active_tasks:
                task.cancel()
            await asyncio.gather(*active_tasks, return_exceptions=True)
        finally:
            agent.db_writer.close()
            logger.info("[FaultAgent] ✅ TimescaleDB connection closed.")
            agent.db_writer.close()
            agent.supabase_writer.close()
            logger.info("[FaultAgent] ✅ Supabase connection closed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[FaultAgent] 🔴 Stopped by user.")
