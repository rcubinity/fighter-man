# Sensor Specifications

This document provides detailed technical specifications for all sensors used in the sensor-hub data collection system.

---

## Table of Contents

1. [Foot Pressure Sensors](#foot-pressure-sensors)
2. [Accelerometer (WT901BLE67 IMU)](#accelerometer-wt901ble67-imu)
3. [Data Collection Rates](#data-collection-rates)
4. [BLE Communication Protocols](#ble-communication-protocols)

---

## Foot Pressure Sensors

### Overview

The system uses two identical foot pressure sensors, one for each foot. Each sensor contains **24 total sensor positions**, of which **18 are active** (6 positions have no physical sensors installed).

### Physical Layout

```
Foot Sensor Layout (Top View - Looking Down at Foot)

           Toe Area (Front)
        ┌─────────────────────┐
        │  0    1    2    3   │  ← Toes
        │                     │
        │  4    5    6    7   │  ← Ball of foot
        │                     │
        │  [8]  9   10   11   │  ← Arch (8 = inactive)
        │                     │
        │ [12] 13   14   15   │  ← Mid-foot (12 = inactive)
        │                     │
        │ [16] 17   18  [19]  │  ← Heel (16,19 = inactive)
        │                     │
        │ [20]  21   22  [23] │  ← Back heel (20,23 = inactive)
        └─────────────────────┘
           Heel Area (Back)

Active Sensors: 0-7, 9-11, 13-15, 17-18, 21-22
Inactive Sensors (no hardware): 8, 12, 16, 19, 20, 23

Total: 24 positions, 18 active sensors
```

### Hardware Specifications

| Spec | Value |
|------|-------|
| Sensor Type | Resistive pressure sensors |
| Active Sensors | 18 per foot |
| Total Positions | 24 per foot (6 inactive) |
| Measurement Unit | Raw pressure values (unitless) |
| Dynamic Range | 0 - ~1000 (typical) |
| Resolution | ~0.1 precision |
| Sampling Rate | ~20 Hz native |
| Power Source | Battery (BLE integrated) |

### BLE Communication

**Protocol Type:** Text-based, newline-delimited ASCII

**Data Format:**
```
L_[[v0,v1,v2,...,v23]]\n    # Left foot
R_[[v0,v1,v2,...,v23]]\n    # Right foot
```

**Service UUIDs:**
- Service: `0000FFF0-0000-1000-8000-00805F9B34FB`
- Notify: `0000FFF1-0000-1000-8000-00805F9B34FB` (receive data)
- Write: `0000FFF2-0000-1000-8000-00805F9B34FB` (send commands)

**Control Commands:**
- Start streaming: `begin`
- Stop streaming: `end`

### Data Processing

**Filtering (parsers.py):**
```python
# Extract 18 active sensors from 24 total positions
ACTIVE_INDICES = [0,1,2,3,4,5,6,7, 9,10,11, 13,14,15, 17,18, 21,22]
EXCLUDED_INDICES = [8, 12, 16, 19, 20, 23]  # No physical sensors

active_values = [values[i] for i in ACTIVE_INDICES]
```

**Calculated Metrics:**
- `max`: Maximum pressure across all 18 active sensors
- `avg`: Average pressure across all 18 active sensors
- `active_count`: Number of sensors with pressure > 0

**Throttling:**
- Default: Process every 2nd packet (FOOT_THROTTLE=2)
- Effective rate: ~10 Hz (from ~20 Hz native)

### Typical Pressure Patterns

| Activity | Pressure Pattern |
|----------|------------------|
| Standing | Constant pressure across heel and ball of foot |
| Walking | Alternating heel → ball → toe pressure waves |
| Running | High spikes at heel and toe, rapid transitions |
| Crawling | Very low pressure, mostly toes/ball |
| Kneeling | Concentrated at toe sensors (0-3) |

---

## Accelerometer (WT901BLE67 IMU)

### Overview

The WT901BLE67 is a **9-axis Inertial Measurement Unit (IMU)** that combines:
- 3-axis accelerometer
- 3-axis gyroscope
- 3-axis angle calculation (roll, pitch, yaw)

### Hardware Specifications

| Spec | Value |
|------|-------|
| Model | WT901BLE67 (WitMotion) |
| Axes | 9 (3 accel + 3 gyro + 3 angles) |
| Communication | BLE 5.0 |
| Sampling Rate | ~100 Hz native |
| Power Source | Battery (BLE integrated) |
| Keep-Alive Required | Yes (1 Hz) |

#### Accelerometer Specs

| Parameter | Specification |
|-----------|--------------|
| Range | ±16g |
| Resolution | 16-bit signed integer |
| Conversion Formula | `acc = raw / 32768.0 * 16` |
| Units | g (gravity, where 1g = 9.81 m/s²) |
| Precision | 3 decimal places |
| Zero-G Reading | ~0.000 (when stationary) |
| Earth Gravity | ~9.807 on Z-axis (upright) |

#### Gyroscope Specs

| Parameter | Specification |
|-----------|--------------|
| Range | ±2000°/s |
| Resolution | 16-bit signed integer |
| Conversion Formula | `gyro = raw / 32768.0 * 2000` |
| Units | degrees per second (°/s) |
| Precision | 2 decimal places |
| Zero Reading | ~0.00 (when stationary) |

#### Angle Specs (Calculated by IMU)

| Parameter | Specification |
|-----------|--------------|
| Range | ±180° |
| Resolution | 16-bit signed integer |
| Conversion Formula | `angle = raw / 32768.0 * 180` |
| Units | degrees (°) |
| Precision | 2 decimal places |
| Reference Frame | Sensor-local coordinate system |

### Coordinate System

```
Sensor Orientation (Default Position - Accelerometer on Back):

         +Y (Forward)
          ↑
          │
          │
    +X ←──┼──→ -X (Left/Right)
          │
          │
          ↓
         -Y (Backward)

         +Z = Up (away from body)
         -Z = Down (into body)


Roll:  Rotation around X-axis (sideways tilt)
       +Roll = Right side down
       -Roll = Left side down

Pitch: Rotation around Y-axis (forward/backward tilt)
       +Pitch = Forward tilt (nose down)
       -Pitch = Backward tilt (nose up)

Yaw:   Rotation around Z-axis (compass heading)
       +Yaw = Clockwise rotation
       -Yaw = Counter-clockwise rotation
```

### BLE Communication

**Protocol Type:** Binary, fixed-length packets

**Packet Structure (20 bytes):**
```
Byte Index:  Description
─────────────────────────────────────────
[0-1]        Header: 0x55 0x61
[2-3]        Acceleration X (signed 16-bit, little-endian)
[4-5]        Acceleration Y (signed 16-bit, little-endian)
[6-7]        Acceleration Z (signed 16-bit, little-endian)
[8-9]        Gyroscope X (signed 16-bit, little-endian)
[10-11]      Gyroscope Y (signed 16-bit, little-endian)
[12-13]      Gyroscope Z (signed 16-bit, little-endian)
[14-15]      Roll angle (signed 16-bit, little-endian)
[16-17]      Pitch angle (signed 16-bit, little-endian)
[18-19]      Yaw angle (signed 16-bit, little-endian)
```

**Service UUIDs (Device has two variants - auto-detected):**

Variant 1:
- Notify: `0000ffe4-0000-1000-8000-00805F9B34FB`
- Write: `0000ffe9-0000-1000-8000-00805F9B34FB`

Variant 2:
- Notify: `0000fff1-0000-1000-8000-00805F9B34FB`
- Write: `0000fff2-0000-1000-8000-00805F9B34FB`

The system automatically detects which variant is present during connection.

### Keep-Alive Protocol

**Requirement:** The WT901BLE67 requires periodic keep-alive commands to maintain data streaming.

**Command:** `bytes([0xff, 0xaa, 0x27, 0x3A, 0x00])`

**Frequency:** Every 1 second

**Implementation:** Background async task runs continuously:
```python
async def _keep_alive(self):
    while self.is_monitoring:
        await asyncio.sleep(1)
        await self.write_char.write(KEEP_ALIVE_CMD)
```

### Data Processing

**Parsing (parsers.py):**
```python
# Unpack binary data (little-endian signed shorts)
header, *raw_values = struct.unpack('<H9h', raw_data)

# Validate header
assert header == 0x6155  # 0x55 0x61 in little-endian

# Extract raw values
acc_raw = raw_values[0:3]
gyro_raw = raw_values[3:6]
angle_raw = raw_values[6:9]

# Convert to physical units
acc = [round(x / 32768.0 * 16, 3) for x in acc_raw]
gyro = [round(x / 32768.0 * 2000, 2) for x in gyro_raw]
angle = [round(x / 32768.0 * 180, 2) for x in angle_raw]
```

**Throttling:**
- Default: Process every 5th packet (ACCEL_THROTTLE=5)
- Effective rate: ~20 Hz (from ~100 Hz native)

### Typical Sensor Readings

| Activity | Acceleration Pattern | Angle Pattern |
|----------|---------------------|---------------|
| Standing | acc.z ≈ 9.8g, acc.x/y ≈ 0 | roll/pitch ≈ 0°, stable |
| Walking | Vertical bounce (±2g), periodic | roll/pitch oscillate ±10° |
| Running | High vertical bounce (±5g), rapid | roll/pitch oscillate ±20° |
| Crawling | acc.z ≈ 0, acc.x or acc.y ≈ ±9.8 | roll or pitch ≈ ±90° |
| Climbing | Forward tilt, acc varies | pitch ≈ +30° to +60° |
| Falling | Sudden spike, then freefall (0g) | Rapid angle changes |

### IMU Orientation Examples

**Upright Standing:**
```json
{
  "acc": {"x": 0.0, "y": 0.0, "z": 9.807},
  "gyro": {"x": 0.0, "y": 0.0, "z": 0.0},
  "angle": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
}
```

**Lying Flat (Face Up):**
```json
{
  "acc": {"x": 0.0, "y": 9.807, "z": 0.0},
  "gyro": {"x": 0.0, "y": 0.0, "z": 0.0},
  "angle": {"roll": 0.0, "pitch": 90.0, "yaw": 0.0}
}
```

**Crawling (Horizontal):**
```json
{
  "acc": {"x": 9.807, "y": 0.0, "z": 0.0},
  "gyro": {"x": 0.0, "y": 0.0, "z": 0.0},
  "angle": {"roll": 90.0, "pitch": 0.0, "yaw": 0.0}
}
```

---

## Data Collection Rates

### Native Rates (Before Throttling)

| Sensor | Native Rate | Typical Use Case |
|--------|-------------|------------------|
| Left Foot | ~20 Hz | Continuous gait monitoring |
| Right Foot | ~20 Hz | Continuous gait monitoring |
| Accelerometer | ~100 Hz | High-frequency motion capture |

**Total Native Data Rate:** ~140 data points/second

### Effective Rates (After Throttling)

| Sensor | Throttle Factor | Effective Rate | Bandwidth |
|--------|----------------|----------------|-----------|
| Left Foot | 2 (every 2nd packet) | ~10 Hz | ~2 KB/s |
| Right Foot | 2 (every 2nd packet) | ~10 Hz | ~2 KB/s |
| Accelerometer | 5 (every 5th packet) | ~20 Hz | ~3 KB/s |

**Total Effective Data Rate:** ~40 data points/second (~7 KB/s)

### Configurable Throttling

Throttling is configurable via environment variables:

```bash
# .env configuration
FOOT_THROTTLE=2     # Process every 2nd foot packet (higher = more throttling)
ACCEL_THROTTLE=5    # Process every 5th accel packet

# Examples:
# FOOT_THROTTLE=1  → No throttling (~20 Hz)
# FOOT_THROTTLE=5  → Heavy throttling (~4 Hz)
```

---

## BLE Communication Protocols

### Connection Process

**1. Discovery Phase (scanner.py):**
```bash
# Scan for nearby BLE devices
sudo python3 scanner.py

# Output:
# MAC: XX:XX:XX:XX:XX:XX | Name: "Foot Sensor L" | RSSI: -45 dBm
```

**2. Connection Sequence (main.py):**
```python
# Priority order with 3-second delays to avoid BLE stack overload
1. Connect to left foot sensor (highest priority)
2. Wait 3 seconds
3. Connect to right foot sensor
4. Wait 3 seconds
5. Connect to accelerometer (lowest priority)
```

**3. Retry Logic:**
- Max retries: 3 (configurable via CONNECTION_RETRIES)
- Delay between retries: 3 seconds
- Timeout per connection attempt: 10 seconds

### Authentication

**Device Authentication (Socket.IO to Server):**
```python
# After connecting to server
socket_client.emit('authenticate', {'device_key': 'firefighter_pi_001'})

# Server responds with:
# 'auth_success' → Ready to transmit data
# 'auth_error' → Disconnect and retry
```

### Packet Fragmentation

Both sensors use packet fragmentation due to BLE limitations:

**Foot Sensors:**
- Complete packet: `L_[[v0,v1,...,v23]]\n` (~100 bytes)
- BLE MTU: ~20 bytes per notification
- Solution: Accumulate chunks in buffer until '\n' delimiter

**Accelerometer:**
- Complete packet: 20 bytes
- BLE MTU: 20 bytes (perfect match)
- Solution: Process each notification as complete packet

### Error Detection

**Foot Sensors:**
- Validate: Prefix matches 'L_' or 'R_'
- Validate: Exactly 24 comma-separated values
- Validate: All values are numeric

**Accelerometer:**
- Validate: Packet length == 20 bytes
- Validate: Header == 0x55 0x61
- Validate: Values within expected ranges

---

## Power Consumption

### Typical Operating Current

| Sensor | Current Draw | Battery Life (Estimate) |
|--------|--------------|------------------------|
| Foot Sensor | ~15 mA @ 3.7V | ~8-12 hours continuous |
| Accelerometer | ~20 mA @ 3.7V | ~6-10 hours continuous |

**Note:** Actual battery life depends on sensor model, BLE transmission rate, and battery capacity.

### Power Optimization

**Throttling Benefits:**
- Reduces processing overhead
- Lowers BLE transmission frequency
- Extends battery life

**Keep-Alive Impact:**
- Accelerometer requires 1Hz keep-alive
- Adds ~1% power overhead
- Necessary for reliable data streaming

---

## Troubleshooting

### Common Issues

**Issue: Foot sensor returns 24 zeros**
- Cause: Sensor not started
- Solution: Send 'begin' command via Write UUID

**Issue: Accelerometer data stops after a few seconds**
- Cause: Missing keep-alive commands
- Solution: Verify keep-alive background task is running

**Issue: BLE connection fails**
- Cause: Multiple connection attempts too close together
- Solution: Add 3-second delays between connections

**Issue: Inconsistent data rates**
- Cause: BLE interference or packet loss
- Solution: Check RSSI signal strength (should be > -70 dBm)

---

## Calibration

### Foot Sensors

**No calibration required.** Foot sensors provide raw pressure values that are used relatively (comparing distribution patterns, not absolute values).

### Accelerometer

**Factory calibrated.** The WT901BLE67 comes pre-calibrated from the manufacturer. However, you can verify:

```python
# Place sensor flat and stationary
# Expected readings (within ±0.5):
{
  "acc": {"x": 0.0, "y": 0.0, "z": 9.8},  # Z should be ~9.8g
  "gyro": {"x": 0.0, "y": 0.0, "z": 0.0},
  "angle": {"roll": 0.0, "pitch": 0.0, "yaw": <any>}  # Yaw drifts over time
}
```

**Note:** Yaw angle (compass heading) may drift without magnetometer calibration. For activity detection, focus on roll and pitch angles.

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture and data flow
- [DATA_DICTIONARY.md](./DATA_DICTIONARY.md) - Complete data field reference
- [ACTIVITY_DETECTION_GUIDE.md](./ACTIVITY_DETECTION_GUIDE.md) - Using sensor data for ML
- [ML_INTEGRATION.md](./ML_INTEGRATION.md) - ML pipeline integration
