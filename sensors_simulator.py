import random
import math
from datetime import datetime

class SensorSimulator:
    def __init__(self, room_id: str):
        self.room_id = room_id
        # Initial occupancy state: "unoccupied", "occupied", or "passive"
        self.occupancy_state = "unoccupied"
        
        # Initialize internal IAQ state variables
        self.current_temp = random.uniform(22.0, 26.0)
        self.current_humidity = random.uniform(50.0, 60.0)
        self.current_co2 = random.uniform(400.0, 600.0)
        
        # Baselines
        self.baseline_temp = 24.0
        self.baseline_humidity = 55.0
        self.baseline_co2 = 500.0
        
        # AR model coefficients
        self.phi_temp = 0.9      # Temperature persistence
        self.phi_humidity = 0.8  # Humidity persistence
        
        # CO₂ decay constant
        self.lambda_co2 = 0.1    # Exponential decay constant for CO₂
        
    def _generate_datetime(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def update_occupancy_state(self):
        """
        Update the occupancy state with probabilities that vary by time-of-day.
        Nighttime (before 8 AM or after 8 PM) drives high occupancy because hotel rooms
        are more likely to be in use. During the day, there's a higher chance of being unoccupied.
        """
        now_hour = datetime.now().hour

        # Define nighttime and daytime probabilities
        if now_hour >= 20 or now_hour < 8:
            # Nighttime: high chance to be occupied
            if self.occupancy_state == "unoccupied":
                # 80% chance to switch to "occupied" if currently unoccupied
                if random.random() < 0.8:
                    self.occupancy_state = "occupied"
            else:
                # If already occupied, there is a chance to become "passive" (e.g., sleeping)
                if self.occupancy_state == "occupied" and random.random() < 0.3:
                    self.occupancy_state = "passive"
        else:
            # Daytime: higher probability to be unoccupied
            if self.occupancy_state != "unoccupied":
                if random.random() < 0.3:
                    self.occupancy_state = "unoccupied"
        
        # A general random fluctuation (5% chance) to allow other transitions
        if random.random() < 0.05:
            self.occupancy_state = random.choice(["occupied", "passive", "unoccupied"])
    
    def generate_presence_data(self) -> dict:
        """
        Generate motion sensor data.
        Occasionally toggle occupancy state and simulate occasional sensor offline.
        """
        self.update_occupancy_state()
        online_status = "online" if random.random() < 0.98 else "offline"
        return {
            "datetime": self._generate_datetime(),
            "online_status": online_status,
            "sensitivity": 100.0,
            "presence_state": self.occupancy_state,
        }
    
    def generate_iaq_data(self) -> dict:
        """
        Generate IAQ data (temperature, humidity, CO₂) using AR components and an exponential decay for CO₂.
        Occupancy influences the CO₂ increment:
          - "occupied" contributes a higher increase.
          - "passive" contributes a lower increase.
        Occasional faults (2% chance) simulate sensor errors.
        """
        # Temperature update: AR(1) model
        noise_temp = random.uniform(-0.3, 0.3)
        self.current_temp = (self.phi_temp * self.current_temp +
                             (1 - self.phi_temp) * self.baseline_temp +
                             noise_temp)
        
        # Humidity update: AR(1) model
        noise_humidity = random.uniform(-1.5, 1.5)
        self.current_humidity = (self.phi_humidity * self.current_humidity +
                                 (1 - self.phi_humidity) * self.baseline_humidity +
                                 noise_humidity)
        
        # CO₂ update: exponential decay model plus occupancy contribution
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
        
        # Introduce an occasional fault (2% chance)
        if random.random() < 0.02:
            fault_multiplier = random.choice([0.5, 1.5])
            self.current_co2 *= fault_multiplier
        
        return {
            "datetime": self._generate_datetime(),
            "temperature": round(self.current_temp, 1),
            "humidity": round(self.current_humidity, 1),
            "co2": round(self.current_co2, 1),
        }
    
    def generate_power_data(self) -> dict:
        """
        Generate power meter data.
        Power is the product of a base consumption, an occupancy factor, and
        an HVAC factor (if CO₂ is high).
        """
        base_power = random.uniform(3.5, 5.0)
        
        # Occupancy factor: factors vary by occupancy state
        if self.occupancy_state == "occupied":
            occupancy_factor = random.uniform(1.1, 1.5)
        elif self.occupancy_state == "passive":
            occupancy_factor = random.uniform(1.0, 1.2)
        else:
            occupancy_factor = 1.0
        
        # HVAC factor: if CO₂ exceeds 800 ppm, HVAC ramps up ventilation
        hvac_factor = random.uniform(1.2, 1.5) if self.current_co2 > 800 else 1.0
        
        noise_power = random.uniform(-0.2, 0.2)
        power_kw = base_power * occupancy_factor * hvac_factor + noise_power
        
        return {
            "datetime": self._generate_datetime(),
            "power_consumption_kw": round(power_kw, 2),
        }

# Example usage:
if __name__ == "__main__":
    simulator = SensorSimulator("Room101")
    for _ in range(10):
        print("Presence Data:", simulator.generate_presence_data())
        print("IAQ Data:", simulator.generate_iaq_data())
        print("Power Data:", simulator.generate_power_data())
        print("-----")