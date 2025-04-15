-- Create supabase_admin if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'supabase_admin') THEN
    CREATE ROLE supabase_admin WITH LOGIN PASSWORD 'secret' SUPERUSER;
  END IF;
END
$$;

-- Create the application-specific tables

-- Room sensor latest values
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

-- Fault/occupancy state per room
CREATE TABLE IF NOT EXISTS room_states (
    room_id TEXT NOT NULL,
    is_occupied BOOLEAN NOT NULL,
    vacancy_last_updated TIMESTAMPTZ NOT NULL,
    datapoint TEXT NOT NULL,
    health_status TEXT CHECK (health_status IN ('healthy', 'warning', 'critical')),
    datapoint_last_updated TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (room_id, datapoint)
);
