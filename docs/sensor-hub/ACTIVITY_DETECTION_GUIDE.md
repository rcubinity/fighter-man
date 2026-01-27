# Activity Detection Guide

This document provides guidance for ML engineers on how to use sensor data to detect and classify firefighter activities. It includes activity profiles, feature engineering suggestions, and data preprocessing strategies.

---

## Table of Contents

1. [Overview](#overview)
2. [Activity Profiles](#activity-profiles)
3. [Feature Engineering](#feature-engineering)
4. [Data Preprocessing](#data-preprocessing)
5. [Pattern Recognition Strategies](#pattern-recognition-strategies)
6. [Implementation Examples](#implementation-examples)

---

## Overview

### Current Stage: Supervised Learning Data Collection

The system is currently in **Stage 1**: collecting labeled training data. Each session corresponds to exactly one activity type, creating clean ground-truth datasets for supervised learning.

### Activity Types

**Validated Activities** (tested with real sensor data from `archived/accelerator/blue/analyze.py`):

| Activity | Code | Description | Validation |
|----------|------|-------------|------------|
| Standing | `Standing` | Stationary upright position | ✅ Tested |
| Sitting | `Sitting` | Seated position with moderate pitch | ✅ Tested |
| Bent_Forward | `Bent_Forward` | Forward bend with high pitch | ✅ Tested |
| Lying_Down | `Lying_Down` | Horizontal orientation | ✅ Tested |
| Jumping | `Jumping` | Rapid vertical acceleration spikes | ✅ Tested |

**Estimated Activities** (require real-world validation):

| Activity | Code | Description | Status |
|----------|------|-------------|--------|
| Walking | `Walking` | Normal walking gait | ⚠️ Estimated |
| Running | `Running` | Fast movement/running | ⚠️ Estimated |
| Crawling | `Crawling` | Low profile movement | ⚠️ Estimated |
| Climbing | `Climbing` | Ladder climbing/stairs | ⚠️ Estimated |
| Kneeling | `Kneeling` | Kneeling position | ⚠️ Estimated |
| Carrying | `Carrying` | Carrying equipment | ⚠️ Estimated |
| Hose_Operation | `Hose_Operation` | Operating fire hose | ⚠️ Estimated |
| Idle | `Idle` | Minimal activity/resting | ⚠️ Estimated |

### Sensor Inputs

**Foot Pressure (2 sensors × 18 points):**
- Distribution of weight across feet
- Gait patterns and balance
- Ground contact phases

**Accelerometer/IMU (9-axis):**
- Body orientation (roll, pitch, yaw angles)
- Movement dynamics (acceleration)
- Rotational velocity (gyroscope)

---

## Activity Profiles

## Validation Status

### ✅ Validated Activities (from archived script)

The following 5 activities have been **tested and validated** with real sensor data from the archived detection script (`/archived/accelerator/blue/analyze.py`). These thresholds are based on actual hardware testing:

- **Standing** - Upright stable posture (lines 50-53)
- **Sitting** - Seated with moderate forward pitch (lines 60-64)
- **Bent_Forward** - Forward bend with high pitch angle (lines 56-57)
- **Lying_Down** - Horizontal orientation (lines 67-68)
- **Jumping** - Rapid vertical acceleration spikes (lines 71-74)

**Key Finding:** The archived script uses **Y-axis as vertical** (not Z-axis). When standing upright, `acc.y ≈ 1.0g`.

### ⚠️ Estimated Activities (Need Real-World Testing)

The following 8 activities have **estimated** thresholds based on sensor specifications and logical inference, but have **not been validated** with real hardware:

- Walking, Running, Crawling, Climbing, Kneeling, Carrying, Hose_Operation, Idle

**These profiles are provided for reference but require validation with actual sensor data before deployment.**

---

## Validated Activity Profiles

### 1. Standing ✅

**Validation Status:** Tested with real sensors (archived/accelerator/blue/analyze.py:50-53)

**Foot Pressure Signature:**
```
Pattern: Constant, balanced pressure on both feet
Max Pressure: 150-300 (moderate)
Avg Pressure: 100-200
Active Sensors: 12-18 (full foot contact)
Variance: Low (<40) - minimal movement
Left-Right Asymmetry: <50 (balanced stance)
```

**Accelerometer Signature (Y-axis vertical):**
```
Acceleration:
  - Y (vertical): 0.85 to 1.15g (gravity on Y-axis when standing)
  - X, Z (lateral): ±0.5g (minimal sway)
  - Magnitude: 0.9 to 1.2g

Gyroscope:
  - Magnitude: <50°/s (low rotational movement)
  - All axes: ±50°/s range

Angles:
  - Pitch: -15° to +15° (nearly upright)
  - Roll: -15° to +15° (nearly level)
  - Yaw: Any (compass heading irrelevant)
```

**Key Features:**
- Upright orientation with gravity on Y-axis
- Minimal movement variance
- Low gyroscope activity
- Stable foot pressure distribution

### 2. Sitting ✅

**Validation Status:** Tested with real sensors (archived/accelerator/blue/analyze.py:60-64)

**Foot Pressure Signature:**
```
Pattern: Minimal foot contact - weight on seat
Max Pressure: 0-150 (low)
Avg Pressure: 0-80
Active Sensors: 0-6 (minimal contact)
Variance: Low (<30) - stable position
```

**Accelerometer Signature (Y-axis vertical):**
```
Acceleration:
  - Y (vertical): 0.5 to 0.9g (reduced gravity support - weight on seat)
  - X, Z (lateral): Within normal range
  - Magnitude: 0.7 to 1.2g

Gyroscope:
  - Magnitude: <20°/s (very low movement)
  - All axes: ±20°/s range

Angles:
  - Pitch: 15° to 45° (moderate forward lean when sitting)
  - Roll: -30° to +30°
  - Yaw: Any
```

**Key Features:**
- Moderate forward pitch (leaning back in chair)
- Lower Y-axis acceleration than standing (weight on seat)
- Requires 2 seconds of stability to confirm (prevents false positives during transitions)
- Minimal foot pressure

### 3. Bent_Forward ✅

**Validation Status:** Tested with real sensors (archived/accelerator/blue/analyze.py:56-57)

**Accelerometer Signature (Y-axis vertical):**
```
Acceleration:
  - Y (vertical): 0.0 to 0.7g (reduced as body bends forward)
  - X, Z: -1.0 to 1.0g
  - Magnitude: 0.5 to 1.2g

Gyroscope:
  - Magnitude: <50°/s
  - All axes: ±50°/s range

Angles:
  - Pitch: 30° to 90° (high forward tilt - key indicator)
  - Roll: -30° to +30°
  - Yaw: Any
```

**Key Features:**
- **High forward pitch angle (>30°)** is the primary indicator
- Y-axis acceleration decreases as body tilts forward
- Distinguishable from sitting by higher pitch angle

### 4. Lying_Down ✅

**Validation Status:** Tested with real sensors (archived/accelerator/blue/analyze.py:67-68)

**Foot Pressure Signature:**
```
Pattern: Minimal to zero foot contact
Max Pressure: 0-100 (very low)
Avg Pressure: 0-50
Active Sensors: 0-8
```

**Accelerometer Signature (Y-axis vertical):**
```
Acceleration:
  - Y (vertical): -0.3 to 0.3g (near zero - horizontal position)
  - X or Z: 0.8 to 1.1g (gravity shifts to horizontal axis)
  - Magnitude: 0.8 to 1.2g

Gyroscope:
  - Magnitude: <30°/s
  - All axes: ±30°/s range

Angles:
  - Pitch or Roll: ±70° to ±100° (horizontal orientation)
  - Horizontal: True (is_horizontal flag)
```

**Key Features:**
- **Y-axis acceleration near 0** (key indicator of horizontal position)
- **X or Z axis shows ~1g** (gravity shifted to horizontal plane)
- Very low foot pressure
- Low movement variance

### 5. Jumping ✅

**Validation Status:** Tested with real sensors (archived/accelerator/blue/analyze.py:71-74)

**Foot Pressure Signature:**
```
Pattern: High pressure spikes alternating with near-zero (airborne phase)
Max Pressure: 400-1000+ (very high during landing)
Avg Pressure: 200-600
Active Sensors: 12-18 (full foot impact)
```

**Accelerometer Signature (Y-axis vertical):**
```
Acceleration:
  - Y (vertical): Rapid spikes >1.3g (push-off) or <0.6g (airborne)
  - X, Z: -2.0 to 2.0g
  - Magnitude: 0.8 to 1.8g

Gyroscope:
  - Magnitude: >100°/s (high rotational activity)
  - All axes: ±150°/s range
  - Minimum threshold: 100°/s

Movement Pattern:
  - Spike high: >1.3g (push-off phase)
  - Spike low: <0.6g (airborne phase)
  - Cooldown: 1.0 second between jumps
```

**Key Features:**
- **Rapid Y-axis acceleration spikes** (>1.3g or <0.6g)
- **High gyroscope activity** (>100°/s)
- Alternating high pressure (landing) and zero pressure (airborne)
- Cooldown period prevents multiple rapid detections

---

## Estimated Activity Profiles

**⚠️ WARNING:** The following profiles are **estimates** based on sensor specifications and have **not been validated** with real hardware. Use with caution and validate before deployment.

### 1. Walking (Estimated)

**Foot Pressure Signature:**
```
Pattern: Alternating heel → ball → toe pressure waves
Frequency: ~1-2 Hz (60-120 steps/min)
Max Pressure: 200-400 (moderate)
Active Sensors: 8-18 per foot (rolling contact)
Distribution: Sequential heel → midfoot → ball → toe
```

**Accelerometer Signature:**
```
Acceleration:
  - Vertical (Z): Periodic bounce ±1-2g at step frequency
  - Lateral (X,Y): Smooth sinusoidal sway < 0.5g

Gyroscope:
  - Low angular velocity ±10-30°/s
  - Periodic oscillation matching step frequency

Angles:
  - Roll: Oscillates ±5-10° (weight shift)
  - Pitch: Oscillates ±5-10° (forward/backward tilt)
  - Yaw: Gradual change (turning)
```

**Key Features:**
- Regular periodic pattern
- Low vertical acceleration
- Balanced left/right pressure
- Upright orientation (angles near 0°)

### 2. Running (Estimated)

**Foot Pressure Signature:**
```
Pattern: Rapid heel strikes with high pressure spikes
Frequency: ~2-3 Hz (120-180 steps/min)
Max Pressure: 400-800 (high)
Active Sensors: 10-18 (full foot impact)
Distribution: Strong heel strike → brief midfoot → toe push-off
```

**Accelerometer Signature:**
```
Acceleration:
  - Vertical (Z): High periodic spikes 5-15g (±5g bounce from baseline)
  - Lateral (X,Y): Larger oscillations ±1-2g

Gyroscope:
  - Higher angular velocity ±30-100°/s
  - More rapid changes

Angles:
  - Roll: Larger oscillations ±10-20°
  - Pitch: Forward lean +5 to +15° (running posture)
  - Yaw: Rapid changes during turns
```

**Key Features:**
- High frequency periodic pattern
- High vertical acceleration spikes
- Forward pitch angle
- High gyroscope variance

### 3. Crawling (Estimated)

**Foot Pressure Signature:**
```
Pattern: Very low or zero foot pressure
Frequency: Irregular, ~0.5-1 Hz
Max Pressure: 0-100 (very low)
Active Sensors: 0-8 (minimal contact, mostly toes)
Distribution: Primarily toe area if any contact
```

**Accelerometer Signature:**
```
Acceleration:
  - Horizontal: Gravity shifted to X or Y axis (~9.8g)
  - Vertical (Z): Near 0g

Gyroscope:
  - Low angular velocity ±5-20°/s
  - Slow, controlled movements

Angles:
  - Roll: ±70-90° (horizontal orientation)
  - Pitch: ±70-90° (horizontal orientation)
  - One of roll/pitch near ±90°
```

**Key Features:**
- **Critical**: Horizontal orientation (roll or pitch ≈ ±90°)
- Near-zero foot pressure
- Gravity vector rotated to horizontal plane
- Low movement dynamics

### 4. Climbing (Estimated)

**Foot Pressure Signature:**
```
Pattern: High localized pressure at ball/toe
Frequency: ~0.5-1.5 Hz (slow stepping)
Max Pressure: 300-600 (high at contact points)
Active Sensors: 4-10 (concentrated at front of foot)
Distribution: Ball and toe area (positions 4-7, 0-3)
```

**Accelerometer Signature:**
```
Acceleration:
  - Vertical (Z): Periodic lifts +2 to +5g
  - Forward/back (Y): Varies with ladder angle

Gyroscope:
  - Moderate angular velocity ±20-50°/s
  - Step-by-step motion

Angles:
  - Pitch: Forward tilt +20 to +60° (ladder climbing)
  - Roll: Mostly stable ±5°
  - Periodic vertical motion
```

**Key Features:**
- Forward pitch angle (leaning into ladder)
- High pressure at ball/toe
- Periodic vertical acceleration
- Low lateral sway

### 5. Kneeling (Estimated)

**Foot Pressure Signature:**
```
Pattern: Localized pressure at toes or heel
Frequency: Near-static with occasional shifts
Max Pressure: 100-200 (low-moderate)
Active Sensors: 4-8 (localized contact)
Distribution: Either toe area (0-3) OR heel area (14-17)
```

**Accelerometer Signature:**
```
Acceleration:
  - Variable based on kneeling posture
  - Often angled (not fully upright)

Gyroscope:
  - Low ±5-15°/s
  - Occasional adjustments

Angles:
  - Pitch: Often forward +15 to +45° (leaning)
  - Roll: ±10°
  - Not horizontal, not fully upright
```

**Key Features:**
- Localized foot pressure (toe or heel only)
- Forward pitch (leaning posture)
- Low movement dynamics
- Asymmetric pressure distribution

### 6. Carrying (Estimated)

**Foot Pressure Signature:**
```
Pattern: Asymmetric pressure between feet
Frequency: Similar to walking ~1-2 Hz but slower
Max Pressure: Higher than normal walking (300-600)
Active Sensors: 10-18 (full contact)
Distribution: Uneven left/right, increased overall pressure
```

**Accelerometer Signature:**
```
Acceleration:
  - Higher baseline load (compensating for weight)
  - Asymmetric lateral movement

Gyroscope:
  - Moderate ±20-50°/s
  - Less smooth than normal walking

Angles:
  - Roll: Asymmetric tilt (compensating for load)
  - Pitch: May be forward or backward (load position)
  - Less regular pattern than walking
```

**Key Features:**
- **Critical**: Asymmetric left/right pressure
- Higher than normal pressure
- Irregular gait pattern
- Compensatory body angles

### 7. Hose_Operation (Estimated)

**Foot Pressure Signature:**
```
Pattern: Wide stance, stable pressure
Frequency: Mostly static with occasional adjustments
Max Pressure: 200-400 (distributed)
Active Sensors: 14-18 (wide foot contact)
Distribution: Even across both feet, wide stance
```

**Accelerometer Signature:**
```
Acceleration:
  - Upper body movement (aiming/directing hose)
  - Feet stable, upper body dynamic

Gyroscope:
  - Moderate ±30-80°/s (upper body rotation)
  - Feet relatively stable

Angles:
  - Variable based on hose direction
  - Dynamic upper body, stable lower body
```

**Key Features:**
- Stable foot pressure (wide stance)
- Dynamic upper body (gyroscope activity)
- Varied pressure as weight shifts
- Moderate angular velocity

### 8. Idle (Estimated)

**Foot Pressure Signature:**
```
Pattern: Low irregular pressure
Frequency: Random, < 0.5 Hz
Max Pressure: 0-150 (low)
Active Sensors: Variable 0-18
Distribution: Random, inconsistent
```

**Accelerometer Signature:**
```
Acceleration:
  - Random small movements
  - No clear pattern

Gyroscope:
  - Low random values ±5-20°/s
  - No periodicity

Angles:
  - Variable, no consistent pattern
  - May be any orientation
```

**Key Features:**
- No clear pattern in any sensor
- Low activity across all sensors
- High entropy/randomness
- May include sitting, lying down

---

## Feature Engineering

### Time-Domain Features

**From Foot Pressure Data:**

| Feature | Formula | Description | Use Case |
|---------|---------|-------------|----------|
| Mean Pressure | `mean(values)` | Average pressure level | Overall load |
| Max Pressure | `max(values)` | Peak pressure | Impact detection |
| Pressure Variance | `var(values)` | Variability | Movement vs static |
| Active Sensor Count | `count(values > threshold)` | Contact area | Foot placement |
| Left-Right Asymmetry | `abs(mean(left) - mean(right))` | Balance | Carrying, injury |
| Toe-Heel Ratio | `mean(toe_sensors) / mean(heel_sensors)` | Weight distribution | Gait phase |
| Pressure Gradient | `diff(values)` | Rate of change | Transition speed |

**From Accelerometer Data:**

| Feature | Formula | Description | Use Case |
|---------|---------|-------------|----------|
| Acceleration Magnitude | `sqrt(x² + y² + z²)` | Total acceleration | Movement intensity |
| Vertical Component | `acc.z` | Up/down motion | Bouncing, jumping |
| Horizontal Component | `sqrt(x² + y²)` | Lateral motion | Sway, turning |
| Gyro Magnitude | `sqrt(gyro.x² + gyro.y² + gyro.z²)` | Rotational speed | Agility |
| Angle Variance | `var([roll, pitch, yaw])` | Posture stability | Balance |
| Orientation | `[roll, pitch, yaw]` | Body position | Posture detection |
| Pitch Threshold | `pitch > 70°` | Horizontal detection | Crawling |
| Roll Threshold | `roll > 70°` | Horizontal detection | Crawling |

### Frequency-Domain Features

**Fourier Transform Analysis:**

```python
# Compute FFT of foot pressure time series
fft_values = np.fft.fft(pressure_window)
frequencies = np.fft.fftfreq(len(pressure_window), d=sample_period)

# Features:
dominant_frequency = frequencies[np.argmax(np.abs(fft_values))]
spectral_energy = np.sum(np.abs(fft_values)**2)
frequency_std = np.std(np.abs(fft_values))
```

**Use Cases:**
- Gait frequency detection (walking vs running)
- Periodicity measurement
- Irregular motion detection

### Statistical Features (500ms Window)

```python
def extract_window_features(pressure_values, accel_values):
    """Extract statistical features from 500ms window."""
    features = {
        # Pressure stats
        'pressure_mean': np.mean(pressure_values),
        'pressure_std': np.std(pressure_values),
        'pressure_min': np.min(pressure_values),
        'pressure_max': np.max(pressure_values),
        'pressure_range': np.ptp(pressure_values),
        'pressure_median': np.median(pressure_values),
        'pressure_iqr': np.percentile(pressure_values, 75) - np.percentile(pressure_values, 25),

        # Acceleration stats
        'acc_magnitude_mean': np.mean(np.linalg.norm(accel_values, axis=1)),
        'acc_magnitude_std': np.std(np.linalg.norm(accel_values, axis=1)),
        'acc_z_mean': np.mean(accel_values[:, 2]),
        'acc_z_std': np.std(accel_values[:, 2]),

        # Angle stats
        'roll_mean': np.mean(angles[:, 0]),
        'roll_std': np.std(angles[:, 0]),
        'pitch_mean': np.mean(angles[:, 1]),
        'pitch_std': np.std(angles[:, 1]),

        # Derived
        'is_horizontal': np.abs(pitch_mean) > 70 or np.abs(roll_mean) > 70,
        'is_upright': np.abs(pitch_mean) < 15 and np.abs(roll_mean) < 15,
    }
    return features
```

### Cross-Sensor Features

**Correlation between Sensors:**

```python
# Foot pressure correlation with vertical acceleration
corr_pressure_acc_z = np.corrcoef(
    foot_pressure_sum,
    accelerometer_z
)[0, 1]

# Left-right foot correlation (gait symmetry)
corr_left_right = np.corrcoef(
    left_foot_pressure,
    right_foot_pressure
)[0, 1]
```

**Use Cases:**
- Gait symmetry analysis
- Impact synchronization
- Coordination detection

---

## Data Preprocessing

### Windowing Strategy

**Current Implementation:** 500ms windows

**Rationale:**
- Captures ~5-10 foot pressure readings (~10 Hz)
- Captures ~10 accelerometer readings (~20 Hz)
- Long enough for pattern recognition
- Short enough for real-time detection

**Alternative Window Sizes:**

| Window Size | Use Case | Pros | Cons |
|-------------|----------|------|------|
| 250ms | Real-time detection | Fast response | May miss patterns |
| 500ms | **Current (balanced)** | Good balance | Some lag |
| 1000ms | Gait cycle analysis | Full walking cycle | High latency |
| 2000ms | Activity transitions | Context awareness | Very slow response |

### Overlapping Windows

**Sliding Window with 50% Overlap:**

```python
window_size = 500  # ms
overlap = 250  # ms (50%)

for t in range(0, total_duration, overlap):
    window_data = data[t:t+window_size]
    features = extract_features(window_data)
    predict(features)
```

**Benefits:**
- Smoother predictions
- Better transition detection
- Reduced edge effects

### Normalization

**Per-User Normalization:**

```python
# Z-score normalization
mean = np.mean(user_training_data)
std = np.std(user_training_data)
normalized = (data - mean) / std
```

**Per-Sensor Normalization:**

```python
# Min-max normalization per sensor
for sensor_idx in range(18):
    sensor_data = pressure[:, sensor_idx]
    min_val = np.min(sensor_data)
    max_val = np.max(sensor_data)
    normalized[:, sensor_idx] = (sensor_data - min_val) / (max_val - min_val)
```

**Accelerometer Normalization:**

```python
# Gravity normalization (already in g units, but remove bias)
acc_magnitude = np.linalg.norm(acc, axis=1)
acc_normalized = acc / acc_magnitude[:, np.newaxis] * 9.8
```

### Handling Missing Data

**Strategies:**

1. **Forward Fill**: Use last known value
2. **Interpolation**: Linear interpolation between valid points
3. **Zero Fill**: Fill with 0 (foot pressure only)
4. **Drop Window**: Exclude windows with > 20% missing data

### Outlier Removal

**IQR Method:**

```python
Q1 = np.percentile(data, 25)
Q3 = np.percentile(data, 75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# Clip outliers
data_clean = np.clip(data, lower_bound, upper_bound)
```

---

## Pattern Recognition Strategies

### Rule-Based Thresholds (Baseline)

**Simple Activity Detection:**

```python
def detect_activity_rule_based(features):
    # Crawling: Horizontal orientation
    if abs(features['pitch']) > 70 or abs(features['roll']) > 70:
        if features['pressure_mean'] < 50:
            return 'Crawling'

    # Standing: Low variance, upright
    if features['pressure_std'] < 20 and features['gyro_magnitude'] < 10:
        if abs(features['pitch']) < 10 and abs(features['roll']) < 10:
            return 'Standing'

    # Running: High frequency, high acceleration
    if features['step_frequency'] > 2.5 and features['acc_z_max'] > 5:
        return 'Running'

    # Walking: Moderate frequency, upright
    if 1 < features['step_frequency'] < 2.5:
        if abs(features['pitch']) < 20:
            return 'Walking'

    return 'Idle'
```

### Machine Learning Approaches

**Recommended Architectures:**

1. **LSTM (Long Short-Term Memory)**
   - Best for: Sequential patterns (walking, running)
   - Input: Time series of windows
   - Captures temporal dependencies

2. **CNN (Convolutional Neural Network)**
   - Best for: Spatial patterns (foot pressure distribution)
   - Input: 2D pressure maps over time
   - Learns local features

3. **Transformer**
   - Best for: Long-range dependencies
   - Input: Sequence of feature vectors
   - Attention mechanism for context

4. **Random Forest / XGBoost**
   - Best for: Engineered features
   - Input: Statistical features from windows
   - Fast, interpretable

### Training Strategy

**Dataset Split:**

```
Training:   60% of sessions (balanced across activities)
Validation: 20% of sessions
Test:       20% of sessions (held-out users if possible)
```

**Class Balancing:**

```python
# Oversample minority classes or undersample majority
from imblearn.over_sampling import SMOTE

X_resampled, y_resampled = SMOTE().fit_resample(X_train, y_train)
```

**Data Augmentation:**

- Time shifting (shift windows by ±100ms)
- Adding Gaussian noise (simulate sensor noise)
- Scaling (simulate different user weights)
- Rotation (accelerometer only)

---

## Implementation Examples

### Example 1: Crawling Detection (Rule-Based)

```python
def is_crawling(acc_data, pressure_data):
    """Simple crawling detection based on horizontal orientation."""
    # Extract angles
    roll = np.mean([d['angle']['roll'] for d in acc_data])
    pitch = np.mean([d['angle']['pitch'] for d in acc_data])

    # Extract pressure
    avg_pressure = np.mean([d['data']['avg'] for d in pressure_data])

    # Check horizontal orientation + low foot pressure
    horizontal = (abs(roll) > 70) or (abs(pitch) > 70)
    low_pressure = avg_pressure < 100

    return horizontal and low_pressure
```

### Example 2: Gait Frequency Detection

```python
def detect_gait_frequency(foot_pressure_window):
    """Detect step frequency using autocorrelation."""
    # Compute autocorrelation
    autocorr = np.correlate(foot_pressure_window, foot_pressure_window, mode='full')
    autocorr = autocorr[len(autocorr)//2:]

    # Find peaks (step periods)
    peaks, _ = scipy.signal.find_peaks(autocorr, distance=5)

    if len(peaks) > 0:
        period = np.mean(np.diff(peaks)) * sample_interval
        frequency = 1.0 / period
        return frequency
    return 0
```

### Example 3: Activity Classifier (ML)

```python
import tensorflow as tf

def build_lstm_classifier(num_features, num_classes=9):
    """Build LSTM model for activity classification."""
    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(128, return_sequences=True, input_shape=(None, num_features)),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.LSTM(64, return_sequences=False),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(num_classes, activation='softmax')
    ])

    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    return model

# Train
model = build_lstm_classifier(num_features=270)
model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=50)
```

---

## Key Takeaways

### Critical Features by Activity

| Activity | Most Important Features |
|----------|------------------------|
| Walking | Step frequency (1-2 Hz), upright angles, alternating pressure |
| Running | Step frequency (2-3 Hz), high acc.z spikes, forward pitch |
| Crawling | **Horizontal angles (roll/pitch > 70°)**, low foot pressure |
| Climbing | Forward pitch (20-60°), toe/ball pressure, vertical acceleration |
| Standing | Low variance in all sensors, upright, constant pressure |
| Kneeling | Localized pressure (toe or heel), forward pitch, low gyro |
| Carrying | Asymmetric left/right pressure, high pressure, irregular gait |
| Hose Op | Stable feet, dynamic upper body (gyro), wide stance |
| Idle | No clear patterns, high entropy |

### Sensor Fusion Benefits

Using both foot pressure AND accelerometer dramatically improves accuracy:

- Foot pressure alone: ~60-70% accuracy
- Accelerometer alone: ~50-60% accuracy
- **Combined**: ~85-95% accuracy

Complementary information:
- Pressure: Ground contact, weight distribution
- Accelerometer: Body orientation, movement dynamics

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [SENSOR_SPECIFICATIONS.md](./SENSOR_SPECIFICATIONS.md) - Hardware specs
- [DATA_DICTIONARY.md](./DATA_DICTIONARY.md) - Data field reference
- [ML_INTEGRATION.md](./ML_INTEGRATION.md) - ML pipeline integration
