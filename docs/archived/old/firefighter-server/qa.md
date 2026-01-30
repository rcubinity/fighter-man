# Firefighter Activity Recognition - Project Q&A

## The Problem

Firefighters perform various activities during emergencies and training:

- Walking, Running, Crawling (through smoke)
- Climbing ladders
- Carrying equipment/victims
- Operating hoses
- Kneeling, Standing, Idle

**Challenge:** How do we automatically recognize what activity a firefighter is doing in real-time?

---

## The Solution: AI-Powered Activity Recognition

Build a machine learning model that can identify firefighter activities from wearable sensor data.

```
Firefighter wears sensors
        |
Sensors detect movement patterns
        |
AI model classifies: "This is Crawling"
        |
Applications: Safety monitoring, training feedback, fatigue detection
```

---

## Why Collect Data?

**To train the AI model.** Machine learning requires labeled examples:

| Sensor Pattern | Label      |
| -------------- | ---------- |
| Pattern A      | "Walking"  |
| Pattern B      | "Walking"  |
| Pattern C      | "Crawling" |
| Pattern D      | "Climbing" |
| ...            | ...        |

The model learns: "When sensors show this pattern -> it's Walking"

**More data = better accuracy.** Need hundreds/thousands of labeled examples per activity.

---

## Why Sessions?

Sessions organize data collection into logical units:

| Session             | Activity Focus | Duration |
| ------------------- | -------------- | -------- |
| `ladder_drill_001`  | Climbing       | 10 min   |
| `smoke_crawl_002`   | Crawling       | 15 min   |
| `hose_training_003` | Hose Operation | 20 min   |

**Benefits:**

1. **Organized** - Know which training exercise produced which data
2. **Labelable** - Can label all windows in a session with the activity performed
3. **Exportable** - Export one session = one clean dataset
4. **Manageable** - Delete bad sessions, keep good ones

---

## The Sensors

| Sensor             | Location          | What It Measures                    |
| ------------------ | ----------------- | ----------------------------------- |
| Foot Pressure (x2) | Left & Right foot | 18 pressure points per foot         |
| Accelerometer/IMU  | Torso/belt        | Acceleration, rotation, orientation |

**Why these sensors?**

- Foot pressure: Detects gait, weight distribution, stance
- Accelerometer: Detects body movement, orientation, vibration

Together they create a unique "fingerprint" for each activity.

---

## The Pipeline

```
Phase 1: Data Collection (sensor-hub on Raspberry Pi)
|-- Collect BLE sensor data
|-- Stream to server in real-time
|-- Store locally as backup

Phase 2: Data Storage (firefighter-server)
|-- Receive sensor streams
|-- Accumulate into 500ms time windows
|-- Convert to 270-dimension vectors
|-- Store in Qdrant vector database

Phase 3: Data Labeling (future annotation tool)
|-- Display time windows to researcher
|-- Researcher labels each window with activity
|-- Labels stored back to database

Phase 4: Model Training (future ML pipeline)
|-- Export labeled data
|-- Train activity classification model
|-- Validate accuracy

Phase 5: Real-time Recognition (future)
|-- Deploy trained model
|-- Classify activities in real-time
|-- Enable applications
```

---

## End Applications

Once the AI model is trained:

| Application                 | Description                                                |
| --------------------------- | ---------------------------------------------------------- |
| **Safety Monitoring**       | Alert if firefighter is motionless too long (down/injured) |
| **Training Feedback**       | "You spent 40% time crawling, 30% climbing"                |
| **Fatigue Detection**       | Detect degraded movement patterns = exhaustion             |
| **Performance Analytics**   | Compare trainees' movement efficiency                      |
| **Incident Reconstruction** | "At 10:32, firefighter was climbing"                       |

---

## Current Status

| Phase                             | Status      |
| --------------------------------- | ----------- |
| sensor-hub (Pi data collection)   | Done        |
| firefighter-server (data storage) | Done        |
| Annotation tool                   | Not started |
| ML model training                 | Not started |
| Real-time recognition             | Not started |

**You are here:** Collecting and storing labeled training data to eventually train the AI model.

---

## Quick Reference

| Question                  | Answer                                                |
| ------------------------- | ----------------------------------------------------- |
| **What are we building?** | AI that recognizes firefighter activities             |
| **Why collect data?**     | To train the machine learning model                   |
| **Why sessions?**         | Organize data by training exercise for labeling       |
| **Why vectors/Qdrant?**   | Enable similarity search + ML-ready format            |
| **End goal?**             | Real-time activity recognition for safety & analytics |

---

## Technical Specifications

### Vector Composition (270 dimensions)

```
Dimensions [0-179]  : 10 foot readings x 18 pressure values = 180 dims
Dimensions [180-269]: 10 accel readings x 9 values = 90 dims
                      (acc xyz, gyro xyz, angle roll/pitch/yaw)
```

### Time Window

- **Duration:** 500ms per window
- **Why 500ms:** Enough data to characterize movement, granular enough for precise activity boundaries

### Activity Labels (Expected)

| Label          | Description                  |
| -------------- | ---------------------------- |
| Walking        | Normal walking pace          |
| Running        | Fast movement                |
| Crawling       | Low crawl (smoke simulation) |
| Climbing       | Ladder ascent/descent        |
| Standing       | Stationary, upright          |
| Kneeling       | One or both knees down       |
| Carrying       | Carrying equipment/person    |
| Hose_Operation | Using fire hose              |
| Idle           | No activity / rest           |

---

**Document Version:** 1.0
**Last Updated:** December 2, 2025
