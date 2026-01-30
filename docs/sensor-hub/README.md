# Sensor Hub

Python application for collecting data from wearable BLE sensors and transmitting to the firefighter-server. Designed to run on a Raspberry Pi in the field.

## Overview

The sensor hub connects to three BLE sensors worn by firefighters:
- **Left Foot Pressure Sensor** - 18 pressure points
- **Right Foot Pressure Sensor** - 18 pressure points
- **WT901BLE67 Accelerometer/IMU** - Acceleration, gyroscope, angles

Data is:
1. Stored locally in SQLite (backup buffer)
2. Transmitted in real-time via Socket.IO
3. Retry-queued if connection fails

## Quick Start

### Prerequisites

- Python 3.7+
- Bluetooth adapter with BLE support
- Raspberry Pi or Linux system (BLE libraries are Linux-focused)

### 1. Install Dependencies

```bash
cd sensor-hub
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file with sensor MAC addresses:

```bash
# BLE Sensor MAC Addresses
LEFT_FOOT_MAC=AA:BB:CC:DD:EE:01
RIGHT_FOOT_MAC=AA:BB:CC:DD:EE:02
ACCELEROMETER_MAC=AA:BB:CC:DD:EE:03

# Socket.IO Server
SOCKET_SERVER_URL=http://192.168.1.100:4100
SOCKET_DEVICE_KEY=firefighter_pi_001
SOCKET_ENABLED=true

# Throttling (reduce data rate)
FOOT_THROTTLE=1       # Process every Nth packet (1 = no throttling)
ACCEL_THROTTLE=5      # 100Hz -> 20Hz

# Connection Retries
CONNECTION_RETRIES=3
```

### 3. Run the Sensor Hub

```bash
python main.py
```

The hub will:
1. Connect to each sensor with staggered delays (BLE stack stability)
2. Begin monitoring and transmitting data
3. Buffer locally if server is unreachable

## Project Structure

```
sensor-hub/
├── main.py                    # Entry point, orchestrates monitoring
├── sensors/
│   ├── __init__.py            # Exports FootSensor, AccelSensor
│   ├── ble_sensor_base.py     # Abstract base class for BLE sensors
│   ├── foot_sensor.py         # Foot pressure sensor implementation
│   ├── accel_sensor.py        # Accelerometer sensor implementation
│   ├── constants.py           # BLE protocol constants
│   └── parsers.py             # Data parsing functions
├── lib/
│   ├── config.py              # Configuration management
│   ├── socket_client.py       # Socket.IO client wrapper
│   └── database/
│       ├── base.py            # SQLite base class
│       ├── foot_db.py         # Foot data storage
│       └── accel_db.py        # Accel data storage
├── senders/
│   ├── base.py                # Background retry sender base
│   ├── foot_sender.py         # Foot data retry sender
│   └── accel_sender.py        # Accel data retry sender
└── scanner.py                 # BLE device scanner utility
```

## Sensor Hardware

### Foot Pressure Sensors

| Specification | Value |
|---------------|-------|
| Protocol | BLE with text-based UART |
| Data Format | Comma-separated values (18 sensors) |
| Sample Rate | ~30 Hz |
| Output | Pressure values (0-100 scale) |

Commands:
- `begin` - Start data transmission
- `end` - Stop data transmission

### WT901BLE67 Accelerometer

| Specification | Value |
|---------------|-------|
| Protocol | BLE with binary packets |
| Packet Size | 20 bytes |
| Sample Rate | ~100 Hz (throttled to 20 Hz) |
| Output | Acceleration (g), Gyroscope (deg/s), Angles (deg) |

The device requires periodic keep-alive commands to maintain connection.

## Data Output Format

### Foot Pressure Data

```json
{
  "timestamp": "2025-01-30T14:30:22.100",
  "device": "LEFT_FOOT",
  "data": {
    "foot": "LEFT",
    "values": [12.3, 45.6, 78.9, ...],
    "max": 89.2,
    "avg": 34.5,
    "active_count": 15
  }
}
```

### Accelerometer Data

```json
{
  "timestamp": "2025-01-30T14:30:22.150",
  "device": "ACCELEROMETER",
  "data": {
    "acc": {"x": 0.12, "y": -0.34, "z": 9.81},
    "gyro": {"x": 1.23, "y": -0.45, "z": 0.67},
    "angle": {"roll": 2.34, "pitch": -1.56, "yaw": 45.78}
  }
}
```

## Scanning for Devices

Use the scanner utility to find BLE devices:

```bash
python scanner.py
```

This will list all discoverable BLE devices with their MAC addresses and names.

## Troubleshooting

### Device Not Found

1. Ensure Bluetooth is enabled: `bluetoothctl power on`
2. Check device is advertising: `bluetoothctl scan on`
3. Verify MAC address in `.env` is correct
4. Try increasing `BLE_SCAN_TIMEOUT` in constants

### Connection Drops Frequently

1. Move closer to the sensor
2. Reduce interference from other BLE devices
3. Increase `CONNECTION_RETRIES` setting
4. Check battery level on sensors

### High CPU Usage

1. Increase throttle values to reduce processing load
2. Consider running on a more powerful device

### Data Not Reaching Server

1. Check server is running and reachable
2. Verify `SOCKET_SERVER_URL` is correct
3. Check `SOCKET_DEVICE_KEY` matches server configuration
4. Look for authentication errors in logs

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Code structure and BLE communication
- [SENSORS.md](./SENSORS.md) - Sensor protocols and data formats
