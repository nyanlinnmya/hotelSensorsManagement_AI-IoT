# sensor_subscriber.py

import json
import time
import pytz
import logging
from datetime import datetime
from config import ROOM_IDS, EXCHANGES
from rabbitmq_management import RabbitMQManager
from database_writer import TimescaleDBWriter

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone
tz = pytz.timezone("Asia/Bangkok")

# Initialize writer globally
db_writer = TimescaleDBWriter()

def format_message(room_id, datapoint, value):
    now = datetime.now(tz)
    return {
        "timestamp": int(now.timestamp()),
        "datetime": now.isoformat(),
        "device_id": room_id,
        "datapoint": datapoint,
        "value": str(value),  # Store as string
    }

def sensor_callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        room_id = message.get("room_id")
        data = message.get("data", {})

        routing_key = method.routing_key
        datapoint = routing_key.split(".")[-1]

        if datapoint == "iaq":
            for key in ["temperature", "humidity", "co2"]:
                if key in data:
                    log_data = format_message(room_id, key, data[key])
                    logger.info(log_data)
                    db_writer.insert_sensor_data(log_data)

        elif datapoint == "presence":
            presence_state = data.get("presence_state")
            log_data = format_message(room_id, "presence", presence_state)
            logger.info(log_data)
            db_writer.insert_sensor_data(log_data)

        elif datapoint == "power":
            power_value = data.get("power")
            log_data = format_message(room_id, "power", power_value)
            logger.info(log_data)
            db_writer.insert_sensor_data(log_data)

        else:
            logger.warning(f"Unhandled datapoint: {datapoint} from {routing_key}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.error(f"Callback error: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag)

if __name__ == "__main__":
    manager = RabbitMQManager()

    try:
        for room_id in ROOM_IDS:
            for sensor_type in ["iaq", "presence", "power"]:
                routing_key = f"{room_id}.{sensor_type}"
                queue_name = f"{room_id}_{sensor_type}_queue"

                manager.subscribe(
                    exchange=EXCHANGES["sensor_data"],
                    queue_name=queue_name,
                    routing_key=routing_key,
                    callback=sensor_callback
                )

        manager.start_consuming()

    except KeyboardInterrupt:
        logger.info("Subscriber stopped by user.")
        manager.close()
        db_writer.close()
