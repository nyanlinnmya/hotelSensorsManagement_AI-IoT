# Define your room IDs here
ROOM_IDS = ["room101",
            "room102"]

RABBITMQ_CONFIG = {
    # "host": "rabbitmq",
    "host": "localhost",
    "port": 5672,
    "user": "admin",
    "password": "secret",
    "vhost": "/",
    "heartbeat": 30
}

# Exchanges and Queues
EXCHANGES = {
    "sensor_data": "sensor_data_exchange",
    "fault_alerts": "fault_exchange",
    "occupancy": "occupancy_exchange",
}

QUEUES = {
    "fault_detection": "fault_detection_queue",
    "occupancy_detection": "occupancy_detection_queue",
}

# Routing Keys (e.g., "room101.iaq", "room101.presence")
def get_routing_key(room_id: str, sensor_type: str) -> str:
    return f"{room_id}.{sensor_type}"


TIMESCALE_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "user": "admin",
    "password": "secret",
    "dbname": "sensor_data",
}

SUPABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "secret",
    "dbname": "supabase",
}

SUPABASE_HTTP_CONFIG = {
    "url": "https://blmpxixwblzyzxvygalm.supabase.co",
    "key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJsbXB4aXh3Ymx6eXp4dnlnYWxtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQyMTA3NzUsImV4cCI6MjA1OTc4Njc3NX0.4NnTOmuhMGTFjsCXIPrwK4peYg1KPtDxGeRTU_qsEbU"
}
