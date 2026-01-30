# Data Reference

Complete reference for all data schemas, field definitions, and data structures in the firefighter activity recognition system. This document covers Socket.IO event payloads, sensor data formats, and Qdrant storage schemas.

---

## Table of Contents

1. [Overview](#overview)
2. [Foot Pressure Data Schema](#foot-pressure-data-schema)
3. [Accelerometer Data Schema](#accelerometer-data-schema)
4. [Sensor Position Mapping](#sensor-position-mapping)
5. [Vector Composition Details](#vector-composition-details)
6. [Qdrant Payload Schema](#qdrant-payload-schema)
7. [Data Rates and Frequencies](#data-rates-and-frequencies)
8. [Example Payloads](#example-payloads)

---

## Overview

The system transmits sensor data via Socket.IO events to the firefighter-server, which windows the data into 270-dimensional vectors stored in Qdrant.

### Event Summary

| Event Name | Namespace | Source | Frequency |
|------------|-----------|--------|-----------|
| `foot_pressure_data` | `/iot` | LEFT_FOOT, RIGHT_FOOT sensors | ~10-20 Hz per foot |
| `accelerometer_data` | `/iot` | WT901BLE67 IMU | ~20 Hz (throttled from 100 Hz) |

### Data Flow

```
Sensors (BLE)
    |
    v
Sensor Hub (Raspberry Pi)
    | Socket.IO events
    v
Firefighter Server
    | 500ms windowing
    v
Qdrant Vector DB (270-dim vectors)
```

---

## Foot Pressure Data Schema

### Socket.IO Event: `foot_pressure_data`

**Namespace:** `/iot`

**Emitted by:** Sensor Hub (Raspberry Pi)

### JSON Schema

```json
{
  "timestamp": "string (ISO 8601)",
  "device": "string",
  "data": {
    "foot": "string",
    "max": "number",
    "avg": "number",
    "active_count": "integer",
    "values": "array[number]"
  }
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | string | Yes | ISO 8601 timestamp with microseconds (e.g., `2025-01-15T14:23:45.123456`) |
| `device` | string | Yes | Device identifier: `"LEFT_FOOT"` or `"RIGHT_FOOT"` |
| `data` | object | Yes | Container for sensor measurements |
| `data.foot` | string | Yes | Foot side: `"LEFT"` or `"RIGHT"` |
| `data.max` | float | Yes | Maximum pressure value across all 18 active sensors |
| `data.avg` | float | Yes | Average pressure value across all 18 active sensors |
| `data.active_count` | integer | Yes | Number of sensors with non-zero pressure (0-18) |
| `data.values` | array | Yes | Array of exactly 18 pressure values (floats) |

### Value Constraints

| Field | Type | Range | Precision | Unit |
|-------|------|-------|-----------|------|
| `timestamp` | string | N/A | microseconds | ISO 8601 |
| `device` | enum | `["LEFT_FOOT", "RIGHT_FOOT"]` | N/A | N/A |
| `data.foot` | enum | `["LEFT", "RIGHT"]` | N/A | N/A |
| `data.max` | float | 0.0 - 1000.0+ | 1 decimal | Raw ADC value |
| `data.avg` | float | 0.0 - 1000.0+ | 1 decimal | Raw ADC value |
| `data.active_count` | integer | 0 - 18 | exact | count |
| `data.values[i]` | float | 0.0 - 1000.0+ | 1 decimal | Raw ADC value |

### Raw Protocol

The foot sensor transmits data as text over BLE with the format:

```
L_[[v1,v2,v3,v4],[v5,v6,v7,v8],...]
R_[[v1,v2,v3,v4],[v5,v6,v7,v8],...]
```

- `L_` prefix indicates left foot, `R_` indicates right foot
- Raw data contains 24 values (6 groups of 4)
- Positions 8, 12, 16, 19, 20, 23 are excluded (no physical sensors)
- After filtering, exactly 18 values remain

---

## Accelerometer Data Schema

### Socket.IO Event: `accelerometer_data`

**Namespace:** `/iot`

**Emitted by:** Sensor Hub (Raspberry Pi)

**Sensor Model:** WT901BLE67 (WitMotion 9-axis IMU)

### JSON Schema

```json
{
  "timestamp": "string (ISO 8601)",
  "device": "string",
  "data": {
    "acc": {
      "x": "number",
      "y": "number",
      "z": "number"
    },
    "gyro": {
      "x": "number",
      "y": "number",
      "z": "number"
    },
    "angle": {
      "roll": "number",
      "pitch": "number",
      "yaw": "number"
    }
  }
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | string | Yes | ISO 8601 timestamp with microseconds |
| `device` | string | Yes | Always `"ACCELEROMETER"` |
| `data` | object | Yes | Container for IMU measurements |
| `data.acc` | object | Yes | 3-axis linear acceleration |
| `data.acc.x` | float | Yes | Acceleration along X-axis |
| `data.acc.y` | float | Yes | Acceleration along Y-axis |
| `data.acc.z` | float | Yes | Acceleration along Z-axis |
| `data.gyro` | object | Yes | 3-axis angular velocity |
| `data.gyro.x` | float | Yes | Angular velocity around X-axis |
| `data.gyro.y` | float | Yes | Angular velocity around Y-axis |
| `data.gyro.z` | float | Yes | Angular velocity around Z-axis |
| `data.angle` | object | Yes | 3-axis orientation |
| `data.angle.roll` | float | Yes | Roll angle (rotation around X) |
| `data.angle.pitch` | float | Yes | Pitch angle (rotation around Y) |
| `data.angle.yaw` | float | Yes | Yaw angle (rotation around Z) |

### Value Constraints

| Field | Type | Range | Precision | Unit |
|-------|------|-------|-----------|------|
| `timestamp` | string | N/A | microseconds | ISO 8601 |
| `device` | string | `"ACCELEROMETER"` | N/A | N/A |
| `data.acc.x` | float | -16.0 to +16.0 | 3 decimals | g (gravity, 1g = 9.807 m/s^2) |
| `data.acc.y` | float | -16.0 to +16.0 | 3 decimals | g |
| `data.acc.z` | float | -16.0 to +16.0 | 3 decimals | g |
| `data.gyro.x` | float | -2000.0 to +2000.0 | 2 decimals | deg/s (degrees per second) |
| `data.gyro.y` | float | -2000.0 to +2000.0 | 2 decimals | deg/s |
| `data.gyro.z` | float | -2000.0 to +2000.0 | 2 decimals | deg/s |
| `data.angle.roll` | float | -180.0 to +180.0 | 2 decimals | degrees |
| `data.angle.pitch` | float | -180.0 to +180.0 | 2 decimals | degrees |
| `data.angle.yaw` | float | -180.0 to +180.0 | 2 decimals | degrees |

### Raw Binary Protocol

The WT901BLE67 transmits 20-byte binary packets:

```
Byte 0:     0x55 (header)
Byte 1:     0x61 (combined packet type)
Bytes 2-7:  Accelerometer X,Y,Z (3 signed 16-bit integers, little-endian)
Bytes 8-13: Gyroscope X,Y,Z (3 signed 16-bit integers, little-endian)
Bytes 14-19: Angles Roll,Pitch,Yaw (3 signed 16-bit integers, little-endian)
```

**Conversion Formulas:**
```python
# Acceleration: +/-16g range
acc = raw_value / 32768.0 * 16  # Result in g

# Gyroscope: +/-2000 deg/s range
gyro = raw_value / 32768.0 * 2000  # Result in deg/s

# Angles: +/-180 degree range
angle = raw_value / 32768.0 * 180  # Result in degrees
```

---

## Sensor Position Mapping

### Foot Pressure Sensor Layout

Each foot insole has 18 active pressure sensors distributed across anatomical regions:

```
                    TOES
        +---+---+---+---+
        | 0 | 1 | 2 | 3 |      Toe area (4 sensors)
        +---+---+---+---+

            BALL OF FOOT
        +---+---+---+---+
        | 4 | 5 | 6 | 7 |      Ball/metatarsal (4 sensors)
        +---+---+---+---+

              ARCH
          +---+---+---+
          | 8 | 9 | 10|        Arch (3 sensors)
          +---+---+---+

            MID-FOOT
          +---+---+---+
          |11 |12 |13 |        Mid-foot (3 sensors)
          +---+---+---+

              HEEL
            +---+---+
            |14 |15 |          Front heel (2 sensors)
            +---+---+
            |16 |17 |          Back heel (2 sensors)
            +---+---+
```

### Array Index to Anatomical Position Mapping

| Array Index | Anatomical Region | Position Description |
|-------------|-------------------|---------------------|
| 0 | Toe | Big toe area, medial |
| 1 | Toe | Second/third toe area |
| 2 | Toe | Third/fourth toe area |
| 3 | Toe | Little toe area, lateral |
| 4 | Ball | First metatarsal head, medial |
| 5 | Ball | Second metatarsal head |
| 6 | Ball | Third/fourth metatarsal |
| 7 | Ball | Fifth metatarsal head, lateral |
| 8 | Arch | Medial arch |
| 9 | Arch | Central arch |
| 10 | Arch | Lateral arch |
| 11 | Mid-foot | Medial mid-foot |
| 12 | Mid-foot | Central mid-foot |
| 13 | Mid-foot | Lateral mid-foot |
| 14 | Heel | Medial heel, anterior |
| 15 | Heel | Lateral heel, anterior |
| 16 | Heel | Medial heel, posterior |
| 17 | Heel | Lateral heel, posterior |

### Raw to Active Sensor Index Mapping

The raw sensor array has 24 positions, but only 18 have physical sensors:

```python
# Positions without physical sensors (excluded)
EXCLUDED_INDICES = {8, 12, 16, 19, 20, 23}

# Raw index -> Active index mapping
# raw[0]  -> values[0]   # Toe
# raw[1]  -> values[1]   # Toe
# raw[2]  -> values[2]   # Toe
# raw[3]  -> values[3]   # Toe
# raw[4]  -> values[4]   # Ball
# raw[5]  -> values[5]   # Ball
# raw[6]  -> values[6]   # Ball
# raw[7]  -> values[7]   # Ball
# raw[8]  -> EXCLUDED
# raw[9]  -> values[8]   # Arch
# raw[10] -> values[9]   # Arch
# raw[11] -> values[10]  # Arch
# raw[12] -> EXCLUDED
# raw[13] -> values[11]  # Mid-foot
# raw[14] -> values[12]  # Mid-foot
# raw[15] -> values[13]  # Mid-foot
# raw[16] -> EXCLUDED
# raw[17] -> values[14]  # Heel
# raw[18] -> values[15]  # Heel
# raw[19] -> EXCLUDED
# raw[20] -> EXCLUDED
# raw[21] -> values[16]  # Back heel
# raw[22] -> values[17]  # Back heel
# raw[23] -> EXCLUDED
```

---

## Vector Composition Details

### Vector Dimensions Summary

| Segment | Dimensions | Index Range | Description |
|---------|------------|-------------|-------------|
| Foot Pressure | 180 | 0 - 179 | 10 readings x 18 values |
| Accelerometer | 90 | 180 - 269 | 10 readings x 9 values |
| **Total** | **270** | 0 - 269 | |

### Foot Pressure Vector Layout (dims 0-179)

```
Reading 0:  [0-17]    (18 pressure values)
Reading 1:  [18-35]   (18 pressure values)
Reading 2:  [36-53]   (18 pressure values)
Reading 3:  [54-71]   (18 pressure values)
Reading 4:  [72-89]   (18 pressure values)
Reading 5:  [90-107]  (18 pressure values)
Reading 6:  [108-125] (18 pressure values)
Reading 7:  [126-143] (18 pressure values)
Reading 8:  [144-161] (18 pressure values)
Reading 9:  [162-179] (18 pressure values)
```

Each reading contains the 18 `data.values` from a `foot_pressure_data` event.

**Note:** Both left and right foot readings are combined into the same segment as they arrive. The windowing does not separate by foot.

### Accelerometer Vector Layout (dims 180-269)

```
Reading 0:  [180-188] (9 values: acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, roll, pitch, yaw)
Reading 1:  [189-197] (9 values)
Reading 2:  [198-206] (9 values)
Reading 3:  [207-215] (9 values)
Reading 4:  [216-224] (9 values)
Reading 5:  [225-233] (9 values)
Reading 6:  [234-242] (9 values)
Reading 7:  [243-251] (9 values)
Reading 8:  [252-260] (9 values)
Reading 9:  [261-269] (9 values)
```

Each reading contains 9 values in this exact order:
1. `data.acc.x`
2. `data.acc.y`
3. `data.acc.z`
4. `data.gyro.x`
5. `data.gyro.y`
6. `data.gyro.z`
7. `data.angle.roll`
8. `data.angle.pitch`
9. `data.angle.yaw`

### Padding and Truncation

- **Max readings per window:** 10 (defined by `MAX_READINGS_PER_WINDOW`)
- **If fewer readings:** Zero-padding applied to fill remaining slots
- **If more readings:** Only the 10 most recent readings are used

### Normalization

Before storage, vectors are L2-normalized:

```python
norm = sqrt(sum(x_i^2 for all i))
normalized_vector = [x_i / norm for all i]
```

This ensures all vectors have unit length, optimizing cosine similarity search in Qdrant.

---

## Qdrant Payload Schema

### Collection Configuration

| Setting | Value |
|---------|-------|
| Collection Name | `sensor_windows` (configurable via `QDRANT_COLLECTION` env var) |
| Vector Dimension | 270 |
| Distance Metric | Cosine |
| Host | `localhost` (configurable via `QDRANT_HOST`) |
| Port | `6333` (configurable via `QDRANT_PORT`) |

### Point Structure

Each Qdrant point contains:

```json
{
  "id": "uuid-string",
  "vector": [/* 270 normalized floats */],
  "payload": {
    "session_id": "string",
    "device": "string",
    "start_time": "number (milliseconds)",
    "end_time": "number (milliseconds)",
    "foot_count": "integer",
    "accel_count": "integer",
    "label": "string or null",
    "raw_data": "string (JSON)"
  }
}
```

### Payload Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | UUID of the recording session |
| `device` | string | Device identifier (from first reading in window) |
| `start_time` | float | Window start time in milliseconds since epoch |
| `end_time` | float | Window end time in milliseconds since epoch |
| `foot_count` | integer | Number of foot pressure readings in this window |
| `accel_count` | integer | Number of accelerometer readings in this window |
| `label` | string | Activity label from session (e.g., "Walking", "Standing") |
| `raw_data` | string | JSON-encoded raw sensor readings (see below) |

### raw_data Structure

The `raw_data` field contains the original sensor readings, useful for reconstruction:

```json
{
  "foot": [
    {
      "timestamp": "2025-01-15T14:23:45.123456",
      "device": "LEFT_FOOT",
      "data": {
        "foot": "LEFT",
        "max": 285.6,
        "avg": 142.3,
        "active_count": 16,
        "values": [12.3, 45.6, ...]
      }
    },
    // ... more foot readings
  ],
  "accel": [
    {
      "timestamp": "2025-01-15T14:23:45.234567",
      "device": "ACCELEROMETER",
      "data": {
        "acc": {"x": 0.023, "y": -0.045, "z": 9.807},
        "gyro": {"x": 0.12, "y": -0.34, "z": 0.05},
        "angle": {"roll": 0.15, "pitch": -0.27, "yaw": 45.12}
      }
    },
    // ... more accel readings
  ]
}
```

---

## Data Rates and Frequencies

### Sensor Output Rates

| Sensor | Native Rate | Throttled Rate | Throttle Factor |
|--------|-------------|----------------|-----------------|
| Foot Pressure (each) | ~10-20 Hz | ~10-20 Hz | 1 (no throttle) |
| Accelerometer | 100 Hz | 20 Hz | 5 |

### Windowing Configuration

| Parameter | Value | Source |
|-----------|-------|--------|
| Window Duration | 500 ms | `DEFAULT_WINDOW_SIZE_MS` |
| Max Readings per Window | 10 | `MAX_READINGS_PER_WINDOW` |
| Vectors per Second | ~2 | (1000ms / 500ms) |

### Expected Readings per Window

At typical data rates:

| Sensor Type | Expected Readings | Typical Range |
|-------------|-------------------|---------------|
| Foot (total) | 5-10 | Combined from both feet |
| Accelerometer | 8-10 | After 5x throttling |

### Data Volume Estimates

| Metric | Value |
|--------|-------|
| Events per second | ~40 (20 foot + 20 accel) |
| Raw event payload size | ~200-400 bytes |
| Raw data rate | ~8-16 KB/s |
| Vectors per minute | ~120 |
| Vectors per hour | ~7,200 |
| Vector size (normalized) | 270 x 4 bytes = 1,080 bytes |
| Qdrant storage per hour | ~8 MB (vectors only, excluding payloads) |

---

## Example Payloads

### Example 1: Foot Pressure Event (Standing)

```json
{
  "timestamp": "2025-01-15T14:23:45.123456",
  "device": "LEFT_FOOT",
  "data": {
    "foot": "LEFT",
    "max": 285.6,
    "avg": 142.3,
    "active_count": 16,
    "values": [
      12.3, 45.6, 67.8, 23.4,
      156.7, 234.5, 198.2, 167.4,
      89.1, 112.3, 98.7,
      134.5, 156.2, 145.8,
      285.6, 267.3,
      198.4, 203.1
    ]
  }
}
```

**Interpretation:**
- Person standing with weight distributed
- Maximum pressure at heel (285.6)
- 16 of 18 sensors active
- Toe area has lower pressure (person weight on heels)

### Example 2: Foot Pressure Event (Walking - Toe Push-off)

```json
{
  "timestamp": "2025-01-15T14:23:45.623789",
  "device": "RIGHT_FOOT",
  "data": {
    "foot": "RIGHT",
    "max": 478.2,
    "avg": 156.8,
    "active_count": 12,
    "values": [
      345.6, 478.2, 389.4, 234.5,
      267.8, 312.4, 289.1, 198.7,
      45.6, 23.4, 12.3,
      0.0, 0.0, 0.0,
      0.0, 0.0,
      0.0, 0.0
    ]
  }
}
```

**Interpretation:**
- Toe push-off phase of gait
- Maximum pressure at toes (478.2)
- Heel sensors inactive (0.0)
- Weight shifting forward

### Example 3: Accelerometer Event (Standing Still)

```json
{
  "timestamp": "2025-01-15T14:23:45.234567",
  "device": "ACCELEROMETER",
  "data": {
    "acc": {
      "x": 0.023,
      "y": -0.045,
      "z": 0.987
    },
    "gyro": {
      "x": 0.12,
      "y": -0.34,
      "z": 0.05
    },
    "angle": {
      "roll": 0.15,
      "pitch": -0.27,
      "yaw": 45.12
    }
  }
}
```

**Interpretation:**
- Stationary upright position
- Z-axis acceleration ~1g (gravity)
- Minimal angular velocity
- Level orientation (roll/pitch near 0)

### Example 4: Accelerometer Event (Running)

```json
{
  "timestamp": "2025-01-15T14:23:46.089234",
  "device": "ACCELEROMETER",
  "data": {
    "acc": {
      "x": -1.234,
      "y": 2.567,
      "z": 2.845
    },
    "gyro": {
      "x": -45.67,
      "y": 23.45,
      "z": -12.34
    },
    "angle": {
      "roll": -8.45,
      "pitch": 12.67,
      "yaw": 48.23
    }
  }
}
```

**Interpretation:**
- Active movement (running)
- Elevated Z acceleration (upward bounce)
- Significant angular velocity
- Body tilted forward (positive pitch)

### Example 5: Qdrant Point (Complete)

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "vector": [0.023, 0.045, 0.067, ...],
  "payload": {
    "session_id": "session_1705312200",
    "device": "LEFT_FOOT",
    "start_time": 1705312200123,
    "end_time": 1705312200623,
    "foot_count": 8,
    "accel_count": 10,
    "label": "Walking",
    "raw_data": "{\"foot\":[...],\"accel\":[...]}"
  }
}
```

---

## Data Quality Indicators

### Valid Data Characteristics

**Foot Pressure:**
- All values >= 0
- `active_count` <= 18
- `max` >= `avg`
- `max` value appears in `values` array

**Accelerometer:**
- Magnitude when stationary: `sqrt(x^2 + y^2 + z^2)` is approximately 1.0g
- Gyro values near 0 when stationary
- Angles within +/-180 degrees

### Invalid Data Indicators

| Issue | Symptom | Likely Cause |
|-------|---------|--------------|
| All zeros | `values` all 0.0 | Sensor disconnected |
| Negative pressure | values < 0 | Parsing error |
| Extreme acceleration | > 16g | Out of range / noise |
| Extreme gyro | > 2000 deg/s | Out of range / noise |
| Static timestamp | Same for many events | Clock issue |

---

## Related Documentation

- [ML_INTEGRATION.md](./ML_INTEGRATION.md) - ML pipeline and training guide
- [firefighter-server/lib/constants.py](../../firefighter-server/lib/constants.py) - Server constants
- [sensor-hub/sensors/parsers.py](../../sensor-hub/sensors/parsers.py) - Data parsing logic
