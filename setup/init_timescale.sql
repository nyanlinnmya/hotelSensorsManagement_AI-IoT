-- Create raw_data table with room_id
CREATE TABLE raw_data (
    timestamp INTEGER,
    datetime TIMESTAMPTZ DEFAULT NOW(),
    room_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    datapoint TEXT NOT NULL,
    value TEXT NOT NULL
);

-- Convert to hypertable with time partitioning on datetime
SELECT create_hypertable('raw_data', 'datetime');

-- Add indexes for efficient room-based queries
CREATE INDEX idx_raw_data_room_id ON raw_data (room_id);