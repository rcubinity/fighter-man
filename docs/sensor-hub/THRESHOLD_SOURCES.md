# Threshold Value Sources

This document explains where the activity detection threshold values came from and how they were validated.

---

## Primary Source: Archived Live Detection Script

**Location:** `/archived/accelerator/blue/analyze.py` and `live.py`

These scripts were previously used for **real-time posture detection** with the WT901BLE67 IMU sensor mounted on the upper back. The thresholds in these scripts were **empirically tested and validated** through live sensor data.

### Sensor Orientation in Archived Scripts

**IMPORTANT:** The archived scripts assume:
- **Y-axis is VERTICAL** when standing upright
- Sensor mounted on upper back (below neck)
- When standing: `acc.y ≈ 1.0g` (gravity on Y-axis)
- When lying horizontal: `acc.y ≈ 0g`, `acc.x or acc.z ≈ 1.0g`

This is **different** from the current sensor-hub documentation which may assume Z-axis as vertical.

---

## Validated Thresholds from Archived Script

### 1. Standing

**Source:** `analyze.py` lines 50-53

```python
STANDING_ACC_Y_MIN = 0.85      # Minimum Y acceleration for standing (g)
STANDING_ACC_Y_MAX = 1.15      # Maximum Y acceleration for standing (g)
STANDING_PITCH_MAX = 15.0      # Maximum pitch angle for standing (degrees)
STANDING_GYRO_MAX = 50.0       # Maximum gyro activity for stable standing (deg/s)
```

**Detection Logic:** Upright posture with gravity on Y-axis, minimal tilt, low rotational movement.

### 2. Sitting

**Source:** `analyze.py` lines 60-64

```python
SITTING_PITCH_MIN = 15.0       # Minimum pitch for sitting
SITTING_PITCH_MAX = 45.0       # Maximum pitch for sitting
SITTING_ACC_Y_MIN = 0.5        # Y acceleration range for sitting
SITTING_ACC_Y_MAX = 0.9
SITTING_STABILITY_TIME = 2.0   # Seconds to be stable to confirm sitting
```

**Detection Logic:** Moderate forward pitch (leaning back in chair), Y-axis shows partial gravity support, requires 2 seconds of stability to confirm.

**Key Insight:** Sitting has lower Y-axis acceleration than standing because body weight is on the seat, not fully supported by the torso.

### 3. Bent Forward

**Source:** `analyze.py` lines 56-57

```python
BENT_PITCH_MIN = 30.0          # Minimum pitch to consider bent forward (degrees)
BENT_ACC_Y_MAX = 0.7           # Y acceleration decreases when bending
```

**Detection Logic:** High forward pitch angle with reduced Y-axis acceleration.

### 4. Lying Down

**Source:** `analyze.py` lines 67-68

```python
LYING_ACC_Y_MAX = 0.3          # Y acceleration near 0 when lying
LYING_ACC_XZ_MIN = 0.8         # X or Z acceleration should be ~1g when lying
```

**Detection Logic:** Horizontal orientation where gravity shifts to X or Z axis, Y-axis shows minimal acceleration.

### 5. Jumping

**Source:** `analyze.py` lines 71-74

```python
JUMP_ACC_Y_SPIKE_HIGH = 1.3    # Acceleration spike during jump (g)
JUMP_ACC_Y_SPIKE_LOW = 0.6     # Acceleration drop during jump (g)
JUMP_GYRO_THRESHOLD = 100.0    # Gyro activity during jump (deg/s)
JUMP_COOLDOWN = 1.0            # Seconds before detecting another jump
```

**Detection Logic:** Rapid Y-axis acceleration spikes (push-off > 1.3g, airborne < 0.6g) with high gyroscope activity.

---

## Activities Detected by Archived Script

The archived script (`analyze.py`) detects **5 activities:**

1. **Standing** - Upright, stable
2. **Sitting** - Moderate pitch, lower Y-acceleration
3. **Bent Forward** - High pitch angle
4. **Lying Down** - Horizontal orientation
5. **Jumping** - Rapid acceleration spikes

### Detection Priority Order

From `analyze.py` lines 291-345:

```python
# Priority order (highest to lowest):
1. JUMPING       # Transient state, highest priority
2. LYING DOWN    # Horizontal orientation
3. BENT FORWARD  # High pitch angle
4. SITTING       # Moderate pitch + stability requirement
5. STANDING      # Default stable state
```

---

## Additional Activities (Not in Archived Script)

The following activities are **not in the archived script** and require **new thresholds** based on sensor specifications and logical inference:

### 6. Walking

**Estimated Thresholds:**
- Acc Y: 0.8-1.2g (periodic bounce around standing baseline)
- Pitch: ±5-10° (slight forward/backward oscillation)
- Gyro: 10-30°/s (moderate rotational movement)
- Pattern: Periodic at 1-2 Hz (step frequency)

**Rationale:** Similar to standing but with periodic oscillations.

### 7. Running

**Estimated Thresholds:**
- Acc Y: 0.5-1.5g (larger bounce during run stride)
- Pitch: ±10-20° (more pronounced forward lean)
- Gyro: 30-100°/s (higher rotational velocity)
- Pattern: Rapid periodic at 2-3 Hz

**Rationale:** Amplified version of walking with forward lean.

### 8. Crawling

**Estimated Thresholds:**
- Acc Y: 0-0.3g (horizontal, similar to lying down)
- Acc X or Z: 0.8-1.1g (gravity on horizontal axis)
- Pitch or Roll: ±70-90° (horizontal orientation)
- Gyro: <40°/s (controlled movement)

**Rationale:** Similar to lying down but with slow intentional movement.

### 9. Climbing

**Estimated Thresholds:**
- Acc Y: 0.7-1.2g (vertical but variable)
- Pitch: 30-60° (forward tilt for ladder climbing)
- Gyro: 20-80°/s (dynamic upper body)
- Pattern: Periodic vertical movement

**Rationale:** Forward tilt similar to bent forward but with vertical motion.

### 10. Kneeling

**Estimated Thresholds:**
- Acc Y: 0.6-0.9g (partial vertical support)
- Pitch: 30-70° (forward lean on knees)
- Gyro: <30°/s (stable position)

**Rationale:** Between sitting and bent forward, with forward pitch.

### 11. Carrying

**Estimated Thresholds:**
- Acc Y: 0.8-1.2g (similar to walking but may be higher)
- Pitch: ±15-30° (compensatory tilt for load)
- Roll: ±10-30° (lateral compensation)
- Gyro: 10-50°/s (moderate movement)

**Rationale:** Walking-like but with compensatory angles for load.

### 12. Hose_Operation

**Estimated Thresholds:**
- Acc Y: 0.9-1.1g (mostly upright)
- Pitch: ±10-20° (slight forward lean)
- Gyro: 30-80°/s (dynamic upper body aiming hose)

**Rationale:** Standing with upper body movement.

### 13. Idle

**Estimated Thresholds:**
- Acc Y: 0-1.2g (any posture)
- Pitch: Any
- Gyro: <40°/s (minimal movement)
- Pattern: No clear periodic pattern

**Rationale:** Catch-all for miscellaneous low-intensity activities.

---

## Threshold Application Strategy

### For Current Sensor-Hub System

**CRITICAL DECISION NEEDED:**

The archived script assumes **Y-axis = vertical**. The current sensor-hub may assume **Z-axis = vertical** based on WT901BLE67 default orientation.

**Options:**

1. **Use archived Y-axis thresholds directly** - If sensor mounted same way
2. **Convert Y→Z** - If sensor mounted differently (Z-axis up)
3. **Recalibrate** - Test with actual sensor hardware

**Recommended Approach:**
- Test with actual hardware to determine sensor orientation
- If Z-axis is vertical: swap all Y↔Z in thresholds
- If Y-axis is vertical: use archived thresholds as-is

### Coordinate System Mapping

If sensor orientation differs:

| Archived (Y-up) | Current (Z-up) | Mapping |
|-----------------|----------------|---------|
| acc.y = 1.0g (standing) | acc.z = 1.0g | Y → Z |
| acc.y = 0g (lying) | acc.z = 0g | Y → Z |
| acc.x or acc.z = 1.0g (lying) | acc.x or acc.y = 1.0g | X,Z → X,Y |

---

## Validation Status

| Activity | Source | Status |
|----------|--------|--------|
| Standing | Archived script (tested) | ✅ Validated |
| Sitting | Archived script (tested) | ✅ Validated |
| Bent Forward | Archived script (tested) | ✅ Validated |
| Lying Down | Archived script (tested) | ✅ Validated |
| Jumping | Archived script (tested) | ✅ Validated |
| Walking | Estimated from specifications | ⚠️ Needs validation |
| Running | Estimated from specifications | ⚠️ Needs validation |
| Crawling | Estimated (similar to lying) | ⚠️ Needs validation |
| Climbing | Estimated from specifications | ⚠️ Needs validation |
| Kneeling | Estimated from specifications | ⚠️ Needs validation |
| Carrying | Estimated from specifications | ⚠️ Needs validation |
| Hose_Operation | Estimated from specifications | ⚠️ Needs validation |
| Idle | Estimated catch-all | ⚠️ Needs validation |

---

## Testing Recommendations

To validate the estimated thresholds:

1. **Collect Real Data:**
   - Run `live.py` script for each activity
   - Record sensor values during performance
   - Note actual acc, gyro, angle ranges

2. **Update Thresholds:**
   - Adjust ranges based on observed values
   - Add safety margins (±10-20%)
   - Test edge cases (transitions between activities)

3. **Cross-Validation:**
   - Test with multiple subjects
   - Test in different environments
   - Test with firefighter gear vs without

---

## Related Files

- **Archived Source:** `/archived/accelerator/blue/analyze.py` (lines 46-78)
- **Live Detection:** `/archived/accelerator/blue/live.py`
- **Current Thresholds:** `docs/accelerometer_thresholds.json`
- **Documentation:** `docs/ACTIVITY_DETECTION_GUIDE.md`

---

## Revision History

- **2025-12-19:** Initial document created from archived script analysis
- **Status:** Thresholds extracted, coordinate system mapping needed
