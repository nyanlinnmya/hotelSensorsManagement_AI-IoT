# Define your room IDs here
ROOM_IDS = ["room101",
            "room102"]

RABBITMQ_CONFIG = {
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