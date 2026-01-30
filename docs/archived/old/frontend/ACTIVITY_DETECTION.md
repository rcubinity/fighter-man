# Activity Detection

This document explains how the frontend detects firefighter activities in real-time from sensor data.

## Table of Contents

1. [Overview](#overview)
2. [Detected Activities](#detected-activities)
3. [Detection Algorithm](#detection-algorithm)
4. [Feature Extraction](#feature-extraction)
5. [Confidence Scoring](#confidence-scoring)
6. [Visualization](#visualization)
7. [Limitations](#limitations)

---

## Overview

### What is Activity Detection?

Activity detection analyzes sensor data to identify what activity the firefighter is performing at any given moment.

**Inputs:**
- Foot pressure data (36 values: 18 per foot)
- Accelerometer data (9 values: acc/gyro/angle)

**Output:**
```javascript
{
  activity: "Standing",   // Detected activity name
  confidence: 85          // Confidence percentage (0-100)
}
```

### How It Works

The detector uses a **rule-based classification** system:

1. Collect latest sensor readings
2. Calculate statistical features
3. Apply classification rules
4. Return activity + confidence score

**Update Frequency:** Every time new sensor data arrives (~20-100 Hz)

---

## Detected Activities

The system can detect 5 basic firefighter activities:

| Activity | Description | Typical Use Case |
|----------|-------------|------------------|
| **Standing** | Upright, stationary or slow movement | Standing at attention, monitoring |
| **Sitting** | Seated position, minimal foot contact | Resting, sitting on equipment |
| **Bent_Forward** | Forward bend, moderate foot pressure | Picking up equipment, tying boots |
| **Lying_Down** | Horizontal position, very low accel Y | Crawling under smoke, prone position |
| **Jumping** | High dynamic movement, foot variance | Jumping over obstacles, dynamic drills |

### Activity Transitions

Activities can transition rapidly during training:

```
Standing → Bent_Forward → Lying_Down → Standing
  (3s)        (2s)           (10s)        (5s)
```

The detector updates continuously to track these transitions.

---

## Detection Algorithm

### Function Signature

```javascript
function detectActivity(footData, accelData) {
  // footData: { foot: 'L'|'R', values: [18 numbers], max, avg }
  // accelData: { acc: {x, y, z}, gyro: {x, y, z}, angle: {roll, pitch, yaw} }

  // Returns: { activity: string, confidence: number }
}
```

### Classification Logic

The detector applies rules in priority order:

```javascript
// 1. Check for lying down (strongest signal)
if (accelY < 1.0) {
  return { activity: "Lying_Down", confidence: 90 };
}

// 2. Check for sitting (minimal foot pressure + tilted)
if (pitch > 30 && avgFootPressure < 5) {
  return { activity: "Sitting", confidence: 85 };
}

// 3. Check for bent forward (high pitch angle)
if (pitch > 45) {
  return { activity: "Bent_Forward", confidence: 80 };
}

// 4. Check for jumping (high movement + foot variance)
if (totalGyro > 50 && footVariance > 15) {
  return { activity: "Jumping", confidence: 85 };
}

// 5. Default to standing
return { activity: "Standing", confidence: 75 };
```

### Rule Details

**Lying_Down Detection:**
- **Primary Signal:** `accelY < 1.0` (very low vertical acceleration)
- **Why It Works:** Body horizontal = gravity pulls sideways, not down
- **Threshold:** 1.0 m/s² (vs. ~9.8 m/s² when upright)

**Sitting Detection:**
- **Signals:** `pitch > 30°` AND `avgFootPressure < 5`
- **Why It Works:** Torso tilted back + minimal weight on feet
- **Threshold:** Pitch angle > 30°, average pressure < 5 units

**Bent_Forward Detection:**
- **Primary Signal:** `pitch > 45°` (forward tilt)
- **Why It Works:** Bending forward tilts IMU significantly
- **Threshold:** 45° pitch angle

**Jumping Detection:**
- **Signals:** `totalGyro > 50` AND `footVariance > 15`
- **Why It Works:** Rapid rotation + alternating foot pressure
- **Thresholds:** Gyro > 50°/s, pressure variance > 15

**Standing (Default):**
- **Condition:** None of the above match
- **Why It Works:** Most common activity, catch-all
- **Confidence:** Lower than others (75% vs 80-90%)

---

## Feature Extraction

Before classification, the detector calculates statistical features from raw sensor data.

### Foot Pressure Features

```javascript
// Input: footData.values = [s1, s2, s3, ..., s18]

// Feature 1: Average pressure
const avgFootPressure = values.reduce((a, b) => a + b, 0) / values.length;

// Feature 2: Maximum pressure
const maxFootPressure = Math.max(...values);

// Feature 3: Variance (foot pressure distribution)
const mean = avgFootPressure;
const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
const footVariance = Math.sqrt(variance);  // Standard deviation
```

**What These Tell Us:**
- **Average:** Overall weight on foot (high = standing, low = sitting/lying)
- **Maximum:** Peak pressure point (high = specific sensor loaded)
- **Variance:** Distribution spread (high = uneven, low = even distribution)

### Accelerometer Features

```javascript
// Input: accelData = { acc: {x, y, z}, gyro: {x, y, z}, angle: {roll, pitch, yaw} }

// Feature 1: Vertical acceleration (body orientation)
const accelY = accelData.acc.y;  // Gravity component

// Feature 2: Pitch angle (forward/backward tilt)
const pitch = Math.abs(accelData.angle.pitch);

// Feature 3: Total rotational velocity
const totalGyro = Math.sqrt(
  Math.pow(accelData.gyro.x, 2) +
  Math.pow(accelData.gyro.y, 2) +
  Math.pow(accelData.gyro.z, 2)
);
```

**What These Tell Us:**
- **AccelY:** Body vertical orientation (9.8 = upright, <1 = horizontal)
- **Pitch:** Torso angle (0° = upright, 90° = bent over)
- **TotalGyro:** Rotation speed (high = dynamic movement, low = static)

---

## Confidence Scoring

### How Confidence is Calculated

Each activity has a base confidence level:

```javascript
const baseConfidence = {
  "Lying_Down": 90,      // Very distinctive signal
  "Sitting": 85,         // Clear combination of signals
  "Bent_Forward": 80,    // Moderate distinctiveness
  "Jumping": 85,         // Clear dynamic signal
  "Standing": 75         // Default, less distinctive
};
```

### Confidence Interpretation

| Range | Meaning | Display Color |
|-------|---------|---------------|
| **80-100%** | High confidence | Green |
| **60-79%** | Medium confidence | Yellow |
| **0-59%** | Low confidence | Orange |

### When Confidence is Low

Low confidence (<60%) indicates:
1. **Transitional Movement:** Between two activities
2. **Unusual Activity:** Not in predefined categories
3. **Sensor Noise:** Missing or corrupt sensor data
4. **Edge Cases:** Posture doesn't fit any category well

**UI Behavior:** Low confidence may show "Waiting..." instead of activity name.

---

## Visualization

### Real-Time Display

During recording and replay, detected activity is displayed:

```
┌─────────────────────────┐
│  Detected Activity:     │
│                         │
│      [SVG Icon]         │
│      👤 (Standing)      │
│                         │
│   Standing (85%)        │
│                         │
│  Session Activity:      │
│     Climbing            │
└─────────────────────────┘
```

**Elements:**
1. **SVG Icon:** Visual representation (Standing = person standing, Sitting = person sitting)
2. **Activity Name:** Text label (color-coded by confidence)
3. **Confidence %:** Numerical confidence score
4. **Session Activity:** User-assigned activity type (for labeling)

### Timeline Coloring

Activities are visualized on the replay timeline:

```
Timeline:
├────────┬─────────┬────────┬─────────┤
[Green]  [Blue]    [Amber]  [Green]
Sitting  Standing  Lying    Sitting
```

**Color Mapping:**
- **Green:** Sitting
- **Blue:** Standing
- **Amber:** Lying_Down
- **Violet:** Bent_Forward
- **Red:** Jumping

---

## Limitations

### Rule-Based vs. Machine Learning

The current detector is **rule-based**, not ML-based:

**Advantages:**
- ✅ Fast and lightweight
- ✅ No training data required
- ✅ Explainable (can trace why decision was made)
- ✅ Works immediately without model training

**Disadvantages:**
- ❌ Limited to predefined activities
- ❌ May misclassify complex movements
- ❌ Thresholds not adaptive to different users
- ❌ Cannot learn from corrections

### Known Misclassifications

**Bent_Forward vs. Sitting:**
- Both have forward pitch angle
- Sitting has low foot pressure, bent forward has moderate
- May confuse if firefighter sits with feet on ground

**Standing vs. Lying_Down (transitioning):**
- During transition, accelY drops gradually
- May briefly show Lying_Down while lowering to ground

**Jumping vs. Fast Walking:**
- Both have high gyro and foot variance
- May classify fast walking as Jumping

### Missing Activities

The following firefighter activities are **not** detected:

- Crawling (similar to Lying_Down)
- Climbing stairs/ladders (may show as Standing or Bent_Forward)
- Carrying equipment (similar to Standing)
- Kneeling (may show as Sitting or Bent_Forward)
- Running (may show as Jumping or Standing)

**Future:** Machine learning model could detect these with training data.

---

## Future Improvements

### Machine Learning Integration

Planned enhancements:

1. **Collect Training Data:** Use current detector to auto-label data
2. **Train ML Model:** Use TensorFlow.js or similar
3. **Deploy in Browser:** Replace rule-based logic with ML model
4. **Continuous Learning:** Learn from user corrections

### Video-Based Detection

Future integration with ml5.js:

1. **Pose Detection:** MoveNet extracts body keypoints from video
2. **Geometric Features:** Calculate joint angles, distances
3. **Multi-Modal Fusion:** Combine sensor + vision data
4. **Enhanced Accuracy:** Vision confirms sensor predictions

### Adaptive Thresholds

Personalize detection per user:

1. **Calibration Phase:** Record baseline activities (sit, stand, etc.)
2. **Learn Thresholds:** Adjust pitch/pressure thresholds per user
3. **Improve Accuracy:** Better detection for different body types

---

**Document Version:** 1.0
**Last Updated:** December 24, 2025
