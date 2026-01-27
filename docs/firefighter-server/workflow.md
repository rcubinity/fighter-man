# Training Drill Workflow

## Overview

This system is designed for **training drills** (practice sessions), not active firefighting. Firefighters wear sensors during controlled training exercises to collect data for AI model training.

---

## Equipment Setup

### What the Firefighter Wears

| Sensor                     | Location          | Data Captured                       |
| -------------------------- | ----------------- | ----------------------------------- |
| Foot Pressure Sensors (x2) | Left & Right foot | 18 pressure points per foot         |
| Accelerometer/IMU          | Belt/Torso        | Acceleration, rotation, orientation |

### Infrastructure

| Component    | Location           | Role                     |
| ------------ | ------------------ | ------------------------ |
| Raspberry Pi | Near training area | Collects BLE sensor data |
| Server       | Cloud/Local        | Stores data in Qdrant    |

---

## Workflow Steps

### Step 1: Setup

```
- Firefighter wears:
  • Foot pressure sensors (left + right)
  • Accelerometer (on belt/torso)
- Raspberry Pi nearby (collects BLE data)
- Server running (firefighter-server)
```

### Step 2: Start Session

```bash
# Operator creates a new recording session
curl -X POST http://server:4100/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "ladder_drill_001"}'
```

- Pi automatically starts streaming sensor data
- Server begins accumulating data into 500ms windows

### Step 3: Training Drill

```
- Firefighter performs activities:
  • Walking
  • Climbing ladders
  • Crawling (smoke simulation)
  • Carrying equipment
  • etc.

- Data flows continuously:
  Sensors → Pi → Server → Qdrant
```

### Step 4: Stop Session

```bash
# Operator stops the recording
curl -X POST http://server:4100/api/sessions/{session_id}/stop
```

- Remaining data flushed to database
- Session marked as "stopped"

### Step 5: Label Activities (Later)

```
- Researcher opens annotation tool
- Reviews session timeline with visualizations:
  • Foot pressure heat maps
  • Accelerometer waveforms
- Labels each time segment:
  • "0:00 - 0:30 → Walking"
  • "0:30 - 1:15 → Climbing"
  • "1:15 - 2:00 → Crawling"
```

### Step 6: Repeat

```
More training drills = More labeled data = Better AI model
```

---

## System Architecture

```
    FIREFIGHTER              RASPBERRY PI              SERVER
   ┌───────────┐            ┌───────────┐           ┌─────────┐
   │ Foot      │───BLE────▶│           │──Socket──▶│         │
   │ Sensors   │            │  sensor-  │    IO     │firefighter-
   │           │            │   hub     │           │ server  │
   │ Accel     │───BLE────▶│           │           │         │
   │ Sensor    │            └───────────┘           └────┬────┘
   └───────────┘                                         │
                                                         ▼
                                                    ┌─────────┐
                                                    │ Qdrant  │
                                                    │ (vector │
                                                    │   db)   │
                                                    └─────────┘
```

---

## Data Flow Detail

```
1. Sensors emit BLE signals (10-100 Hz)
         │
         ▼
2. Pi receives via Bluetooth (sensor-hub)
         │
         ▼
3. Pi streams to server via Socket.IO
         │
         ▼
4. Server accumulates into 500ms windows
         │
         ▼
5. Windows converted to 270-dim vectors
   • 180 dims from foot sensors (10 readings × 18 values)
   • 90 dims from accelerometer (10 readings × 9 values)
         │
         ▼
6. Vectors stored in Qdrant for ML training
```

---

## Why This Approach?

| Question              | Answer                                            |
| --------------------- | ------------------------------------------------- |
| Why training drills?  | Need labeled data - can't label during real fires |
| Why 500ms windows?    | Enough data to capture movement patterns          |
| Why Qdrant (vectors)? | Enables similarity search + ML-ready format       |
| Why Socket.IO?        | Real-time streaming for continuous sensor data    |

---

## Future: Real Firefighting

Once AI is trained with enough labeled data:

```
Training Phase (Now)          →    Deployment Phase (Future)
─────────────────────────────────────────────────────────────
Collect data from drills            Deploy trained model
Label activities manually           Real-time activity recognition
Train ML model                      Safety alerts for command center
```

---

**Document Version:** 1.0
**Last Updated:** December 2, 2025
