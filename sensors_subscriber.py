# sensor_subscriber.py

import json
import time
import pytz
import logging
from datetime import datetime
from config import ROOM_IDS, EXCHANGES
from rabbitmq_management import RabbitMQManager

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone
tz = pytz.timezone("Asia/Bangkok")

def format_message(room_id, datapoint, value):
    now = datetime.now(tz)
    return {
        "timestamp": int(now.timestamp()),
        "datetime": now.isoformat(),
        "device_id": room_id,
        "datapoint": datapoint,
        "value": str(value),
    }

def sensor_callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        room_id = message.get("room_id")
        data = message.get("data", {})

        if method.routing_key.endswith(".iaq"):
            # Expecting temperature, humidity, co2
            for key in ["temperature", "humidity", "co2"]:
                if key in data:
                    log_data = format_message(room_id, key, data[key])
                    logger.info(log_data)

        else:
            # Generic handling for presence and power
            datapoint = method.routing_key.split(".")[-1]
            log_data = format_message(room_id, datapoint, data)
            logger.info(log_data)

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
