# Sensor Specifications

This document describes the BLE sensors used by the sensor-hub, including their protocols, data formats, and configuration options.

## Overview

| Sensor | Type | Protocol | Sample Rate | Data Points |
|--------|------|----------|-------------|-------------|
| Foot Pressure (L/R) | Pressure Insole | Text UART | ~30 Hz | 18 sensors |
| WT901BLE67 | IMU | Binary | ~100 Hz | 9 values |

## Foot Pressure Sensors

### Hardware

Custom insole sensors with 18 pressure-sensitive points distributed across the foot:
- Heel (3 sensors)
- Midfoot (6 sensors)
- Forefoot (6 sensors)
- Toes (3 sensors)

### BLE Service

| UUID | Type | Description |
|------|------|-------------|
| `0000FFF0-0000-1000-8000-00805F9B34FB` | Service | Main service |
| `0000FFF1-0000-1000-8000-00805F9B34FB` | Notify | Data notifications |
| `0000FFF2-0000-1000-8000-00805F9B34FB` | Write | Command channel |

### Protocol

**Text-based UART with newline delimiters.**

**Commands:**
- `begin` - Start data transmission
- `end` - Stop data transmission

**Data Format:**
```
<foot>,<v1>,<v2>,...,<v18>,<max>,<avg>,<active>\n
```

Example:
```
L,12.3,45.6,78.9,23.4,56.7,89.0,34.5,67.8,90.1,12.3,45.6,78.9,23.4,56.7,89.0,34.5,67.8,90.1,89.0,45.6,15\n
```

**Fields:**
| Index | Field | Type | Description |
|-------|-------|------|-------------|
| 0 | foot | char | `L` or `R` for left/right |
| 1-18 | values | float | Pressure readings (0-100 scale) |
| 19 | max | float | Maximum pressure value |
| 20 | avg | float | Average pressure value |
| 21 | active | int | Number of active sensors |

### Parsed Output

```json
{
  "timestamp": "2025-01-30T14:30:22.100",
  "device": "LEFT_FOOT",
  "data": {
    "foot": "LEFT",
    "values": [12.3, 45.6, 78.9, 23.4, 56.7, 89.0, 34.5, 67.8, 90.1,
               12.3, 45.6, 78.9, 23.4, 56.7, 89.0, 34.5, 67.8, 90.1],
    "max": 89.0,
    "avg": 45.6,
    "active_count": 15
  }
}
```

### Connection Sequence

```
1. Scan for device by MAC address
2. Connect to device
3. Subscribe to notifications on FFF1
4. Write 'begin' to FFF2
5. Receive continuous data stream
6. On disconnect: write 'end' to FFF2
```

---

## WT901BLE67 Accelerometer/IMU

### Hardware

9-axis IMU sensor from WitMotion:
- 3-axis accelerometer
- 3-axis gyroscope
- 3-axis magnetometer (used for angle calculation)

### BLE Service

The device has two possible UUID patterns (variants):

**Variant 1:**
| UUID | Type | Description |
|------|------|-------------|
| `0000ffe4-*` | Notify | Data notifications |
| `0000ffe9-*` | Write | Command channel |

**Variant 2:**
| UUID | Type | Description |
|------|------|-------------|
| `0000fff1-*` | Notify | Data notifications |
| `0000fff2-*` | Write | Command channel |

The sensor implementation auto-discovers which variant is present.

### Protocol

**Binary packets, 20 bytes each.**

**Packet Structure:**
```
Byte 0-1:   Header (0x55 + type)
Byte 2-19:  Data (varies by type)
```

**Packet Types:**
- `0x51` - Acceleration data
- `0x52` - Gyroscope data
- `0x53` - Angle data

Each notification may contain multiple packet types concatenated.

### Keep-Alive

The device requires periodic commands to maintain connection:

```python
ACCEL_KEEPALIVE_COMMAND = bytes([0xff, 0xaa, 0x27, 0x3A, 0x00])
ACCEL_KEEPALIVE_INTERVAL = 1.0  # seconds
```

### Data Ranges

| Measurement | Range | Resolution |
|-------------|-------|------------|
| Acceleration | +/- 16g | 0.001g |
| Gyroscope | +/- 2000 deg/s | 0.1 deg/s |
| Roll/Pitch | +/- 180 deg | 0.01 deg |
| Yaw | 0-360 deg | 0.01 deg |

### Parsed Output

```json
{
  "timestamp": "2025-01-30T14:30:22.150",
  "device": "ACCELEROMETER",
  "data": {
    "acc": {
      "x": 0.123,
      "y": -0.456,
      "z": 9.812
    },
    "gyro": {
      "x": 1.23,
      "y": -0.45,
      "z": 0.67
    },
    "angle": {
      "roll": 2.34,
      "pitch": -1.56,
      "yaw": 45.78
    }
  }
}
```

### Connection Sequence

```
1. Scan for device by MAC address
2. Connect to device
3. Discover service UUIDs (detect variant)
4. Subscribe to notifications on notify UUID
5. Start keep-alive task (1 Hz)
6. Receive continuous binary packets
7. On disconnect: stop keep-alive
```

---

## Throttling Configuration

Both sensors support throttling to reduce data rate:

```python
# Process every Nth packet
throttle = 5  # 100 Hz -> 20 Hz

# In notification handler
self.packet_count += 1
if self.packet_count % self.throttle != 0:
    return  # Skip this packet
```

**Recommended Settings:**

| Sensor | Default Throttle | Reason |
|--------|------------------|--------|
| Foot Pressure | 1 (none) | Already ~30 Hz, needed for detailed gait analysis |
| Accelerometer | 5 | 100 Hz is excessive; 20 Hz captures movement well |

---

## Timing Constants

All timing values are centralized in `sensors/constants.py`:

| Constant | Value | Purpose |
|----------|-------|---------|
| `BLE_SCAN_TIMEOUT` | 10.0s | Max time to scan for device |
| `BLE_CONNECT_TIMEOUT` | 15.0s | Max time for connection |
| `BLE_RETRY_DELAY` | 3.0s | Delay between retry attempts |
| `BLE_STABILIZATION_DELAY` | 0.2s | Wait after connect for stability |
| `BLE_NOTIFICATION_SETUP_DELAY` | 0.3s | Wait after enabling notifications |
| `SENSOR_STARTUP_STAGGER` | 3.0s | Delay between starting each sensor |
| `ACCEL_KEEPALIVE_INTERVAL` | 1.0s | Frequency of keep-alive commands |

---

## Sensor Placement

### Foot Sensors

Sensors are embedded in insoles worn inside boots:
- Place insole flat in boot
- Ensure wiring exits at ankle
- BLE module clips to boot exterior

### Accelerometer

Typically worn on the torso or hip:
- Attach to belt or chest harness
- Ensure stable mounting to reduce vibration noise
- Keep away from metal objects that may interfere with BLE

---

## Troubleshooting

### Foot Sensor Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| No data | Sensor not started | Verify 'begin' command sent |
| Partial values | Newline parsing issue | Check data buffer handling |
| Incorrect readings | Calibration needed | Contact sensor manufacturer |

### Accelerometer Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Disconnects frequently | Keep-alive not working | Verify write UUID discovered |
| Wrong UUID variant | Auto-discovery failed | Manually set UUIDs in code |
| Angle drift | Magnetometer interference | Move away from metal objects |

### General BLE Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Device not found | Out of range | Move closer |
| Connection fails | BLE stack busy | Increase stagger delay |
| Multiple devices fail | Bluetooth overloaded | Reduce concurrent connections |
