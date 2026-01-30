# Stage 1: Training Sessions

## Overview

Stage 1 is the **data collection and understanding phase**. The goal is to record clean sensor data for each activity type so we can understand what the sensor values look like for different movements.

---

## Core Concept: 1 Session = 1 Activity

Each recording session captures **only one type of activity**. The entire session is labeled with that activity.

```
Session 1: Walking
┌─────────────────────────────────────────┐
│ Start ──────────────────────────► Stop  │
│         Person walks entire time        │
│                                         │
│ ALL data in this session = "Walking"    │
└─────────────────────────────────────────┘

Session 2: Crawling
┌─────────────────────────────────────────┐
│ Start ──────────────────────────► Stop  │
│        Person crawls entire time        │
│                                         │
│ ALL data in this session = "Crawling"   │
└─────────────────────────────────────────┘

Session 3: Climbing
┌─────────────────────────────────────────┐
│ Start ──────────────────────────► Stop  │
│        Person climbs entire time        │
│                                         │
│ ALL data in this session = "Climbing"   │
└─────────────────────────────────────────┘
```

---

## Purpose

**Understand what sensor values look like for each activity:**

| Activity | What We Learn |
|----------|---------------|
| Walking | Foot pressure patterns, accelerometer rhythm |
| Crawling | Low foot pressure, body angle changes |
| Climbing | Alternating pressure, vertical acceleration |
| Standing | Stable pressure, minimal movement |
| Running | High frequency patterns, impact forces |

This data helps us:
- Identify unique patterns for each activity
- Set thresholds for detection
- Build training data for ML models

---

## Workflow

### Step 1: Create Session
```
POST /api/sessions
{
  "name": "walking_session_001",
  "activity_type": "Walking"
}
```

### Step 2: Record Activity
- Firefighter performs ONLY the specified activity
- Sensors capture foot pressure + accelerometer data
- Data streams to server via Socket.IO

### Step 3: Stop Session
```
POST /api/sessions/{id}/stop
```

### Step 4: Analyze Data
- Review sensor patterns for that activity
- Compare with other activity sessions
- Build understanding of each activity's "signature"

---

## Data Collected

### Foot Pressure Sensor
- 18 pressure points per foot (left + right)
- Captures weight distribution, gait pattern

### Accelerometer/IMU
- Acceleration (x, y, z)
- Gyroscope (x, y, z)
- Angle (roll, pitch, yaw)

---

## Example Sessions to Create

| Session Name | Activity | Duration | Notes |
|--------------|----------|----------|-------|
| walking_001 | Walking | 2-3 min | Normal pace |
| walking_002 | Walking | 2-3 min | Fast pace |
| crawling_001 | Crawling | 2-3 min | Low crawl |
| climbing_001 | Climbing | 2-3 min | Ladder up/down |
| standing_001 | Standing | 1-2 min | Stationary |
| running_001 | Running | 1-2 min | Light jog |

---

## Future Stages

| Stage | Description |
|-------|-------------|
| **Stage 1 (Current)** | Record sessions, understand sensor patterns |
| Stage 2 | Analyze patterns, identify thresholds |
| Stage 3 | Build decision logic / ML model |
| Stage 4 | Real-time activity recognition |

---

**Document Version:** 1.0
**Last Updated:** December 16, 2025
