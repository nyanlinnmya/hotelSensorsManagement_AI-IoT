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
# Structure: { room_id: { "iaq": { ... }, "power": { ... } } }
AGGREGATED_DATA = {}

def get_aggregated_field(data, key):
    """Helper to get a value from a data dict or "null" if missing or None."""
    val = data.get(key)
    return str(val) if val is not None else "null"

class SensorSubscriber:
    """
    Class for subscribing to RabbitMQ sensor data and logging messages.
    It handles data aggregation: when both IAQ and power data are present,
    they are combined with the latest presence sensor data.
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

    def log_combined_message(self, room_id, presence_data):
        """
        Combines aggregated IAQ and power data with the given presence sensor data.
        Any missing value is replaced with "null".
        After logging, clears the aggregator for that room.
        """
        base = self.format_base_message(room_id)
        iaq = AGGREGATED_DATA.get(room_id, {}).get("iaq", {})
        power = AGGREGATED_DATA.get(room_id, {}).get("power", {})

        combined = {
            **base,
            # IAQ data: temperature, humidity, co2
            "temperature": get_aggregated_field(iaq, "temperature"),
            "humidity": get_aggregated_field(iaq, "humidity"),
            "co2": get_aggregated_field(iaq, "co2"),
            # Power data: note the renamed key
            "power_kw_power_meter": get_aggregated_field(power, "power_consumption_kw"),
            # Presence sensor data: presence_state, sensitivity, online_status
            "presence_state": get_aggregated_field(presence_data, "presence_state"),
            "sensitivity": get_aggregated_field(presence_data, "sensitivity"),
            "online_status": get_aggregated_field(presence_data, "online_status"),
        }
        logger.info(f"[Subscriber] Received Combined sensor data: {combined}")
        # Clear the aggregator for this room after combining.
        if room_id in AGGREGATED_DATA:
            del AGGREGATED_DATA[room_id]

    def log_presence_only(self, room_id, presence_data):
        """
        Log only presence sensor data when no full IAQ and power data are available.
        """
        base = self.format_base_message(room_id)
        presence_msg = {
            **base,
            "presence_state": get_aggregated_field(presence_data, "presence_state"),
            "sensitivity": get_aggregated_field(presence_data, "sensitivity"),
            "online_status": get_aggregated_field(presence_data, "online_status"),
        }
        logger.info(f"[Subscriber] Received Presence-only sensor data: {presence_msg}")

    def sensor_callback(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            room_id = message.get("room_id")
            data = message.get("data", {})
            routing_key = method.routing_key
            sensor_type = routing_key.split(".")[-1]

            # Process based on sensor type.
            if sensor_type == "iaq":
                # Store IAQ data for the room.
                if room_id not in AGGREGATED_DATA:
                    AGGREGATED_DATA[room_id] = {}
                AGGREGATED_DATA[room_id]["iaq"] = data
                logger.info(f"[Subscriber] Aggregated IAQ data for {room_id}: {data}")

            elif sensor_type == "power":
                # Store power sensor data for the room.
                if room_id not in AGGREGATED_DATA:
                    AGGREGATED_DATA[room_id] = {}
                AGGREGATED_DATA[room_id]["power"] = data
                logger.info(f"[Subscriber] Aggregated power data for {room_id}: {data}")

            elif sensor_type == "presence":
                # Handle presence data
                # Check if we have both IAQ and power data for combining.
                room_agg = AGGREGATED_DATA.get(room_id, {})
                if "iaq" in room_agg and "power" in room_agg:
                    self.log_combined_message(room_id, data)
                else:
                    self.log_presence_only(room_id, data)
            else:
                logger.warning(f"[Subscriber] Unhandled sensor type: {sensor_type} from {routing_key}")

            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"[Subscriber] Callback error: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag)

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