import random
import math
from datetime import datetime

class SensorSimulator:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.occupancy_state = "unoccupied"
        
        self.current_temp = random.uniform(22.0, 26.0)
        self.current_humidity = random.uniform(50.0, 60.0)
        self.current_co2 = random.uniform(400.0, 600.0)
        
        self.baseline_temp = 24.0
        self.baseline_humidity = 55.0
        self.baseline_co2 = 500.0
        
        self.phi_temp = 0.9
        self.phi_humidity = 0.8
        self.lambda_co2 = 0.1

    def update_occupancy_state(self):
        now_hour = datetime.now().hour
        if now_hour >= 20 or now_hour < 8:
            if self.occupancy_state == "unoccupied" and random.random() < 0.8:
                self.occupancy_state = "occupied"
            elif self.occupancy_state == "occupied" and random.random() < 0.3:
                self.occupancy_state = "passive"
        else:
            if self.occupancy_state != "unoccupied" and random.random() < 0.3:
                self.occupancy_state = "unoccupied"

        if random.random() < 0.05:
            self.occupancy_state = random.choice(["occupied", "passive", "unoccupied"])

    def generate_presence_data(self, timestamp: int, datetime_str: str) -> dict:
        self.update_occupancy_state()
        online_status = "online" if random.random() < 0.98 else "offline"
        return {
            "timestamp": timestamp,
            "datetime": datetime_str,
            "online_status": online_status,
            "sensitivity": 100.0,
            "presence_state": self.occupancy_state,
        }

    def generate_iaq_data(self, timestamp: int, datetime_str: str) -> dict:
        noise_temp = random.uniform(-0.3, 0.3)
        self.current_temp = (self.phi_temp * self.current_temp +
                             (1 - self.phi_temp) * self.baseline_temp +
                             noise_temp)

        noise_humidity = random.uniform(-1.5, 1.5)
        self.current_humidity = (self.phi_humidity * self.current_humidity +
                                 (1 - self.phi_humidity) * self.baseline_humidity +
                                 noise_humidity)

        if self.occupancy_state == "occupied":
            occupancy_contrib = random.uniform(30, 50)
        elif self.occupancy_state == "passive":
            occupancy_contrib = random.uniform(10, 20)
        else:
            occupancy_contrib = 0

        decay_factor = math.exp(-self.lambda_co2)
        noise_co2 = random.uniform(-5, 5)
        self.current_co2 = (self.current_co2 * decay_factor +
                            (1 - decay_factor) * self.baseline_co2 +
                            occupancy_contrib + noise_co2)

        if random.random() < 0.02:
            fault_multiplier = random.choice([0.5, 1.5])
            self.current_co2 *= fault_multiplier

        return {
            "timestamp": timestamp,
            "datetime": datetime_str,
            "temperature": round(self.current_temp, 1),
            "humidity": round(self.current_humidity, 1),
            "co2": round(self.current_co2, 1),
        }

    def generate_power_data(self, timestamp: int, datetime_str: str) -> dict:
        base_power = random.uniform(3.5, 5.0)

        if self.occupancy_state == "occupied":
            occupancy_factor = random.uniform(1.1, 1.5)
        elif self.occupancy_state == "passive":
            occupancy_factor = random.uniform(1.0, 1.2)
        else:
            occupancy_factor = 1.0

        hvac_factor = random.uniform(1.2, 1.5) if self.current_co2 > 800 else 1.0
        noise_power = random.uniform(-0.2, 0.2)
        power_kw = base_power * occupancy_factor * hvac_factor + noise_power

        return {
            "timestamp": timestamp,
            "datetime": datetime_str,
            "power_consumption_kw": round(power_kw, 2),
        }

# Test run
if __name__ == "__main__":
    sim = SensorSimulator("test_room")
    now = datetime.now()
    ts = int(now.timestamp())
    dt_str = now.isoformat()

    print("Presence:", sim.generate_presence_data(ts, dt_str))
    print("IAQ:", sim.generate_iaq_data(ts, dt_str))
    print("Power:", sim.generate_power_data(ts, dt_str))
