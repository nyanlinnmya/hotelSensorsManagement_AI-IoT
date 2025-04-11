# database_writer.py

import psycopg2
from psycopg2.extras import execute_values
import logging
from config import TIMESCALE_CONFIG

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
