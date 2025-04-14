import json
import pytz
import logging
from datetime import datetime
from config import ROOM_IDS, EXCHANGES
from rabbitmq_management import RabbitMQManager

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone configuration
tz = pytz.timezone("Asia/Bangkok")

# Global dictionary to aggregate IAQ and power data per room.
AGGREGATED_DATA = {}

def get_aggregated_field(data, key):
    """Helper to get a value from a data dict or 'null' if missing or None."""
    val = data.get(key)
    return str(val) if val is not None else "null"

class SensorSubscriber:
    """
    Subscribes to RabbitMQ sensor data and returns structured messages.
    Combines IAQ + Power + Presence if possible, otherwise returns Presence-only.
    """

    def __init__(self):
        self.tz = tz

    def format_base_message(self, room_id):
        now = datetime.now(self.tz)
        return {
            "timestamp": int(now.timestamp()),
            "datetime": now.isoformat(),
            "device_id": room_id
        }

    def combine_message(self, room_id, presence_data):
        """Combine IAQ + Power + Presence sensor data."""
        base = self.format_base_message(room_id)
        iaq = AGGREGATED_DATA.get(room_id, {}).get("iaq", {})
        power = AGGREGATED_DATA.get(room_id, {}).get("power", {})

        combined = {
            **base,
            "temperature": get_aggregated_field(iaq, "temperature"),
            "humidity": get_aggregated_field(iaq, "humidity"),
            "co2": get_aggregated_field(iaq, "co2"),
            "power_kw_power_meter": get_aggregated_field(power, "power_consumption_kw"),
            "presence_state": get_aggregated_field(presence_data, "presence_state"),
            "sensitivity": get_aggregated_field(presence_data, "sensitivity"),
            "online_status": get_aggregated_field(presence_data, "online_status"),
        }
        logger.info(f"[Subscriber] Received Combined sensor data: {combined}")
        del AGGREGATED_DATA[room_id]
        return combined

    def presence_only_message(self, room_id, presence_data):
        """Return presence-only data structure."""
        base = self.format_base_message(room_id)
        presence_msg = {
            **base,
            "presence_state": get_aggregated_field(presence_data, "presence_state"),
            "sensitivity": get_aggregated_field(presence_data, "sensitivity"),
            "online_status": get_aggregated_field(presence_data, "online_status"),
        }
        logger.info(f"[Subscriber] Received Presence-only sensor data: {presence_msg}")
        return presence_msg

    def sensor_callback(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            room_id = message.get("room_id")
            data = message.get("data", {})
            routing_key = method.routing_key
            sensor_type = routing_key.split(".")[-1]

            # Aggregating IAQ and power data
            if sensor_type == "iaq":
                AGGREGATED_DATA.setdefault(room_id, {})["iaq"] = data
                logger.info(f"[Subscriber] Aggregated IAQ data for {room_id}: {data}")

            elif sensor_type == "power":
                AGGREGATED_DATA.setdefault(room_id, {})["power"] = data
                logger.info(f"[Subscriber] Aggregated Power data for {room_id}: {data}")

            elif sensor_type == "presence":
                if "iaq" in AGGREGATED_DATA.get(room_id, {}) and "power" in AGGREGATED_DATA.get(room_id, {}):
                    combined = self.combine_message(room_id, data)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return combined
                else:
                    presence_msg = self.presence_only_message(room_id, data)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return presence_msg

            else:
                logger.warning(f"[Subscriber] Unhandled sensor type: {sensor_type} from {routing_key}")

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"[Subscriber] Callback error: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag)
            return None

if __name__ == "__main__":
    manager = RabbitMQManager()
    subscriber = SensorSubscriber()

    try:
        # Subscribe for all rooms and sensor types
        for room_id in ROOM_IDS:
            for sensor_type in ["iaq", "presence", "power"]:
                routing_key = f"{room_id}.{sensor_type}"
                queue_name = f"{room_id}_{sensor_type}_queue"

                manager.subscribe(
                    exchange=EXCHANGES["sensor_data"],
                    queue_name=queue_name,
                    routing_key=routing_key,
                    callback=subscriber.sensor_callback
                )

        manager.start_consuming()

    except KeyboardInterrupt:
        logger.info("[Subscriber] Subscriber stopped by user.")
        manager.close()
