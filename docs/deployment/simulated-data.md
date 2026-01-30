# Simulated Sensor Data

This document explains how the test client generates realistic simulated sensor data for testing without physical hardware.

## Overview

The script `firefighter-server/tests/realistic_activity_client.py` generates fake sensor data that closely mimics real sensor behavior. This allows testing the frontend and server without:
- A Raspberry Pi
- Physical BLE sensors
- A firefighter wearing the equipment

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  realistic_activity_client.py                               │
│                                                             │
│  ActivityGenerator class                                    │
│  ├── generate_foot_data()  → 18 pressure values            │
│  └── generate_accel_data() → acc, gyro, angles             │
│                                                             │
│  Values based on:                                           │
│  • Real sensor calibration data                            │
│  • Physics (gravity = 1g)                                  │
│  • Validated activity thresholds                           │
└─────────────────────────────────────────────────────────────┘
              │
              │ Socket.IO (same as real Pi)
              ▼
┌─────────────────────────────────────────────────────────────┐
│  firefighter-server                                         │
│  (Cannot tell the difference from real sensor data)        │
└─────────────────────────────────────────────────────────────┘
```

## Realistic Value Ranges

The simulated values are calibrated to match real sensor behavior:

### Accelerometer (IMU)

The Y-axis is vertical when the sensor is worn upright.

| Activity | acc.y Range | Why It's Realistic |
|----------|-------------|-------------------|
| Standing | 0.9 - 1.1g | Gravity pulls down at 1g when upright |
| Sitting | 0.6 - 0.85g | Partial weight on seat reduces Y-axis reading |
| Bent Forward | 0.2 - 0.65g | Torso angle shifts gravity vector |
| Lying Down | -0.25 - 0.25g | Gravity shifts to X-axis when horizontal |
| Jumping | 0.4 - 1.45g | Oscillates: low in air, high on landing |

### Foot Pressure Sensors

18 pressure points per foot, values represent relative pressure.

| Activity | Pressure Range | Why It's Realistic |
|----------|----------------|-------------------|
| Standing | 100 - 200 | Full body weight distributed on feet |
| Sitting | 0 - 80 | Most weight on seat, minimal on feet |
| Bent Forward | 120 - 220 | Weight shifts to toes (front sensors higher) |
| Lying Down | 0 - 50 | Almost no weight on feet |
| Jumping | 0 - 800 | 0 in air, 400-800 on landing (impact force) |

### Gyroscope & Angles

| Activity | Pitch Range | Gyro Activity | Why |
|----------|-------------|---------------|-----|
| Standing | -10° to 10° | Low (±30°/s) | Stable upright posture |
| Sitting | 20° to 40° | Low (±15°/s) | Moderate forward lean |
| Bent Forward | 40° to 80° | Medium (±40°/s) | High forward pitch |
| Lying Down | ±75° to 95° | Low (±20°/s) | Near horizontal |
| Jumping | -20° to 20° | High (±120°/s) | Rapid body movement |

## Code Examples

### Foot Pressure Generation

```python
if self.activity == "Standing":
    # Standing: Full weight distribution, moderate pressure
    base_pressure = random.uniform(100, 200)
    values = [
        round(base_pressure + random.uniform(-20, 20), 1)
        for _ in range(18)
    ]

elif self.activity == "Jumping":
    # Jumping: Oscillating between high pressure (landing) and low (airborne)
    jump_phase = math.sin(elapsed * 2 * math.pi)  # 1 jump per second

    if jump_phase > 0.5:
        # Landing phase - high pressure
        base_pressure = random.uniform(400, 800)
    elif jump_phase < -0.5:
        # Airborne - very low pressure
        base_pressure = random.uniform(0, 50)
```

### Accelerometer Generation

```python
if self.activity == "Standing":
    acc_x = random.uniform(-0.3, 0.3)
    acc_y = random.uniform(0.9, 1.1)   # Gravity on Y-axis
    acc_z = random.uniform(-0.3, 0.3)
    pitch = random.uniform(-10, 10)    # Stable upright

elif self.activity == "Lying_Down":
    # Gravity shifts to X-axis when horizontal
    acc_x = random.choice([
        random.uniform(0.85, 1.05),    # Lying on back
        random.uniform(-1.05, -0.85)   # Lying on front
    ])
    acc_y = random.uniform(-0.25, 0.25)  # Near zero
    pitch = random.choice([
        random.uniform(-95, -75),
        random.uniform(75, 95)
    ])
```

## Usage

### Basic Usage

```bash
cd firefighter-server
source venv/bin/activate

# Simulate standing for 30 seconds
python tests/realistic_activity_client.py --activity Standing --duration 30

# Simulate jumping continuously (Ctrl+C to stop)
python tests/realistic_activity_client.py --activity Jumping
```

### Available Activities

```
Standing      - Upright stable posture
Sitting       - Seated position
Bent_Forward  - Bending forward at waist
Lying_Down    - Horizontal on ground
Jumping       - Vertical jumps
```

### Options

```bash
python tests/realistic_activity_client.py \
    --activity Standing \      # Required: activity to simulate
    --duration 60 \            # Optional: seconds (default: continuous)
    --server http://localhost:4100 \  # Optional: server URL
    --foot-hz 2 \              # Optional: foot sensor frequency (default: 2Hz)
    --accel-hz 5               # Optional: accelerometer frequency (default: 5Hz)
```

## Data Flow Comparison

### Real Sensors (Production)

```
Physical Sensors → BLE → Raspberry Pi → Socket.IO → Server
     (real)                (sensor-hub)
```

### Simulated Sensors (Testing)

```
random.uniform() → Python Script → Socket.IO → Server
  (fake but realistic)   (realistic_activity_client.py)
```

The server and frontend **cannot distinguish** between real and simulated data because:
1. Same Socket.IO events (`foot_pressure_data`, `accelerometer_data`)
2. Same data structure (timestamp, device, values)
3. Same value ranges (calibrated to real sensors)

## Source of Realistic Values

The value ranges were derived from:
1. **Physics**: Gravity = 1g, impact forces during jumping
2. **Sensor calibration**: Real pressure sensor output ranges
3. **Activity analysis**: Thresholds validated from recorded sensor data
4. **IMU orientation**: Y-axis vertical when sensor worn on torso
