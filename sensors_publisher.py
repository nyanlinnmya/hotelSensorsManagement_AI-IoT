import time
from sensors_simulator import SensorSimulator
from rabbitmq_management import RabbitMQManager
from config import EXCHANGES, get_routing_key

import logging
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SensorPublisher:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.simulator = SensorSimulator(room_id)
        self.rabbitmq = RabbitMQManager()
        self.last_iaq_publish = 0
        self.last_power_publish = 0

    def publish_data(self):
        current_time = time.time()

        # Presence (every 1 second)
        presence_data = self.simulator.generate_presence_data()
        self.rabbitmq.publish(
            exchange=EXCHANGES["sensor_data"],
            routing_key=get_routing_key(self.room_id, "presence"),
            message=presence_data,
        )
        print(f"Published Presence: {presence_data}")

        # IAQ (every 60 seconds)
        if current_time - self.last_iaq_publish >= 60:
            iaq_data = self.simulator.generate_iaq_data()
            self.rabbitmq.publish(
                exchange=EXCHANGES["sensor_data"],
                routing_key=get_routing_key(self.room_id, "iaq"),
                message=iaq_data,
            )
            self.last_iaq_publish = current_time
            print(f"Published IAQ: {iaq_data}")

        # Power (every 60 seconds, offset from IAQ)
        if current_time - self.last_power_publish >= 60:
            power_data = self.simulator.generate_power_data()
            self.rabbitmq.publish(
                exchange=EXCHANGES["sensor_data"],
                routing_key=get_routing_key(self.room_id, "power"),
                message=power_data,
            )
            self.last_power_publish = current_time
            print(f"Published Power: {power_data}")

if __name__ == "__main__":
    room101_publisher = SensorPublisher(room_id="room101")
    try:
        while True:
            room101_publisher.publish_data()
            time.sleep(1)  # Main loop runs every 1s
    except KeyboardInterrupt:
        room101_publisher.rabbitmq.close()