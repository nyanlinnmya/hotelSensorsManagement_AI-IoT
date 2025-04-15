# database_writer.py


import psycopg2
from psycopg2.extras import execute_values
import logging
from datetime import datetime
from config import TIMESCALE_CONFIG, SUPABASE_CONFIG

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimescaleDBWriter:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connect()
        self._create_table()

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=TIMESCALE_CONFIG["host"],
                port=TIMESCALE_CONFIG["port"],
                user=TIMESCALE_CONFIG["user"],
                password=TIMESCALE_CONFIG["password"],
                dbname=TIMESCALE_CONFIG["dbname"],
            )
            self.cursor = self.conn.cursor()
            logger.info("✅ Connected to TimescaleDB")
        except Exception as e:
            logger.error(f"❌ Failed to connect to TimescaleDB: {e}")
            raise

    def _create_table(self):
        """Create the raw_data table if not exists"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS raw_data (
                    timestamp INTEGER NOT NULL,
                    datetime TIMESTAMPTZ NOT NULL,
                    device_id TEXT NOT NULL,
                    datapoint TEXT NOT NULL,
                    value TEXT NOT NULL
                );
            """)
            self.conn.commit()
            logger.info("✅ Ensured table 'raw_data' exists")
        except Exception as e:
            logger.error(f"❌ Failed to create table: {e}")
            self.conn.rollback()

    def insert_sensor_data(self, data: dict):
        """Insert one data row into raw_data"""
        try:
            self.cursor.execute("""
                INSERT INTO raw_data (timestamp, datetime, device_id, datapoint, value)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                data["timestamp"],
                data["datetime"],
                data["device_id"],
                data["datapoint"],
                data["value"]
            ))
            self.conn.commit()
            logger.debug(f"Inserted data: {data}")
        except Exception as e:
            logger.error(f"❌ Insert failed: {e} | Data: {data}")
            self.conn.rollback()

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            logger.info("🛑 TimescaleDB connection closed")

class SupabaseWriter:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                host=SUPABASE_CONFIG["host"],
                port=SUPABASE_CONFIG["port"],
                user=SUPABASE_CONFIG["user"],
                password=SUPABASE_CONFIG["password"],
                dbname=SUPABASE_CONFIG["dbname"]
            )
            self.cursor = self.conn.cursor()
            logger.info("✅ Connected to Supabase DB")
            self._create_tables()
        except Exception as e:
            logger.error(f"❌ Failed to connect to Supabase: {e}")
            raise

    def _create_tables(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS room_sensors (
                    room_id TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    datetime TIMESTAMPTZ NOT NULL,
                    temperature NUMERIC NOT NULL,
                    humidity NUMERIC NOT NULL,
                    co2 NUMERIC NOT NULL,
                    presence_state TEXT NOT NULL,
                    power_data NUMERIC NOT NULL,
                    PRIMARY KEY (room_id, timestamp)
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS room_states (
                    room_id TEXT NOT NULL,
                    is_occupied BOOLEAN NOT NULL,
                    vacancy_last_updated TIMESTAMPTZ NOT NULL,
                    datapoint TEXT NOT NULL,
                    health_status TEXT CHECK (health_status IN ('healthy', 'warning', 'critical')),
                    datapoint_last_updated TIMESTAMPTZ NOT NULL,
                    PRIMARY KEY (room_id, datapoint)
                );
            """)
            self.conn.commit()
            logger.info("✅ Ensured Supabase tables 'room_sensors' and 'room_states' exist")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Failed to create tables in Supabase: {e}")

    def upsert_sensor_data(self, room_id: str, data: dict):
        try:
            query = """
                INSERT INTO room_sensors (
                    room_id, timestamp, datetime, temperature, humidity, co2,
                    presence_state, power_data
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (room_id, timestamp)
                DO UPDATE SET
                    datetime = EXCLUDED.datetime,
                    temperature = EXCLUDED.temperature,
                    humidity = EXCLUDED.humidity,
                    co2 = EXCLUDED.co2,
                    presence_state = EXCLUDED.presence_state,
                    power_data = EXCLUDED.power_data;
            """
            self.cursor.execute(query, (
                room_id,
                data["timestamp"],
                data["datetime"],
                data.get("temperature", 0),
                data.get("humidity", 0),
                data.get("co2", 0),
                data.get("presence_state", "unknown"),
                data.get("power_kw_power_meter", 0),
            ))
            self.conn.commit()
            logger.info(f"🟢 Upserted sensor values for {room_id}")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Failed to upsert sensor data: {e}")

    def upsert_room_state(self, room_id: str, is_occupied: bool, datapoint: str, health_status: str = "healthy"):
        try:
            now = datetime.now()
            query = """
                INSERT INTO room_states (
                    room_id,
                    is_occupied,
                    vacancy_last_updated,
                    datapoint,
                    health_status,
                    datapoint_last_updated
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (room_id, datapoint)
                DO UPDATE SET
                    is_occupied = EXCLUDED.is_occupied,
                    vacancy_last_updated = EXCLUDED.vacancy_last_updated,
                    datapoint = EXCLUDED.datapoint,
                    health_status = EXCLUDED.health_status,
                    datapoint_last_updated = EXCLUDED.datapoint_last_updated;
            """
            self.cursor.execute(query, (
                room_id,
                is_occupied,
                now,
                datapoint,
                health_status,
                now
            ))
            self.conn.commit()
            logger.info(f"🟢 Upserted room state for {room_id}, datapoint={datapoint}")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Failed to upsert room state: {e}")

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            logger.info("🛑 Supabase connection closed")

# Optional: For testing
if __name__ == "__main__":
    writer = TimescaleDBWriter()
    sample = {
        "timestamp": 1681234567,
        "datetime": "2025-04-11T23:15:00+07:00",
        "device_id": "room101",
        "datapoint": "temperature",
        "value": "27.3"
    }
    writer.insert_sensor_data(sample)
    writer.close()

    supabase = SupabaseWriter()

    test_sensor_data = {
        "timestamp": int(datetime.now().timestamp()),
        "datetime": datetime.now().isoformat(),
        "temperature": 24.5,
        "humidity": 53.2,
        "co2": 635,
        "presence_state": "occupied",
        "power_kw_power_meter": 5.2
    }
    supabase.upsert_sensor_data("room101", test_sensor_data)
    supabase.upsert_room_state("room101", is_occupied=True, datapoint="co2", health_status="healthy")
    supabase.close()