# sensors_publisher.py

import time
import logging
from threading import Thread, local
from config import ROOM_IDS, get_routing_key, EXCHANGES
from sensors_simulator import SensorSimulator
from rabbitmq_management import RabbitMQManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Thread-local storage for RabbitMQManager
_thread_local = local()

def get_thread_local_manager() -> RabbitMQManager:
    """Ensure each thread has its own RabbitMQManager (connection + channel)."""
    if not hasattr(_thread_local, "manager"):
        _thread_local.manager = RabbitMQManager()
    return _thread_local.manager


class SensorPublisher:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.simulator = SensorSimulator(room_id)
        self.running = True

    def publish_iaq(self):
        while self.running:
            data = self.simulator.generate_iaq_data()
            routing_key = get_routing_key(self.room_id, "iaq")
            get_thread_local_manager().publish(
                EXCHANGES["sensor_data"],
                routing_key,
                {"room_id": self.room_id, "data": data}
            )
            logger.info(f"[{self.room_id}] Published IAQ to '{routing_key}': {data}")
            time.sleep(60)

    def publish_presence(self):
        while self.running:
            data = self.simulator.generate_presence_data()
            routing_key = get_routing_key(self.room_id, "presence")
            get_thread_local_manager().publish(
                EXCHANGES["sensor_data"],
                routing_key,
                {"room_id": self.room_id, "data": data}
            )
            logger.info(f"[{self.room_id}] Published Presence to '{routing_key}': {data}")
            time.sleep(1)

    def publish_power(self):
        while self.running:
            data = self.simulator.generate_power_data()
            routing_key = get_routing_key(self.room_id, "power")
            get_thread_local_manager().publish(
                EXCHANGES["sensor_data"],
                routing_key,
                {"room_id": self.room_id, "data": data}
            )
            logger.info(f"[{self.room_id}] Published Power to '{routing_key}': {data}")
            time.sleep(60)

    def start_publishing(self):
        Thread(target=self.publish_iaq, daemon=True).start()
        Thread(target=self.publish_presence, daemon=True).start()
        Thread(target=self.publish_power, daemon=True).start()
        logger.info(f"Started publishing threads for room: {self.room_id}")

    def stop_publishing(self):
        self.running = False
        logger.info(f"Stopped publishing for room: {self.room_id}")


if __name__ == "__main__":
    publishers = []
    try:
        for room_id in ROOM_IDS:
            publisher = SensorPublisher(room_id)
            publisher.start_publishing()
            publishers.append(publisher)

        # Keep the main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Stopping publishers...")
        for publisher in publishers:
            publisher.stop_publishing()

    finally:
        logger.info("Shutting down... Done.")
