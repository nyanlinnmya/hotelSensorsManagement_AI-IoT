-- Latest sensor values
CREATE TABLE room_sensors (
    room_id TEXT PRIMARY KEY,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    temperature FLOAT,
    humidity FLOAT,
    co2 FLOAT,
    presence_state TEXT,
    power_consumption JSONB
);

-- Add an index on last_updated for faster queries
CREATE INDEX idx_room_sensors_last_updated ON room_sensors (last_updated);

-- Fault/occupancy states
CREATE TABLE room_states (
    room_id TEXT PRIMARY KEY,
    is_occupied BOOLEAN DEFAULT FALSE,
    last_fault TIMESTAMPTZ,
    fault_type TEXT,
    FOREIGN KEY (room_id) REFERENCES room_sensors(room_id)
);

-- Add an index on is_occupied for faster queries
CREATE INDEX idx_room_states_is_occupied ON room_states (is_occupied);

-- Enable Realtime
ALTER TABLE room_sensors REPLICA IDENTITY FULL;
ALTER TABLE room_states REPLICA IDENTITY FULL;