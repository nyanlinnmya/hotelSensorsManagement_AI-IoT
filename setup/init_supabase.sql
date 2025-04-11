-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_cron";

-- Room sensor latest values
CREATE TABLE room_sensors (
    room_id TEXT PRIMARY KEY,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    temperature FLOAT,
    humidity FLOAT,
    co2 FLOAT,
    presence_state TEXT,
    power_data JSONB
);

-- Room state and faults
CREATE TABLE room_states (
    room_id TEXT PRIMARY KEY REFERENCES room_sensors(room_id),
    is_occupied BOOLEAN DEFAULT FALSE,
    last_fault TIMESTAMPTZ,
    current_fault TEXT,
    health_status TEXT CHECK (health_status IN ('healthy', 'warning', 'critical'))
);

-- Enable realtime for both tables
ALTER PUBLICATION supabase_realtime ADD TABLE room_sensors;
ALTER PUBLICATION supabase_realtime ADD TABLE room_states;

-- Create a view for dashboard
CREATE MATERIALIZED VIEW room_analytics AS
SELECT 
    s.room_id,
    s.temperature,
    s.humidity,
    s.co2,
    s.presence_state,
    s.power_data,
    st.is_occupied,
    st.health_status,
    st.current_fault,
    st.last_fault
FROM room_sensors s
JOIN room_states st ON s.room_id = st.room_id;

-- Refresh view every minute
SELECT cron.schedule('*/1 * * * *', 'REFRESH MATERIALIZED VIEW room_analytics');