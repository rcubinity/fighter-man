# Sensor Hub - Developer Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Hardware Requirements](#hardware-requirements)
3. [BLE Sensors](#ble-sensors)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Running the System](#running-the-system)
7. [Architecture](#architecture)
8. [Data Flow](#data-flow)
9. [API Reference](#api-reference)
10. [Database Schema](#database-schema)
11. [Troubleshooting](#troubleshooting)

---

## Project Overview

### Purpose

Sensor Hub is a Raspberry Pi application that collects data from wearable BLE (Bluetooth Low Energy) sensors worn by firefighters during training. It captures foot pressure data and accelerometer/IMU data, then transmits this data to a central server for storage and AI/ML training.

### Key Features

- **BLE Sensor Connection** - Connects to multiple BLE sensors concurrently
- **Real-time Transmission** - Broadcasts data via Socket.IO to server
- **Offline Resilience** - Stores data in SQLite when network unavailable
- **Automatic Retry** - Background senders retry failed transmissions
- **Throttling** - Configurable data rate to manage bandwidth

### Technology Stack

| Component | Technology |
|-----------|------------|
| Platform | Raspberry Pi (Linux) |
| Language | Python 3.11+ |
| BLE Library | Bleak |
| Real-time | python-socketio |
| Local Storage | SQLite3 |
| Data Processing | NumPy |

---

## Hardware Requirements

### Raspberry Pi

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Model | Pi 3B+ | Pi 4 (2GB+) |
| OS | Raspberry Pi OS Lite | Raspberry Pi OS Lite (64-bit) |
| Bluetooth | Built-in BLE | Built-in BLE |
| Storage | 8 GB SD | 32 GB SD |

### BLE Sensors

| Sensor | Model | Purpose |
|--------|-------|---------|
| Foot Pressure | Custom insole sensors | Measure foot pressure distribution |
| Accelerometer | WT901BLE67 | Measure acceleration, gyroscope, angles |

---

## BLE Sensors

### Foot Pressure Sensor

**Communication Protocol:**
- Service UUID: `0000FFF0-0000-1000-8000-00805F9B34FB`
- Notify UUID: `0000FFF1-0000-1000-8000-00805F9B34FB`
- Write UUID: `0000FFF2-0000-1000-8000-00805F9B34FB`

**Data Format:**
```
Text protocol with newline delimiters
Format: L_[[v1,v2,v3,v4],[v5,v6,v7,v8],...]\n  (Left foot)
        R_[[v1,v2,v3,v4],[v5,v6,v7,v8],...]\n  (Right foot)

Total values: 24 (6 excluded positions = 18 active sensors)
Excluded indices: 8, 12, 16, 19, 20, 23
```

**Commands:**
| Command | Description |
|---------|-------------|
| `begin` | Start data collection |
| `end` | Stop data collection |

**Output Data Structure:**
```json
{
  "timestamp": "2025-12-01T10:30:00.100Z",
  "device": "LEFT_FOOT",
  "data": {
    "foot": "LEFT",
    "max": 150.5,
    "avg": 75.2,
    "active_count": 12,
    "values": [10.0, 20.5, 30.2, 40.1, 50.5, 60.3, 70.8, 80.2, 90.1, 100.5, 110.2, 120.3, 130.1, 140.5, 145.2, 148.3, 150.0, 149.5]
  }
}
```

### Accelerometer (WT901BLE67)

**Communication Protocol:**
- Notify UUID: `0000FFE4-0000-1000-8000-00805F9B34FB` or `0000FFF1-0000-1000-8000-00805F9B34FB`
- Write UUID: `0000FFE9-0000-1000-8000-00805F9B34FB` or `0000FFF2-0000-1000-8000-00805F9B34FB`

**Data Format:**
```
Binary protocol (20 bytes per packet)
[0]: 0x55 (header)
[1]: 0x61 (combined packet type)
[2-7]: Accelerometer X,Y,Z (3 signed shorts, little-endian)
[8-13]: Gyroscope X,Y,Z (3 signed shorts, little-endian)
[14-19]: Angles Roll,Pitch,Yaw (3 signed shorts, little-endian)

Conversion:
- Accelerometer: value / 32768.0 * 16 (±16g range)
- Gyroscope: value / 32768.0 * 2000 (±2000°/s range)
- Angles: value / 32768.0 * 180 (±180° range)
```

**Keep-alive Command:**
```python
bytes([0xff, 0xaa, 0x27, 0x3A, 0x00])  # Send every 1 second
```

**Output Data Structure:**
```json
{
  "timestamp": "2025-12-01T10:30:00.050Z",
  "device": "ACCELEROMETER",
  "data": {
    "acc": {"x": 0.1, "y": -0.2, "z": 9.8},
    "gyro": {"x": 1.5, "y": -2.3, "z": 0.5},
    "angle": {"roll": 5.2, "pitch": -3.1, "yaw": 180.0}
  }
}
```

---

## Installation

### Step 1: System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Bluetooth dependencies
sudo apt install -y bluetooth bluez python3-pip python3-venv

# Enable Bluetooth
sudo systemctl enable bluetooth
sudo systemctl start bluetooth
```

### Step 2: Clone Repository

```bash
cd ~
git clone <repository-url>
cd sensor-hub
```

### Step 3: Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Find Sensor MAC Addresses

```bash
# Run BLE scanner
sudo python scanner.py

# Output example:
# ======================================================================
# Found 5 unique BLE device(s)
# ======================================================================
# MAC Address          Device Name               Signal
# ----------------------------------------------------------------------
# ed:63:5b:c4:2d:92    FSR-L                     -45 dBm (Excellent)
# c7:f7:92:82:f2:f9    WT901BLE67                -52 dBm (Excellent)
# ======================================================================
```

### Step 5: Configure Environment

```bash
# Edit .env file
nano .env
```

Update MAC addresses and server URL:
```bash
LEFT_FOOT_MAC=ed:63:5b:c4:2d:92
RIGHT_FOOT_MAC=XX:XX:XX:XX:XX:XX
ACCELEROMETER_MAC=c7:f7:92:82:f2:f9
SOCKETIO_SERVER_URL=http://your-server:4100
```

---

## Configuration

### Environment Variables (.env)

#### BLE Sensor Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LEFT_FOOT_MAC` | (required) | MAC address of left foot sensor |
| `RIGHT_FOOT_MAC` | XX:XX:XX:XX:XX:XX | MAC address of right foot sensor |
| `ACCELEROMETER_MAC` | (required) | MAC address of accelerometer |
| `FOOT_THROTTLE` | 2 | Process every Nth foot packet (1=all) |
| `ACCEL_THROTTLE` | 5 | Process every Nth accel packet (1=all) |
| `CONNECTION_RETRIES` | 3 | Max BLE connection attempts |

#### Socket.IO Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SOCKETIO_SERVER_URL` | http://localhost:4100 | Server URL |
| `SOCKETIO_DEVICE_KEY` | firefighter_pi_001 | Device authentication key |
| `SOCKETIO_ENABLED` | true | Enable/disable Socket.IO |
| `SOCKETIO_NAMESPACE` | /iot | Socket.IO namespace |

#### Database Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_FOOT_FILE` | ./database/foot.db | Foot sensor database path |
| `DB_ACCEL_FILE` | ./database/accel.db | Accelerometer database path |

#### Sender Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SENDER_POLLING_INTERVAL` | 30 | Seconds between retry attempts |
| `SENDER_MAX_RECORDS` | 100 | Records per batch |
| `SENDER_RETRY_BACKOFF_BASE` | 60 | Initial retry delay (seconds) |
| `SENDER_MAX_BACKOFF` | 3600 | Maximum retry delay (seconds) |

#### HTTP Fallback

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBHOOK_FOOT_URLS` | (empty) | Comma-separated HTTP endpoints |
| `WEBHOOK_ACCEL_URLS` | (empty) | Comma-separated HTTP endpoints |

### Sample .env File

```bash
# BLE Device MAC Addresses
LEFT_FOOT_MAC=ed:63:5b:c4:2d:92
RIGHT_FOOT_MAC=XX:XX:XX:XX:XX:XX
ACCELEROMETER_MAC=c7:f7:92:82:f2:f9

# Performance Tuning
FOOT_THROTTLE=2
ACCEL_THROTTLE=5
CONNECTION_RETRIES=3

# Socket.IO Server
SOCKETIO_SERVER_URL=http://192.168.1.100:4100
SOCKETIO_DEVICE_KEY=firefighter_pi_001
SOCKETIO_ENABLED=true
SOCKETIO_NAMESPACE=/iot

# HTTP Fallback
WEBHOOK_FOOT_URLS=http://192.168.1.100:4100/api/foot
WEBHOOK_ACCEL_URLS=http://192.168.1.100:4100/api/accel

# SQLite Database
DB_FOOT_FILE=./database/foot.db
DB_ACCEL_FILE=./database/accel.db

# Sender Settings
SENDER_POLLING_INTERVAL=30
SENDER_MAX_RECORDS=100
SENDER_RETRY_BACKOFF_BASE=60
SENDER_MAX_BACKOFF=3600
```

---

## Running the System

### Option 1: Main Application (Recommended)

Runs sensor collection with SQLite storage and Socket.IO broadcast:

```bash
# Activate environment
source venv/bin/activate

# Run main application
sudo python main.py
```

**Note:** `sudo` is required for BLE access on Raspberry Pi.

### Option 2: Background Senders (Separate Processes)

For retrying failed transmissions:

```bash
# Terminal 1: Main sensor collection
sudo python main.py

# Terminal 2: Foot data sender
python send_foot_data.py

# Terminal 3: Accel data sender
python send_accel_data.py
```

### Option 3: Using Supervisor (Production)

Create supervisor config `/etc/supervisor/conf.d/sensor-hub.conf`:

```ini
[program:sensor-hub]
command=/home/pi/sensor-hub/venv/bin/python main.py
directory=/home/pi/sensor-hub
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/sensor-hub.err.log
stdout_logfile=/var/log/sensor-hub.out.log

[program:send-foot-data]
command=/home/pi/sensor-hub/venv/bin/python send_foot_data.py
directory=/home/pi/sensor-hub
user=pi
autostart=true
autorestart=true
stderr_logfile=/var/log/send-foot.err.log
stdout_logfile=/var/log/send-foot.out.log

[program:send-accel-data]
command=/home/pi/sensor-hub/venv/bin/python send_accel_data.py
directory=/home/pi/sensor-hub
user=pi
autostart=true
autorestart=true
stderr_logfile=/var/log/send-accel.err.log
stdout_logfile=/var/log/send-accel.out.log
```

Start supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

### Option 4: Systemd Service

Create `/etc/systemd/system/sensor-hub.service`:

```ini
[Unit]
Description=Sensor Hub BLE Monitor
After=bluetooth.target network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/sensor-hub
ExecStart=/home/pi/sensor-hub/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sensor-hub
sudo systemctl start sensor-hub
```

---

## Architecture

### Directory Structure

```
sensor-hub/
├── main.py                      # Main entry point
├── scanner.py                   # BLE device scanner utility
├── sensors/                     # BLE sensor interfaces
│   ├── __init__.py
│   ├── foot_sensor.py           # Foot pressure sensor class
│   ├── accel_sensor.py          # Accelerometer sensor class
│   └── parsers.py               # Data parsing functions
├── lib/                         # Shared utilities
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   ├── socket_client.py         # Socket.IO client
│   └── database/                # SQLite layer
│       ├── __init__.py
│       ├── base.py              # Abstract database class
│       ├── foot_db.py           # Foot sensor database
│       └── accel_db.py          # Accelerometer database
├── senders/                     # Background transmission
│   ├── __init__.py
│   ├── base.py                  # Base sender class
│   ├── foot_sender.py           # Foot data sender
│   └── accel_sender.py          # Accelerometer sender
├── send_foot_data.py            # Foot sender entry point
├── send_accel_data.py           # Accel sender entry point
├── database/                    # SQLite files (runtime)
│   ├── foot.db
│   └── accel.db
├── tests/                       # Test scripts
│   ├── __init__.py
│   └── test_database.py
├── docs/                        # Documentation
├── requirements.txt             # Python dependencies
├── .env                         # Configuration
└── run_tests.sh                 # Test runner
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         SENSOR HUB                              │
│                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│  │ FootSensor  │     │ AccelSensor │     │   Scanner   │       │
│  │   (BLE)     │     │   (BLE)     │     │  (Utility)  │       │
│  └──────┬──────┘     └──────┬──────┘     └─────────────┘       │
│         │                   │                                   │
│         ▼                   ▼                                   │
│  ┌─────────────────────────────────────────┐                   │
│  │              main.py                     │                   │
│  │  - Connects to sensors                   │                   │
│  │  - Handles data callbacks                │                   │
│  │  - Stores in SQLite                      │                   │
│  │  - Broadcasts via Socket.IO              │                   │
│  └─────────────────────────────────────────┘                   │
│         │                   │                                   │
│         ▼                   ▼                                   │
│  ┌─────────────┐     ┌─────────────┐                           │
│  │  SQLite DB  │     │ Socket.IO   │──────▶ To Server          │
│  │  (Backup)   │     │  Client     │                           │
│  └──────┬──────┘     └─────────────┘                           │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────┐                   │
│  │         Background Senders               │                   │
│  │  - Fetch unsent records                  │                   │
│  │  - Retry with exponential backoff        │                   │
│  │  - Mark as sent on success               │                   │
│  └─────────────────────────────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Normal Operation (Network Available)

```
1. BLE Sensor emits data
        │
        ▼
2. Sensor class receives notification
        │
        ▼
3. Parser converts raw data to dict
        │
        ▼
4. Data callback in main.py
        │
        ├──────────────────────┐
        ▼                      ▼
5. Store in SQLite      6. Emit via Socket.IO
   (backup)                    │
        │                      ▼
        │              7. Server receives
        │                      │
        ▼                      ▼
8. Mark as sent         8. Store in Qdrant
   (eventually)
```

### Offline Operation (Network Unavailable)

```
1. BLE Sensor emits data
        │
        ▼
2. Data callback in main.py
        │
        ├──────────────────────┐
        ▼                      ▼
3. Store in SQLite      4. Socket.IO fails
   (records accumulate)       │
        │                     ▼
        │              5. Data stays in
        │                 SQLite (sent=0)
        ▼
6. Background sender polls
        │
        ▼
7. Fetch unsent records
        │
        ▼
8. Retry transmission
        │
        ├─── Success ──▶ Mark sent=1
        │
        └─── Failure ──▶ Wait (exponential backoff)
                              │
                              ▼
                        Retry later
```

---

## API Reference

### FootSensor Class

```python
from sensors import FootSensor

sensor = FootSensor(
    mac_address="ed:63:5b:c4:2d:92",
    device_name="LEFT_FOOT",
    data_callback=async_callback_function,  # Optional
    throttle=2,                              # Process every 2nd packet
    max_retries=3                            # Connection attempts
)

# Methods
await sensor.connect()           # Connect to BLE device
await sensor.start_monitoring()  # Start receiving data
await sensor.stop_monitoring()   # Stop and disconnect
await sensor.monitor_loop()      # Full lifecycle (connect + monitor)
```

### AccelSensor Class

```python
from sensors import AccelSensor

sensor = AccelSensor(
    mac_address="c7:f7:92:82:f2:f9",
    device_name="ACCELEROMETER",
    data_callback=async_callback_function,  # Optional
    throttle=5,                              # Process every 5th packet
    max_retries=3                            # Connection attempts
)

# Methods (same as FootSensor)
await sensor.connect()
await sensor.start_monitoring()
await sensor.stop_monitoring()
await sensor.monitor_loop()
```

### SocketIOClient Class

```python
from lib.socket_client import SocketIOClient

client = SocketIOClient(
    server_url="http://localhost:4100",
    device_key="firefighter_pi_001",
    namespace="/iot"
)

# Methods
client.connect()                    # Connect to server
client.emit("event_name", data)     # Send data
client.disconnect()                 # Disconnect

# Properties
client.connected                    # bool: Connection status
client.authenticated                # bool: Auth status
```

### Database Classes

```python
from lib.database.foot_db import FootDatabase
from lib.database.accel_db import AccelDatabase

# Initialize
foot_db = FootDatabase("./database/foot.db")
accel_db = AccelDatabase("./database/accel.db")

# Methods
db.save_record(record_dict)         # Save sensor reading
db.fetch_batch(limit=100)           # Get unsent records
db.mark_sent([id1, id2, ...])       # Mark records as sent
db.count_unsent()                   # Count pending records
db.count_total()                    # Count all records
db.delete_sent(older_than_hours=24) # Cleanup old records
db.transform_for_send(row)          # Convert row to send format
```

---

## Database Schema

### foot_readings Table

```sql
CREATE TABLE foot_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,        -- ISO datetime
    device TEXT NOT NULL,           -- LEFT_FOOT or RIGHT_FOOT
    foot TEXT NOT NULL,             -- LEFT or RIGHT
    max_pressure REAL,              -- Maximum pressure value
    avg_pressure REAL,              -- Average pressure value
    active_count INTEGER,           -- Number of active sensors
    values_json TEXT,               -- JSON array of 18 values
    sent INTEGER DEFAULT 0          -- 0=unsent, 1=sent
);

CREATE INDEX idx_foot_sent ON foot_readings(sent, id);
```

### accel_readings Table

```sql
CREATE TABLE accel_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,        -- ISO datetime
    device TEXT NOT NULL,           -- ACCELEROMETER
    acc_x REAL,                     -- Acceleration X (g)
    acc_y REAL,                     -- Acceleration Y (g)
    acc_z REAL,                     -- Acceleration Z (g)
    gyro_x REAL,                    -- Gyroscope X (°/s)
    gyro_y REAL,                    -- Gyroscope Y (°/s)
    gyro_z REAL,                    -- Gyroscope Z (°/s)
    roll REAL,                      -- Roll angle (°)
    pitch REAL,                     -- Pitch angle (°)
    yaw REAL,                       -- Yaw angle (°)
    sent INTEGER DEFAULT 0          -- 0=unsent, 1=sent
);

CREATE INDEX idx_accel_sent ON accel_readings(sent, id);
```

---

## Troubleshooting

### BLE Connection Issues

**Error:** `Device not found during scan`

**Solutions:**
1. Ensure sensor is powered on and in range
2. Check MAC address is correct in .env
3. Run with sudo: `sudo python main.py`
4. Restart Bluetooth: `sudo systemctl restart bluetooth`
5. Check Bluetooth is enabled: `bluetoothctl power on`

---

**Error:** `Connection attempt failed`

**Solutions:**
1. Move Pi closer to sensor
2. Increase `CONNECTION_RETRIES` in .env
3. Check for interference from other BLE devices
4. Try resetting the sensor

---

**Error:** `Notification error` or `BLE stack overload`

**Solutions:**
1. Increase throttle values (`FOOT_THROTTLE`, `ACCEL_THROTTLE`)
2. Add delay between sensor connections (already in code)
3. Reduce number of concurrent sensors
4. Reboot Raspberry Pi

---

### Socket.IO Connection Issues

**Error:** `Connection failed` or `Connection refused`

**Solutions:**
1. Verify server URL in .env is correct
2. Check server is running: `curl http://server:4100/health`
3. Check firewall allows outbound connections
4. Verify network connectivity: `ping server`

---

**Error:** `Authentication failed`

**Solutions:**
1. Check `SOCKETIO_DEVICE_KEY` matches server's `ALLOWED_DEVICE_KEYS`
2. Verify server allows the device key

---

### Database Issues

**Error:** `Database locked`

**Solutions:**
1. Ensure only one process writes at a time
2. Check disk space: `df -h`
3. Delete old database and restart

---

**Error:** `Disk full`

**Solutions:**
1. Run cleanup: Records are auto-deleted after 24 hours
2. Manually delete: `rm database/*.db`
3. Reduce data rate with higher throttle values

---

### Performance Issues

**Problem:** High CPU usage

**Solutions:**
1. Increase throttle values
2. Check for runaway processes: `top`
3. Reduce sensor count

---

**Problem:** Memory growing

**Solutions:**
1. Check for memory leaks with `htop`
2. Restart application periodically
3. Reduce buffer sizes

---

### Testing

**Run database tests:**
```bash
./run_tests.sh
```

**Manual BLE test:**
```bash
# Scan for devices
sudo python scanner.py

# Test single sensor connection
sudo python -c "
import asyncio
from sensors import FootSensor

async def test():
    sensor = FootSensor('ed:63:5b:c4:2d:92', 'TEST')
    if await sensor.connect():
        print('Connected!')
        await sensor.stop_monitoring()
    else:
        print('Failed to connect')

asyncio.run(test())
"
```

---

## Support

For issues or questions:
1. Check this documentation
2. Review log output for error messages
3. Check `todo.md` for known issues
4. Contact development team

---

**Document Version:** 1.0
**Last Updated:** December 1, 2025
