-- Create raw_data table
CREATE TABLE raw_data (
    timestamp INTEGER,
    datetime TIMESTAMPTZ DEFAULT NOW(),
    device_id TEXT,
    datapoint TEXT,
    value TEXT
);

-- Convert to hypertable
SELECT create_hypertable('raw_data', 'datetime');