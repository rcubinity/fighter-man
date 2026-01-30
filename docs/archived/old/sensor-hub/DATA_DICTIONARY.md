# Data Dictionary

Complete reference for all data fields transmitted from the sensor-hub system. This document defines JSON schemas, data types, units, and valid ranges for both foot pressure and accelerometer data.

---

## Table of Contents

1. [Overview](#overview)
2. [Foot Pressure Data Schema](#foot-pressure-data-schema)
3. [Accelerometer Data Schema](#accelerometer-data-schema)
4. [Common Fields](#common-fields)
5. [Value Ranges](#value-ranges)
6. [Example Payloads](#example-payloads)

---

## Overview

All sensor data is transmitted as JSON payloads via Socket.IO events. The system uses two primary event types:

| Event Name | Description | Frequency |
|------------|-------------|-----------|
| `foot_pressure_data` | Foot sensor readings | ~10 Hz per foot (~20 Hz total) |
| `accelerometer_data` | IMU readings | ~20 Hz |

**Namespace:** `/iot`

**Total Data Rate:** ~40 events/second (~7 KB/s)

---

## Foot Pressure Data Schema

### Socket.IO Event

**Event Name:** `foot_pressure_data`

**Emitted From:** Raspberry Pi (sensor-hub)

**Received By:** Server at `http://localhost:4100/iot`

### JSON Schema

```json
{
  "timestamp": string (ISO 8601),
  "device": string (enum),
  "data": {
    "foot": string (enum),
    "max": number (float),
    "avg": number (float),
    "active_count": number (integer),
    "values": array[number] (18 floats)
  }
}
```

### Field Definitions

| Field Path | Type | Required | Description |
|------------|------|----------|-------------|
| `timestamp` | string | Yes | ISO 8601 timestamp with microseconds |
| `device` | string | Yes | Device identifier: `"LEFT_FOOT"` or `"RIGHT_FOOT"` |
| `data` | object | Yes | Sensor measurements container |
| `data.foot` | string | Yes | Foot side: `"LEFT"` or `"RIGHT"` |
| `data.max` | number | Yes | Maximum pressure across all 18 active sensors |
| `data.avg` | number | Yes | Average pressure across all 18 active sensors |
| `data.active_count` | integer | Yes | Number of sensors with pressure > 0 |
| `data.values` | array | Yes | Array of 18 pressure values (one per active sensor) |

### Value Constraints

| Field | Type | Range | Precision | Unit |
|-------|------|-------|-----------|------|
| `timestamp` | string | N/A | Microseconds | ISO 8601 |
| `device` | enum | `["LEFT_FOOT", "RIGHT_FOOT"]` | N/A | N/A |
| `data.foot` | enum | `["LEFT", "RIGHT"]` | N/A | N/A |
| `data.max` | float | 0.0 - 1000.0 (typical) | 0.1 | Raw sensor value |
| `data.avg` | float | 0.0 - 1000.0 (typical) | 0.1 | Raw sensor value |
| `data.active_count` | integer | 0 - 18 | 1 | Count |
| `data.values[i]` | float | 0.0 - 1000.0 (typical) | 0.1 | Raw sensor value |

### Sensor Position Mapping

The `data.values` array contains 18 elements corresponding to active sensor positions:

```
Array Index → Physical Position (see SENSOR_SPECIFICATIONS.md for layout)
─────────────────────────────────────────────────────────────────────
values[0]  → Position 0  (Toe area, leftmost)
values[1]  → Position 1  (Toe area)
values[2]  → Position 2  (Toe area)
values[3]  → Position 3  (Toe area, rightmost)
values[4]  → Position 4  (Ball of foot, leftmost)
values[5]  → Position 5  (Ball of foot)
values[6]  → Position 6  (Ball of foot)
values[7]  → Position 7  (Ball of foot, rightmost)
values[8]  → Position 9  (Arch)
values[9]  → Position 10 (Arch)
values[10] → Position 11 (Arch)
values[11] → Position 13 (Mid-foot)
values[12] → Position 14 (Mid-foot)
values[13] → Position 15 (Mid-foot)
values[14] → Position 17 (Heel)
values[15] → Position 18 (Heel)
values[16] → Position 21 (Back heel)
values[17] → Position 22 (Back heel)
```

**Note:** Positions 8, 12, 16, 19, 20, 23 are skipped (no physical sensors).

---

## Accelerometer Data Schema

### Socket.IO Event

**Event Name:** `accelerometer_data`

**Emitted From:** Raspberry Pi (sensor-hub)

**Received By:** Server at `http://localhost:4100/iot`

### JSON Schema

```json
{
  "timestamp": string (ISO 8601),
  "device": string (constant),
  "data": {
    "acc": {
      "x": number (float),
      "y": number (float),
      "z": number (float)
    },
    "gyro": {
      "x": number (float),
      "y": number (float),
      "z": number (float)
    },
    "angle": {
      "roll": number (float),
      "pitch": number (float),
      "yaw": number (float)
    }
  }
}
```

### Field Definitions

| Field Path | Type | Required | Description |
|------------|------|----------|-------------|
| `timestamp` | string | Yes | ISO 8601 timestamp with microseconds |
| `device` | string | Yes | Device identifier: `"ACCELEROMETER"` (constant) |
| `data` | object | Yes | Sensor measurements container |
| `data.acc` | object | Yes | 3-axis acceleration |
| `data.acc.x` | number | Yes | Acceleration along X-axis |
| `data.acc.y` | number | Yes | Acceleration along Y-axis |
| `data.acc.z` | number | Yes | Acceleration along Z-axis |
| `data.gyro` | object | Yes | 3-axis gyroscope (angular velocity) |
| `data.gyro.x` | number | Yes | Angular velocity around X-axis |
| `data.gyro.y` | number | Yes | Angular velocity around Y-axis |
| `data.gyro.z` | number | Yes | Angular velocity around Z-axis |
| `data.angle` | object | Yes | 3-axis orientation angles |
| `data.angle.roll` | number | Yes | Roll angle (rotation around X-axis) |
| `data.angle.pitch` | number | Yes | Pitch angle (rotation around Y-axis) |
| `data.angle.yaw` | number | Yes | Yaw angle (rotation around Z-axis) |

### Value Constraints

| Field | Type | Range | Precision | Unit |
|-------|------|-------|-----------|------|
| `timestamp` | string | N/A | Microseconds | ISO 8601 |
| `device` | string | `"ACCELEROMETER"` | N/A | N/A |
| `data.acc.x` | float | ±16.0 | 3 decimals | g (gravity) |
| `data.acc.y` | float | ±16.0 | 3 decimals | g (gravity) |
| `data.acc.z` | float | ±16.0 | 3 decimals | g (gravity) |
| `data.gyro.x` | float | ±2000.0 | 2 decimals | °/s (degrees/second) |
| `data.gyro.y` | float | ±2000.0 | 2 decimals | °/s (degrees/second) |
| `data.gyro.z` | float | ±2000.0 | 2 decimals | °/s (degrees/second) |
| `data.angle.roll` | float | ±180.0 | 2 decimals | ° (degrees) |
| `data.angle.pitch` | float | ±180.0 | 2 decimals | ° (degrees) |
| `data.angle.yaw` | float | ±180.0 | 2 decimals | ° (degrees) |

### Coordinate System

See [SENSOR_SPECIFICATIONS.md](./SENSOR_SPECIFICATIONS.md#coordinate-system) for detailed coordinate system definition.

**Quick Reference:**
- **X-axis**: Left (-) to Right (+)
- **Y-axis**: Backward (-) to Forward (+)
- **Z-axis**: Down (-) to Up (+)

**Gravity Reference (1g = 9.807 m/s²):**
- Upright standing: `acc.z ≈ +9.8`
- Lying on back: `acc.y ≈ +9.8`
- Lying on side: `acc.x ≈ ±9.8`

---

## Common Fields

### Timestamp Format

**Format:** ISO 8601 with microsecond precision

**Pattern:** `YYYY-MM-DDTHH:MM:SS.ffffff`

**Example:** `2025-12-19T14:23:45.123456`

**Timezone:** Local time (Raspberry Pi system time)

**Generation:**
```python
from datetime import datetime
timestamp = datetime.now().isoformat()
```

**Parsing (Python):**
```python
from datetime import datetime
dt = datetime.fromisoformat(timestamp)
```

**Parsing (JavaScript):**
```javascript
const dt = new Date(timestamp);
```

### Device Identifiers

| Identifier | Description | Count |
|------------|-------------|-------|
| `"LEFT_FOOT"` | Left foot pressure sensor | 1 |
| `"RIGHT_FOOT"` | Right foot pressure sensor | 1 |
| `"ACCELEROMETER"` | WT901BLE67 IMU | 1 |

**Total Devices:** 3

---

## Value Ranges

### Foot Pressure Values

**Typical Ranges by Activity:**

**Note:** Only Standing, Sitting, and Jumping have been partially observed with real sensors. Other activities are estimates.

| Activity | Max Pressure | Avg Pressure | Active Count | Validation Status |
|----------|--------------|--------------|--------------|-------------------|
| No Contact | 0 | 0 | 0 | Reference |
| Light Touch | 1-50 | 1-20 | 1-8 | Reference |
| Standing ✅ | 150-300 | 100-200 | 12-18 | Validated (IMU) + Observed (foot) |
| Sitting ✅ | 0-150 | 0-80 | 0-6 | Validated (IMU) + Observed (foot) |
| Jumping ✅ | 400-1000+ | 200-600 | 12-18 | Validated (IMU) + Observed (foot) |
| Bent_Forward ✅ | N/A | N/A | N/A | Validated (IMU only) |
| Lying_Down ✅ | 0-100 | 0-50 | 0-8 | Validated (IMU only) |
| Walking ⚠️ | 50-500 | 30-200 | 5-18 | Estimated |
| Running ⚠️ | 200-800 | 100-400 | 8-18 | Estimated |
| Crawling ⚠️ | 0-100 | 0-50 | 0-8 | Estimated |
| Climbing ⚠️ | 300-600 | 200-400 | 12-18 | Estimated |
| Kneeling ⚠️ | 100-250 | 50-150 | 4-10 | Estimated |
| Carrying ⚠️ | 300-600 | 150-350 | 12-18 | Estimated |
| Hose_Operation ⚠️ | 200-450 | 100-250 | 10-18 | Estimated |
| Idle ⚠️ | 0-250 | 0-150 | 0-12 | Estimated |

**Note:** Values are relative and depend on individual weight, sensor calibration, and mounting. ✅ = Validated with archived script, ⚠️ = Estimated, needs testing.

### Accelerometer Values

**Typical Ranges by Activity:**

**Note:** Only Standing, Sitting, Bent_Forward, Lying_Down, and Jumping have been validated. Others are estimates. **Y-axis is vertical** in validated data.

| Activity | Acceleration (g) | Gyroscope (°/s) | Angles (°) | Validation Status |
|----------|------------------|-----------------|------------|-------------------|
| Stationary | ±0.5 | ±5 | ±2 | Reference |
| Standing ✅ | Y: 0.85-1.15 | <50 | Pitch/Roll: ±15 | Validated |
| Sitting ✅ | Y: 0.5-0.9 | <20 | Pitch: 15-45 | Validated |
| Bent_Forward ✅ | Y: 0.0-0.7 | <50 | Pitch: 30-90 | Validated |
| Lying_Down ✅ | Y: ±0.3, X or Z: 0.8-1.1 | <30 | Pitch/Roll: ±70-100 | Validated |
| Jumping ✅ | Y: >1.3 or <0.6 | >100 | Varies | Validated |
| Walking ⚠️ | ±2.0 | ±50 | ±15 | Estimated |
| Running ⚠️ | ±5.0 | ±100 | ±30 | Estimated |
| Crawling ⚠️ | Horizontal | <40 | ±70-100 | Estimated |
| Climbing ⚠️ | ±3.0 | 20-80 | Pitch: 20-60 | Estimated |
| Falling | ±16.0 (max) | ±500 | Rapid changes | Reference |

**Free Fall Detection:** All acceleration values near 0 (< 0.5g) indicates free fall.

**Impact Detection:** Sudden spike > 10g indicates impact/collision.

**Coordinate System Note:** Validated activities use **Y-axis as vertical** (from archived script). Standing: Y≈1g, Lying: Y≈0g.

---

## Example Payloads

### Example 1: Left Foot Pressure (Standing)

```json
{
  "timestamp": "2025-12-19T14:23:45.123456",
  "device": "LEFT_FOOT",
  "data": {
    "foot": "LEFT",
    "max": 285.6,
    "avg": 142.3,
    "active_count": 16,
    "values": [
      12.3, 45.6, 67.8, 23.4,      // Toe area (indices 0-3)
      156.7, 234.5, 198.2, 167.4,  // Ball of foot (indices 4-7)
      89.1, 112.3, 98.7,            // Arch (indices 8-10)
      134.5, 156.2, 145.8,          // Mid-foot (indices 11-13)
      285.6, 267.3,                 // Heel (indices 14-15)
      198.4, 203.1                  // Back heel (indices 16-17)
    ]
  }
}
```

**Interpretation:**
- Person is standing with weight distributed across foot
- Maximum pressure at heel (285.6)
- 16 out of 18 sensors active (normal for standing)
- Average pressure 142.3 (moderate)

### Example 2: Right Foot Pressure (Walking - Heel Strike)

```json
{
  "timestamp": "2025-12-19T14:23:45.623789",
  "device": "RIGHT_FOOT",
  "data": {
    "foot": "RIGHT",
    "max": 512.8,
    "avg": 98.4,
    "active_count": 8,
    "values": [
      0.0, 0.0, 0.0, 0.0,           // Toe area (no contact)
      0.0, 0.0, 12.3, 23.4,         // Ball of foot (minimal)
      0.0, 0.0, 0.0,                // Arch (no contact)
      45.6, 67.8, 89.1,             // Mid-foot (transitioning)
      512.8, 487.3,                 // Heel (maximum pressure)
      345.2, 367.8                  // Back heel (high pressure)
    ]
  }
}
```

**Interpretation:**
- Heel strike phase of gait cycle
- Maximum pressure concentrated at heel (512.8)
- Only 8 sensors active (heel and back heel)
- Toes not in contact with ground

### Example 3: Accelerometer (Upright Standing)

```json
{
  "timestamp": "2025-12-19T14:23:45.123456",
  "device": "ACCELEROMETER",
  "data": {
    "acc": {
      "x": 0.023,
      "y": -0.045,
      "z": 9.807
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
- Person standing upright (acc.z ≈ 9.8g)
- Minimal lateral movement (acc.x, acc.y ≈ 0)
- Very low angular velocity (gyro values near 0)
- Nearly level orientation (roll, pitch ≈ 0°)
- Yaw is arbitrary (compass heading, drifts over time)

### Example 4: Accelerometer (Running)

```json
{
  "timestamp": "2025-12-19T14:23:46.089234",
  "device": "ACCELEROMETER",
  "data": {
    "acc": {
      "x": -1.234,
      "y": 2.567,
      "z": 12.345
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
- Vertical acceleration > 1g (z = 12.3g) indicates upward bounce
- Lateral movement (x, y) from body rotation
- High angular velocity (gyro values) from rapid movement
- Roll and pitch oscillating (body sway during running)

### Example 5: Accelerometer (Crawling)

```json
{
  "timestamp": "2025-12-19T14:23:47.456789",
  "device": "ACCELEROMETER",
  "data": {
    "acc": {
      "x": 9.678,
      "y": 0.234,
      "z": 0.567
    },
    "gyro": {
      "x": 5.67,
      "y": -8.45,
      "z": 2.34
    },
    "angle": {
      "roll": 87.45,
      "pitch": 3.21,
      "yaw": 52.34
    }
  }
}
```

**Interpretation:**
- Horizontal orientation (acc.x ≈ 9.8g, acc.z ≈ 0)
- Person is lying on side or crawling
- Roll angle ≈ 90° confirms horizontal position
- Low gyro values indicate slow, controlled movement

---

## Data Quality Indicators

### Valid Data Characteristics

**Foot Pressure:**
- ✅ All values ≥ 0
- ✅ active_count ≤ 18
- ✅ max ≥ avg
- ✅ max appears in values array

**Accelerometer:**
- ✅ Total acceleration magnitude ≈ 9.8g (when stationary)
  - Formula: `sqrt(x² + y² + z²) ≈ 9.8`
- ✅ Gyro values near 0 when stationary
- ✅ Angles within ±180°

### Invalid/Corrupted Data Indicators

**Warning Signs:**
- ⚠️ All zeros (sensor not started or disconnected)
- ⚠️ Negative pressure values (parsing error)
- ⚠️ active_count > 18 (logic error)
- ⚠️ Accelerometer magnitude >> 16g (out of range)
- ⚠️ Gyro values >> 2000°/s (out of range)
- ⚠️ Timestamp not increasing monotonically (clock issues)

---

## Server-Side Data Transformation

### Window Aggregation

The server accumulates individual sensor readings into **500ms time windows** and converts them to vectors for storage in Qdrant.

**Vector Structure (270 dimensions):**

```
Dimensions 0-179:   Foot pressure data (18 sensors × 10 readings)
  └─> [0-89]:       Left foot (18 values × 5 readings)
  └─> [90-179]:     Right foot (18 values × 5 readings)

Dimensions 180-269: Accelerometer data (9 values × 10 readings)
  └─> [180-209]:    Acceleration X,Y,Z (3 values × 10 readings)
  └─> [210-239]:    Gyroscope X,Y,Z (3 values × 10 readings)
  └─> [240-269]:    Angles Roll,Pitch,Yaw (3 values × 10 readings)
```

**Window Metadata:**
- `session_id`: PostgreSQL session UUID
- `start_time`: Window start timestamp
- `end_time`: Window end timestamp
- `window_id`: Unique identifier
- `labels`: Activity labels (for supervised learning)

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [SENSOR_SPECIFICATIONS.md](./SENSOR_SPECIFICATIONS.md) - Hardware specifications
- [ACTIVITY_DETECTION_GUIDE.md](./ACTIVITY_DETECTION_GUIDE.md) - ML feature engineering
- [ML_INTEGRATION.md](./ML_INTEGRATION.md) - ML pipeline integration
