-- Create the `auth` schema first for GoTrue
CREATE SCHEMA IF NOT EXISTS auth;

-- Create the application-specific tables
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

CREATE TABLE IF NOT EXISTS room_states (
    room_id TEXT NOT NULL,
    is_occupied BOOLEAN NOT NULL,
    vacancy_last_updated TIMESTAMPTZ NOT NULL,
    datapoint TEXT NOT NULL,
    health_status TEXT CHECK (health_status IN ('healthy', 'warning', 'critical')),
    datapoint_last_updated TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (room_id, datapoint)
);

-- Enable Realtime for room_states
ALTER TABLE room_states REPLICA IDENTITY FULL;

-- Attach to Realtime publication (if not already done)
CREATE PUBLICATION supabase_realtime;
ALTER PUBLICATION supabase_realtime ADD TABLE room_states;
