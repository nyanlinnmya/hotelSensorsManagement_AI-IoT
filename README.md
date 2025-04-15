# 🏨 Hotel Sensors Management – AI + IoT System

This project simulates smart hotel room sensors and processes real-time IoT data using a combination of Python agents, RabbitMQ, TimescaleDB, and Supabase, with a React dashboard for visualization.

---

## 📦 Project Structure

```
hotelSensorsManagement_AI-IoT/
├── config.py                       # Configuration: room list, RabbitMQ, DBs
├── sensors_publisher.py           # Publishes IAQ, presence, and power data
├── sensors_subscriber.py          # Logs sensor messages from RabbitMQ
├── fault_detection_agent.py       # Identifies sensor faults
├── occupancy_detection_agent.py   # Determines if room is occupied
├── supabase_updater_agent.py      # Updates latest data & health to Supabase
├── database_writer.py             # Writes to TimescaleDB + Supabase
├── sensors_simulator.py           # Realistic IAQ & occupancy simulation
├── rabbitmq_management.py         # Declares exchanges and queues
├── setup_rabbitmq.py              # One-time queue/exchange setup
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Base image for all Python agents
├── docker-setup/
│   ├── docker-compose.yml         # Main orchestration
│   ├── init_timescale.sql         # Creates raw_data table
│   └── rabbitmq.conf              # RabbitMQ guest access config
└── hotel-iot-dashboard/
    └── react-app/                 # Frontend React dashboard
```

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd hotelSensorsManagement_AI-IoT/docker-setup
```

---

### 2. Build and Run

```bash
docker-compose up -d --build
```

This launches:
- RabbitMQ
- TimescaleDB
- All Python microservices
- Supabase integrations
- React dashboard

---

### 3. View the Dashboard

Visit: [http://localhost:3000](http://localhost:3000)

See room statuses, fault alerts, and live CO₂ / temp / humidity gauges.

---

### 4. View RabbitMQ

Visit: [http://localhost:15672](http://localhost:15672)

- Username: `admin`
- Password: `secret`

---

### 5. Add More Rooms

Open `config.py` and add more room IDs:

```python
ROOM_IDS = ["room101", "room102", "room103", "room104"]
```

Then restart containers:

```bash
docker-compose restart
```

---

### 6. Supabase (Cloud) Setup

You're using [Supabase Cloud](https://app.supabase.com).

- Enable Row Level Security (RLS) on `room_states` and `room_sensors`
- Add realtime support:
  
```sql
ALTER PUBLICATION supabase_realtime ADD TABLE room_states;
```

---

## ☁️ Supabase (Cloud) Setup

You will use [Supabase Cloud](https://app.supabase.com) to track room occupancy and sensor health in real time.

### ✅ Step 1: Create a Supabase Project

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Click **New Project**
3. Fill in:
   - **Project Name**
   - **Database Password**
4. Click **Create Project**

After a few seconds, your project will be ready.

---

### ✅ Step 2: Create Required Tables

#### 📋 Table 1: `room_sensors`

Go to **Table Editor → New Table**

- **Name**: `room_sensors`
- **Columns**:

| Name           | Type        | Required | Default |
|----------------|-------------|----------|---------|
| room_id        | text        | ✅       |         |
| timestamp      | integer     | ✅       |         |
| datetime       | timestamptz | ✅       | `now()` |
| temperature    | numeric     | ✅       |         |
| humidity       | numeric     | ✅       |         |
| co2            | numeric     | ✅       |         |
| presence_state | text        | ✅       |         |
| power_data     | numeric     | ✅       |         |

- ✅ **Primary key**: `(room_id, timestamp)`

---

#### 📋 Table 2: `room_states`

- **Name**: `room_states`
- **Columns**:

| Name                 | Type        | Required | Default |
|----------------------|-------------|----------|---------|
| room_id              | text        | ✅       |         |
| is_occupied          | boolean     | ✅       |         |
| vacancy_last_updated | timestamptz | ✅       | `now()` |
| datapoint            | text        | ✅       |         |
| health_status        | text        | ✅       |         |
| datapoint_last_updated | timestamptz | ✅     | `now()` |

- ✅ **Primary key**: `(room_id, datapoint)`

---

### ✅ Step 3: Enable Realtime for Supabase Tables

1. Go to **SQL Editor**
2. Run this SQL:

```sql
ALTER PUBLICATION supabase_realtime ADD TABLE room_states;
```

> This allows the frontend to receive live updates from Supabase.

---

### ✅ Step 4: Configure Row-Level Security (RLS)

Supabase enables RLS by default. You must allow insert/update access to your tables.

1. Go to **room_sensors** → **RLS** tab → **+ New Policy**
2. Choose:
   - **Name**: `Allow All`
   - **Action**: `ALL`
   - **Role**: `public`
   - **Using Expression**: `true`
   - **With Check Expression**: `true`

3. Click **Enable Policy**

Repeat the same steps for the `room_states` table.

---

### ✅ Step 5: Get Supabase URL and Key

1. Go to **Project Settings → API**
2. Copy:
   - `SUPABASE_URL` → used in your `config.py`
   - `anon` key → used as your Supabase API key

Paste them into your `config.py` like so:

```python
SUPABASE_HTTP_CONFIG = {
    "url": "https://<your-project-id>.supabase.co",
    "key": "<your-anon-key>"
}
```

---

✅ Done! Your agents can now write to Supabase and your React dashboard can read data live.

---

### 7. Shutdown

```bash
docker-compose down
```

---

## 📊 Tech Stack

- Python 3.11
- RabbitMQ + aio-pika
- Supabase (Cloud)
- TimescaleDB
- React + Recharts (via NGINX)

---

## 👤 Author

Built with ❤️ by **Nyan**
