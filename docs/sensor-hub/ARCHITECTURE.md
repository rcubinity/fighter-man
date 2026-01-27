# Sensor-Hub System Architecture

## Overview

The sensor-hub is a production-ready IoT data collection pipeline designed for supervised machine learning. It collects real-time sensor data from BLE (Bluetooth Low Energy) devices and transmits it to a centralized server for storage and future ML model training.

**Key Design Principle:** This system is **pure data collection** with no onboard intelligence. Activity detection and classification are deferred to future ML development after sufficient training data has been collected.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      BLE SENSORS (Wearables)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Left Foot    │  │ Right Foot   │  │ Accelerometer (IMU)    │   │
│  │ Pressure     │  │ Pressure     │  │ WT901BLE67             │   │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘   │
│         │                  │                       │                 │
│         └──────────────────┼───────────────────────┘                 │
│                            │ BLE Protocol                            │
└────────────────────────────┼─────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              RASPBERRY PI (sensor-hub)                              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  main.py (Entry Point)                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐   │  │
│  │  │ FootSensor  │  │ FootSensor  │  │  AccelSensor      │   │  │
│  │  │ (Left)      │  │ (Right)     │  │  (WT901BLE67)     │   │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────────┬────────┘   │  │
│  │         │                 │                     │            │  │
│  │         └─────────────────┼─────────────────────┘            │  │
│  │                           ▼                                  │  │
│  │              ┌────────────────────────┐                      │  │
│  │              │  Data Parsers          │                      │  │
│  │              │  - parse_foot_data()   │                      │  │
│  │              │  - parse_accel_data()  │                      │  │
│  │              └────────────┬───────────┘                      │  │
│  │                           │                                  │  │
│  │              ┌────────────▼───────────┐                      │  │
│  │              │  Throttle & Format     │                      │  │
│  │              │  (Reduce data rate)    │                      │  │
│  │              └────────────┬───────────┘                      │  │
│  └────────────────────────────┼──────────────────────────────────┘  │
│                               │                                     │
│            ┌──────────────────┼──────────────────┐                  │
│            │                  │                  │                  │
│            ▼                  ▼                  ▼                  │
│  ┌─────────────────┐  ┌─────────────┐  ┌─────────────────┐        │
│  │ SQLite Database │  │ Socket.IO   │  │ stdout (JSON)   │        │
│  │ (Backup Buffer) │  │ Client      │  │ (Logging)       │        │
│  │                 │  │ Real-time   │  │                 │        │
│  │ foot.db         │  │ Broadcast   │  │                 │        │
│  │ accel.db        │  │ to Server   │  │                 │        │
│  └─────────┬───────┘  └──────┬──────┘  └─────────────────┘        │
│            │                  │                                     │
│            │                  │                                     │
│  ┌─────────▼──────────────────┼─────────────────────────┐          │
│  │  Background Batch Senders  │                         │          │
│  │  - send_foot_data.py       │                         │          │
│  │  - send_accel_data.py      │                         │          │
│  │  (Retry failed transmissions)                        │          │
│  └────────────────────────────┼─────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
                                │ Socket.IO + HTTP Fallback
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   FIREFIGHTER-SERVER                                │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Flask + Socket.IO Server (Python)                            │ │
│  │  - Receives real-time sensor streams                          │ │
│  │  - Accumulates data into 500ms time windows                   │ │
│  │  - Converts to 270-dimension vectors                          │ │
│  └───────────────────────────┬───────────────────────────────────┘ │
│                               │                                     │
│            ┌──────────────────┼──────────────────┐                  │
│            │                  │                  │                  │
│            ▼                  ▼                  ▼                  │
│  ┌─────────────────┐  ┌─────────────┐  ┌─────────────────┐        │
│  │ PostgreSQL      │  │ Qdrant      │  │ REST API        │        │
│  │ Session         │  │ Vector DB   │  │ /api/sessions   │        │
│  │ Metadata        │  │             │  │ (Management)    │        │
│  │                 │  │ Sensor      │  │                 │        │
│  │ - id            │  │ Vectors     │  │                 │        │
│  │ - name          │  │ 270-dim     │  │                 │        │
│  │ - activity_type │  │             │  │                 │        │
│  │ - timestamps    │  │             │  │                 │        │
│  └─────────────────┘  └─────────────┘  └─────────────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### 1. BLE Sensors (Hardware Layer)

**Foot Pressure Sensors (Left & Right)**
- Measure foot pressure distribution at 18 points per foot
- Transmit text protocol data via BLE
- Service UUID: `0000FFF0-...`

**Accelerometer (WT901BLE67)**
- 9-axis IMU (accelerometer + gyroscope + angles)
- Transmit binary protocol data via BLE
- Service UUID: Auto-detected (`ffe4` or `fff1` variant)
- Requires 1Hz keep-alive commands

### 2. Raspberry Pi (sensor-hub)

**Main Process (main.py)**
- Orchestrates concurrent sensor connections
- Priority connection: Left foot → Right foot → Accelerometer
- 3-second delays between connections to avoid BLE stack overload
- Runs sensors concurrently using asyncio.gather()

**Sensor Classes**
- `FootSensor` (`sensors/foot_sensor.py`): Handles foot pressure BLE communication
- `AccelSensor` (`sensors/accel_sensor.py`): Handles accelerometer BLE communication
- Both follow same interface: `connect()` → `start_monitoring()` → `monitor_loop()`

**Data Parsers** (`sensors/parsers.py`)
- `parse_foot_data()`: Text protocol → JSON (18 active sensors, max, avg, count)
- `parse_accel_data()`: Binary 20-byte packets → JSON (acc, gyro, angles)

**Storage Layer**
- `lib/database/foot_db.py`: SQLite backup for foot data
- `lib/database/accel_db.py`: SQLite backup for accelerometer data
- Write-ahead logging: Always persist before transmission

**Network Layer**
- `lib/socket_client.py`: Socket.IO client with auto-reconnection
- Real-time broadcast to server at `/iot` namespace
- Device authentication with device_key

**Background Senders**
- `send_foot_data.py`: Batch retry process for foot data
- `send_accel_data.py`: Batch retry process for accelerometer data
- Poll SQLite every 30s for unsent records
- Exponential backoff on failures (60s → 3600s max)

### 3. Firefighter-Server

**Data Reception**
- Flask + Socket.IO server listening at `http://localhost:4100`
- Namespace: `/iot`
- Events: `foot_pressure_data`, `accelerometer_data`

**Data Processing**
- Accumulate readings into 500ms time windows
- Convert to vectors:
  - Foot: 18 sensors × 10 readings = 180 dimensions
  - Accel: 9 values × 10 readings = 90 dimensions
  - Total: 270-dimension vectors

**Storage Strategy**
- **PostgreSQL**: Session metadata (id, name, activity_type, timestamps, status)
- **Qdrant**: Sensor vectors (270-dim) with session_id tags
- **Separation Rationale**: SQL for queries, vector DB for similarity search

**REST API**
- Session management: Create, list, get, update, delete, stop
- Activity types: Walking, Running, Crawling, Climbing, Standing, etc.
- Export: CSV/JSON for ML training

---

## Data Flow Paths

### Path 1: Real-time Streaming (Normal Operation)

```
1. BLE Sensor → Notification
   └─> Fragmented packets arrive at Raspberry Pi

2. Raspberry Pi: Accumulate & Parse
   └─> FootSensor/AccelSensor accumulates packets in buffer
   └─> Parse complete packets (newline for foot, 20 bytes for accel)

3. Throttle
   └─> Foot: Process every 2nd packet (~10 Hz from ~20 Hz)
   └─> Accel: Process every 5th packet (~20 Hz from ~100 Hz)

4. Format Output
   └─> Create JSON payload with timestamp and device identifier

5. Dual Storage
   a) SQLite: ALWAYS save (backup buffer)
      └─> INSERT with sent=0 (unsent flag)

   b) Socket.IO: Attempt real-time broadcast
      └─> Emit to server at /iot namespace
      └─> Fire-and-forget (no acknowledgment)

6. Server Receives
   └─> Accumulate into 500ms windows
   └─> Store in Qdrant as 270-dim vector
   └─> Associate with active PostgreSQL session
```

### Path 2: Batch Retry (Network Failure Recovery)

```
1. Polling Loop (every 30s)
   └─> send_foot_data.py / send_accel_data.py processes run

2. Fetch Unsent Records
   └─> SELECT * FROM {table} WHERE sent = 0 LIMIT 100

3. Transmit via Dual Path
   a) Socket.IO (Primary)
      └─> Emit each record individually

   b) HTTP Webhook (Fallback)
      └─> POST batch to configured URLs
      └─> 10s timeout per URL

4. Mark Success
   └─> UPDATE sent = 1 WHERE id IN (...)

5. Exponential Backoff on Failure
   └─> Delay = 60s × (2 ^ consecutive_failures)
   └─> Max delay: 3600s (1 hour)

6. Cleanup
   └─> DELETE WHERE sent = 1 AND timestamp < NOW() - 24 hours
```

---

## Key Design Patterns

### 1. Write-Ahead Logging
**Guarantee:** No data loss even if network fails

```python
# Always write to SQLite BEFORE Socket.IO
foot_db.save_record(data)       # Persistent backup
socket_client.emit(...)          # Attempt real-time (may fail)
```

### 2. Graceful Degradation
**Fallback Hierarchy:**
1. **Primary**: Real-time Socket.IO broadcast
2. **Fallback 1**: Background batch retry via Socket.IO
3. **Fallback 2**: HTTP webhook transmission

### 3. Throttling at Source
**Purpose**: Reduce bandwidth and processing load

- BLE sensors produce high-frequency data (20-100 Hz)
- Raspberry Pi throttles at packet level
- Configurable per sensor type
- Trade-off: Lower data rate for reliability

### 4. Dual-Path Transmission
**Independence**: Real-time and batch processes are decoupled

- `main.py`: Real-time collection + immediate broadcast
- `send_*.py`: Independent batch retry processes
- Both can run simultaneously without interference

### 5. Priority Connection
**Rationale**: Critical sensors connect first

```python
# Connection sequence in main.py
1. Left foot (highest priority - most important)
2. Wait 3s
3. Right foot
4. Wait 3s
5. Accelerometer (lower priority)
```

---

## Data Storage Strategy

### Raspberry Pi (sensor-hub)

**SQLite Databases**
- **Location**: `./database/foot.db`, `./database/accel.db`
- **Purpose**: Backup buffer for network failures
- **Retention**: 24 hours after successful transmission
- **Schema**:
  - `foot_readings`: timestamp, device, foot, max, avg, active_count, values_json, sent
  - `accel_readings`: timestamp, device, acc_x/y/z, gyro_x/y/z, roll/pitch/yaw, sent

### Server (firefighter-server)

**PostgreSQL**
- **Purpose**: Session metadata (queryable, exportable)
- **Schema**: id, name, activity_type, created_at, stopped_at, status, updated_at
- **Indexes**: status, activity_type, created_at, (status, activity_type)

**Qdrant Vector Database**
- **Purpose**: Sensor data vectors for similarity search
- **Collection**: `sensor_windows`
- **Dimensions**: 270 (180 foot + 90 accel)
- **Payload**: session_id, start_time, end_time, window_id, labels

---

## Configuration

### Environment Variables

**Raspberry Pi (.env)**
```bash
# BLE Sensors
LEFT_FOOT_MAC=XX:XX:XX:XX:XX:XX
RIGHT_FOOT_MAC=XX:XX:XX:XX:XX:XX
ACCELEROMETER_MAC=XX:XX:XX:XX:XX:XX

# Performance Tuning
FOOT_THROTTLE=2              # Every 2nd packet (~10 Hz)
ACCEL_THROTTLE=5             # Every 5th packet (~20 Hz)
CONNECTION_RETRIES=3         # Max connection attempts

# Socket.IO
SOCKETIO_SERVER_URL=http://localhost:4100
SOCKETIO_DEVICE_KEY=firefighter_pi_001
SOCKETIO_NAMESPACE=/iot
SOCKETIO_ENABLED=true

# Database
DB_FOOT_FILE=./database/foot.db
DB_ACCEL_FILE=./database/accel.db

# Background Senders
SENDER_POLLING_INTERVAL=30   # Seconds
SENDER_MAX_RECORDS=100       # Batch size
```

**Server (.env)**
```bash
# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=4100

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=firefighter

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=sensor_windows
VECTOR_DIMENSION=270
WINDOW_SIZE_MS=500
```

---

## Performance Characteristics

### Data Rates

**Native Sensor Rates:**
- Foot sensors: ~20 Hz per foot
- Accelerometer: ~100 Hz

**Effective Rates (After Throttling):**
- Foot sensors: ~10 Hz per foot (throttle=2)
- Accelerometer: ~20 Hz (throttle=5)
- **Total**: ~40 data points/second from Raspberry Pi

**Network Bandwidth:**
- Foot JSON payload: ~200 bytes
- Accel JSON payload: ~150 bytes
- Total: ~14 KB/second sustained

### Latency

**Real-time Mode:**
- BLE notification → Server: < 100ms typical
- End-to-end: < 200ms

**Batch Retry Mode:**
- Polling interval: 30 seconds
- Backlog processing: 100 records per batch

---

## Error Handling

### Connection Failures

**BLE Connection:**
- Retry 3 times with 3-second delays
- Log errors and continue with available sensors
- Graceful degradation: System works with partial sensors

**Socket.IO Connection:**
- Infinite auto-reconnection attempts
- Exponential backoff: 5s → 60s max
- SQLite buffer ensures no data loss during downtime

### Data Integrity

**Packet Validation:**
- Foot: Validate newline delimiter and 24 values
- Accel: Validate 20-byte length and header (0x55 0x61)
- Discard malformed packets

**Database Constraints:**
- NOT NULL on critical fields
- Indexed for query performance
- Automatic cleanup of old data

---

## Deployment

### Raspberry Pi Setup

```bash
cd sensor-hub
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure .env with MAC addresses
# Run main process
python3 main.py

# Run background senders (separate terminals)
python3 send_foot_data.py
python3 send_accel_data.py
```

### Server Setup

```bash
cd firefighter-server
docker-compose up -d  # Starts PostgreSQL + Qdrant + Server
```

---

## Monitoring

### Raspberry Pi

**Logs:**
- stdout: JSON formatted sensor data
- Console: Connection status, errors

**Database Metrics:**
```python
# Check unsent records
SELECT COUNT(*) FROM foot_readings WHERE sent = 0;
SELECT COUNT(*) FROM accel_readings WHERE sent = 0;
```

### Server

**Health Endpoint:**
```bash
curl http://localhost:4100/health
```

**Response:**
```json
{
  "status": "healthy",
  "server": "running",
  "qdrant": {"status": "healthy"},
  "postgres": {"status": "healthy"},
  "active_session": "session-uuid-here"
}
```

---

## Future Enhancements

### Stage 2: Pattern Analysis
- Analyze collected data to identify activity signatures
- Set thresholds (e.g., "crawling = horizontal angles")

### Stage 3: ML Model Training
- Export labeled data from Qdrant
- Train LSTM/CNN for activity classification
- Validate model accuracy

### Stage 4: Real-time Inference
- Deploy trained model to Raspberry Pi or Server
- Classify activities in real-time
- Confidence scores and uncertainty handling

---

## Related Documentation

- [SENSOR_SPECIFICATIONS.md](./SENSOR_SPECIFICATIONS.md) - Detailed sensor hardware specs
- [DATA_DICTIONARY.md](./DATA_DICTIONARY.md) - Complete data field reference
- [ACTIVITY_DETECTION_GUIDE.md](./ACTIVITY_DETECTION_GUIDE.md) - ML feature engineering guide
- [ML_INTEGRATION.md](./ML_INTEGRATION.md) - ML pipeline integration
