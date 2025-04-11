-- Create raw_data table
CREATE TABLE raw_data (
    timestamp INTEGER,
    datetime TIMESTAMPTZ DEFAULT NOW(),
    room_id TEXT,                  -- Added room_id
    device_id TEXT,
    datapoint TEXT,
    value TEXT
);

-- Convert to hypertable
SELECT create_hypertable('raw_data', 'datetime');
CREATE INDEX idx_raw_data_room_id ON raw_data (room_id);  -- For faster room queries