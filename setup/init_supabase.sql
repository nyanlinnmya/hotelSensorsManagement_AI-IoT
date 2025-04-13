-- Create a supabase_admin role with superuser privileges
CREATE ROLE supabase_admin WITH LOGIN PASSWORD 'admin' SUPERUSER;

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


CREATE TABLE IF NOT EXISTS room_states (
    room_id TEXT PRIMARY KEY,
    is_occupied BOOLEAN NOT NULL,
    vacancy_last_updated TIMESTAMPTZ NOT NULL,
    datapoint TEXT NOT NULL,
    health_status TEXT CHECK (health_status IN ('healthy', 'warning', 'critical')),
    last_updated TIMESTAMPTZ NOT NULL
);

-- Set the pg_cron configuration so that the current database ('supabase') is used.
-- ALTER SYSTEM SET cron.database_name = 'supabase';
-- SELECT pg_reload_conf();

-- Enable required extensions
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "pg_cron";

-- Enable realtime publication
CREATE PUBLICATION supabase_realtime;

-- Enable realtime for both tables
ALTER PUBLICATION supabase_realtime ADD TABLE room_sensors;
ALTER PUBLICATION supabase_realtime ADD TABLE room_states;

-- Create a materialized view for the dashboard
CREATE MATERIALIZED VIEW room_analytics AS
SELECT 
    s.room_id,
    s.temperature,
    s.humidity,
    s.co2,
    s.presence_state,
    s.power_data,
    st.is_occupied,
    st.vacancy_last_updated,
    st.datapoint,
    st.health_status,
    st.last_updated
FROM room_sensors s
JOIN room_states st ON s.room_id = st.room_id;

-- Refresh the materialized view every minute using pg_cron
SELECT cron.schedule('*/1 * * * *', 'REFRESH MATERIALIZED VIEW room_analytics');