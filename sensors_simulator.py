import random
from datetime import datetime

class SensorSimulator:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.occupancy_state = "unoccupied"

    def _generate_datetime(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def generate_iaq_data(self) -> dict:
        """Generate IAQ data (temperature, humidity, CO₂)."""
        base_temp = random.uniform(22.0, 26.0)
        base_humidity = random.uniform(50.0, 60.0)
        base_co2 = random.uniform(400.0, 600.0)

        if self.occupancy_state == "occupied":
            base_co2 += random.uniform(100.0, 200.0)  # CO₂ rises when occupied

        return {
            "datetime": self._generate_datetime(),
            "temperature": round(base_temp + random.uniform(-0.5, 0.5), 1),
            "humidity": round(base_humidity + random.uniform(-2.0, 2.0), 1),
            "co2": round(base_co2 + random.uniform(-10.0, 10.0), 1),
        }

    def generate_presence_data(self) -> dict:
        """Generate motion sensor data (5% chance to flip state)."""
        if random.random() < 0.05:
            self.occupancy_state = "occupied" if self.occupancy_state == "unoccupied" else "unoccupied"
        return {
            "datetime": self._generate_datetime(),
            "online_status": "online",
            "sensitivity": 100.0,
            "presence_state": self.occupancy_state,
        }

    def generate_power_data(self) -> dict:
        """Generate power meter data (spikes when occupied)."""
        base_power = [random.uniform(3.5, 5.0) for _ in range(6)]
        if self.occupancy_state == "occupied":
            base_power = [p * random.uniform(1.1, 1.5) for p in base_power]
        return {
            "datetime": self._generate_datetime(),
            **{f"power_kw_power_meter_{i+1}": round(base_power[i] + random.uniform(-0.2, 0.2), 2)
               for i in range(6)},
        }