# Running Detection Discussion

## Overview

This document discusses the feasibility, implementation strategy, and validation approach for detecting **running** activity using the available sensor suite (foot pressure sensors + 9-axis IMU).

**Status**: Estimated activity requiring real-world validation ⚠️
**Expected Accuracy**: 80-90% with sensor fusion
**Priority**: Medium-High (less common than walking, but critical for emergency response)

---

## 1. Why Running Detection Matters

Running is a high-intensity activity for firefighters during:
- **Emergency response**: Racing to save lives
- **Evacuation**: Quick retreat from danger
- **Equipment retrieval**: Sprinting for critical gear
- **Physical assessment**: Peak exertion indicator
- **Training validation**: PT and drill monitoring

Detecting running enables:
- **Fatigue monitoring**: High metabolic cost tracking
- **Safety alerts**: Sustained sprinting may indicate danger
- **Performance metrics**: Sprint duration, frequency, recovery time
- **Caloric expenditure**: Running burns ~3x more than walking
- **Incident timeline**: Understanding critical moments in operations

---

## 2. Available Sensor Data

### Foot Pressure Sensors (18 per foot, ~10 Hz)

**Running-Relevant Metrics:**
- `max_pressure`: Peak impact force (400-800, much higher than walking)
- `variance`: High temporal variance (150-400, more than walking)
- `active_count`: Fewer simultaneous contacts (4-12, vs 8-18 for walking)
- `pressure_distribution`: Forefoot-heavy (toe/ball) vs heel-strike in walking
- **Flight phase**: Periods with zero pressure (both feet off ground)

**Key Pattern**: Higher impact force + flight phase (both feet airborne briefly)

### Accelerometer/IMU (WT901BLE67, ~20 Hz)

**Running-Relevant Metrics:**
- `acc.y`: Large vertical acceleration spikes (±3-8g during landing)
- `acc.x`, `acc.z`: Higher lateral/forward acceleration (±2-4g)
- `gyro`: Moderate angular velocity (±30-100°/s, higher than walking)
- `angle.pitch`: Slight forward lean (5-15° forward)

**Key Pattern**: High-amplitude periodic vertical acceleration at 2-3.5 Hz (step frequency)

---

## 3. Running Characteristics & Thresholds

### Foot Pressure Thresholds

From `foot_pressure_thresholds.json`:

| Parameter | Running Range | Confidence Weight | Notes |
|-----------|---------------|-------------------|-------|
| **Step Frequency** | **2.0-3.5 Hz** | **HIGH** ⭐⭐⭐ | 120-210 steps/min (faster than walking) |
| **Max Pressure** | **400-800** | **HIGH** ⭐⭐⭐ | High impact force (2x walking) |
| Variance | 150-400 | HIGH ⭐⭐⭐ | Very dynamic pattern |
| Average Pressure | 150-400 | MEDIUM ⭐⭐ | Higher sustained force |
| Active Sensors | 4-12 | MEDIUM ⭐⭐ | Fewer contacts (forefoot strike) |
| **Flight Phase Ratio** | **20-40%** | **HIGH** ⭐⭐⭐ | Time with zero pressure |
| Left-Right Asymmetry | < 150 | LOW ⭐ | Slightly higher than walking |

**Confidence Calculation:**
```
Strong Confidence (>80%):
  step_frequency IN [2.0, 3.5] AND max_pressure > 400 AND flight_phase > 20%

Moderate Confidence (60-80%):
  step_frequency > 2.2 AND variance > 150

Weak Confidence (40-60%):
  max_pressure > 350 AND variance > 100
```

### Accelerometer Thresholds

From `ACTIVITY_DETECTION_GUIDE.md`:

| Feature | Running Pattern | Detection Method |
|---------|----------------|------------------|
| **Vertical Acc (Y)** | **±3-8g spikes** | Peak detection at 2-3 Hz |
| Forward Acc (Z) | ±2-4g periodic | Propulsion force |
| Lateral Acc (X) | ±1-2g | Side-to-side motion |
| **Gyroscope** | **±30-100°/s** | Higher rotation than walking |
| Pitch | +5 to +15° | Forward lean |
| Roll | ±10-20° | Weight transfer |
| **Impact Detection** | **acc.y < -2g** | Landing shock ⭐⭐⭐ |

**Key Insight**: Running has distinctive **impact spikes** (acc.y < -2g during landing) and **flight phase** (both feet off ground) that walking lacks.

---

## 4. Detection Algorithm

### Option 1: Threshold-Based (Recommended for MVP)

**Advantages**: Fast, interpretable, no training required
**Expected Accuracy**: 70-80%

```javascript
function detectRunning(footData, accelData, windowSize = 500) {
    // Step 1: Check upright/forward-leaning posture
    const isRunningPosture = (
        accelData.angle.pitch > -5 && accelData.angle.pitch < 20 &&
        Math.abs(accelData.angle.roll) < 25 &&
        accelData.acc.y > 0.5  // Not lying down
    );

    if (!isRunningPosture) return { activity: null, confidence: 0 };

    // Step 2: Calculate step frequency
    const stepFreq = estimateStepFrequency(footData.pressures);

    // Step 3: Check for high impact (acceleration spikes)
    const hasHighImpact = accelData.acc.y < -2.0 || accelData.acc.y > 3.0;

    // Step 4: Check max pressure
    const maxPressure = Math.max(footData.left_max, footData.right_max);

    // Step 5: Detect flight phase (periods with zero pressure)
    const flightPhaseRatio = detectFlightPhase(footData.pressures);

    // Decision logic
    if (stepFreq >= 2.0 && stepFreq <= 3.5 && maxPressure > 400) {
        if (flightPhaseRatio > 20 || hasHighImpact) {
            return { activity: 'Running', confidence: 85 };
        } else {
            return { activity: 'Running', confidence: 65 };
        }
    } else if (stepFreq > 1.8 && maxPressure > 350 && hasHighImpact) {
        return { activity: 'Running', confidence: 60 };
    }

    return { activity: null, confidence: 0 };
}
```

### Option 2: Sensor Fusion (Best Accuracy)

**Advantages**: 80-90% accuracy, robust to edge cases
**Expected Accuracy**: 80-90%

```javascript
function detectRunningFusion(footData, accelData, windowSize = 500) {
    // Extract features from both sensors
    const footFeatures = {
        stepFreq: estimateStepFrequency(footData.pressures),
        maxPressure: Math.max(footData.left_max, footData.right_max),
        variance: calculateVariance(footData.pressures),
        flightPhaseRatio: detectFlightPhase(footData.pressures),
        avgPressure: footData.avg_pressure
    };

    const accelFeatures = {
        verticalImpact: detectImpactSpikes(accelData.acc.y),
        gyroMagnitude: calculateGyroMagnitude(accelData.gyro),
        forwardLean: accelData.angle.pitch,
        maxAcceleration: Math.max(
            Math.abs(accelData.acc.x),
            Math.abs(accelData.acc.y),
            Math.abs(accelData.acc.z)
        )
    };

    // Score each feature
    let score = 0;

    // Foot pressure scoring (50% weight)
    if (footFeatures.stepFreq >= 2.0 && footFeatures.stepFreq <= 3.5) score += 20;
    if (footFeatures.maxPressure > 400) score += 15;
    if (footFeatures.flightPhaseRatio > 20) score += 15;

    // Accelerometer scoring (50% weight)
    if (accelFeatures.verticalImpact > 3.0) score += 20;
    if (accelFeatures.gyroMagnitude > 30) score += 10;
    if (accelFeatures.forwardLean > 5 && accelFeatures.forwardLean < 20) score += 10;
    if (accelFeatures.maxAcceleration > 3.0) score += 10;

    // Convert score to confidence
    const confidence = Math.min(score, 100);

    if (confidence >= 70) {
        return { activity: 'Running', confidence };
    }

    return { activity: null, confidence: 0 };
}
```

---

## 5. Feature Engineering

### Critical Features (Importance Ranking)

1. **Step Frequency (2.0-3.5 Hz)** ⭐⭐⭐⭐⭐
   - Most distinctive feature vs walking (1.0-2.0 Hz)
   - Can be calculated from both sensors
   - Higher frequency = higher confidence

2. **Impact Spikes (acc.y < -2g or > 3g)** ⭐⭐⭐⭐⭐
   - Unique to running (walking: ±1-2g)
   - Landing impact is very distinctive
   - Easy to detect with simple threshold

3. **Flight Phase (20-40%)** ⭐⭐⭐⭐
   - Both feet off ground (running-specific)
   - Detected as zero pressure periods
   - Walking has no flight phase

4. **Max Pressure (> 400)** ⭐⭐⭐⭐
   - Higher impact than walking (200-500)
   - Forefoot strike pattern
   - Correlates with running speed

5. **High Variance (150-400)** ⭐⭐⭐
   - More dynamic than walking (50-200)
   - Indicates rapid changes in force

6. **Forward Lean (5-15°)** ⭐⭐
   - Slight forward pitch during running
   - Helps distinguish from jumping (more vertical)

### Feature Calculation Methods

**Flight Phase Detection:**
```javascript
function detectFlightPhase(pressureWindow, threshold = 20) {
    let flightFrames = 0;
    for (let i = 0; i < pressureWindow.length; i++) {
        // Both feet off ground if total pressure < threshold
        if (pressureWindow[i].left + pressureWindow[i].right < threshold) {
            flightFrames++;
        }
    }
    const flightPhaseRatio = (flightFrames / pressureWindow.length) * 100;
    return flightPhaseRatio;
}
```

**Impact Spike Detection:**
```javascript
function detectImpactSpikes(accelYWindow) {
    const impacts = accelYWindow.filter(y => y < -2.0 || y > 3.0);
    return impacts.length / accelYWindow.length;  // Ratio of high-impact frames
}
```

**Step Frequency (Zero-Crossing for Running):**
```javascript
function estimateStepFrequency(pressureWindow, samplingRate = 10) {
    // Use vertical acceleration for better accuracy at high speeds
    const mean = pressureWindow.reduce((a, b) => a + b) / pressureWindow.length;
    let crossings = 0;

    for (let i = 1; i < pressureWindow.length; i++) {
        if ((pressureWindow[i-1] - mean) * (pressureWindow[i] - mean) < 0) {
            crossings++;
        }
    }

    const frequency = (crossings / 2) / (pressureWindow.length / samplingRate);
    return frequency;
}
```

---

## 6. Distinguishing Running from Similar Activities

### Running vs. Walking

| Feature | Running | Walking |
|---------|---------|---------|
| **Step Frequency** | **2.0-3.5 Hz** | **1.0-2.0 Hz** ⭐⭐⭐ |
| **Impact Force** | **400-800** | **200-500** ⭐⭐⭐ |
| **Flight Phase** | **20-40%** | **0%** ⭐⭐⭐ |
| Vertical Acc | ±3-8g | ±1-2g |
| Gyroscope | ±30-100°/s | ±10-30°/s |

**Decision**: If step frequency > 2.2 Hz OR flight phase > 15%, classify as running

### Running vs. Jumping

| Feature | Running | Jumping |
|---------|---------|---------|
| Pattern | Periodic (2-3 Hz) | Intermittent |
| Flight Phase | 20-40% | 50-80% (higher) |
| Max Acc | ±3-8g | ±5-15g (higher) |
| Forward Motion | Yes (pitch > 0) | Minimal (pitch ~0) |
| Duration | Sustained (>2s) | Brief (<1s per jump) |

**Decision**: Sustained periodicity = running, brief intense spikes = jumping

### Running vs. Jumping Jacks / Plyometrics

| Feature | Running | Jumping Jacks |
|---------|---------|---------------|
| Forward Lean | 5-15° | Near 0° (vertical) |
| Foot Pattern | Alternating L/R | Synchronized |
| Frequency | 2-3 Hz | 1-2 Hz (slower) |
| Lateral Motion | Low (acc.x < 2g) | High (acc.x > 3g) |

**Decision**: Forward lean + alternating feet = running

---

## 7. Implementation Roadmap

### Phase 1: Basic Threshold Detection (Week 1) ✅

**Goal**: Detect running with >70% accuracy using simple thresholds

**Tasks**:
- [ ] Add running thresholds to `activityDetector.js`
- [ ] Implement step frequency estimation (optimized for 2-3 Hz)
- [ ] Implement impact spike detection (`acc.y < -2g`)
- [ ] Add flight phase detection (zero pressure periods)
- [ ] Test with simulated data

**Expected Outcome**: Running detection works in ideal conditions

### Phase 2: Data Collection (Week 2) ⚠️

**Goal**: Collect real running data from multiple users

**Tasks**:
- [ ] Record 10+ running sessions (different speeds: jog, run, sprint)
- [ ] Label ground truth activity manually
- [ ] Analyze actual step frequencies (may vary 2.0-4.0 Hz)
- [ ] Measure flight phase ratios at different speeds
- [ ] Validate max pressure thresholds

**Expected Outcome**: Validation of estimated thresholds

### Phase 3: Sensor Fusion (Week 3) 🎯

**Goal**: Achieve 80-90% accuracy with combined sensors

**Tasks**:
- [ ] Implement feature scoring system
- [ ] Tune weights based on collected data
- [ ] Add temporal context (require 1-2s of sustained pattern)
- [ ] Implement hysteresis (prevent flapping between walking/running)

**Expected Outcome**: Production-ready running detection

### Phase 4: Speed Classification (Week 4) 🚀

**Goal**: Distinguish jogging vs sprinting

**Tasks**:
- [ ] Define sub-categories: Jogging (2.0-2.5 Hz), Running (2.5-3.0 Hz), Sprinting (3.0-3.5 Hz)
- [ ] Correlate step frequency with actual speed
- [ ] Add intensity metrics (impact force, acceleration magnitude)

**Expected Outcome**: Granular running intensity classification

---

## 8. Validation Metrics

### Test Scenarios

1. **Jogging**: Slow run (2.0-2.5 Hz), moderate effort
2. **Running**: Normal pace (2.5-3.0 Hz), sustainable
3. **Sprinting**: Maximum effort (3.0-3.5 Hz), brief bursts
4. **Running with Gear**: Weighted vest or backpack (higher impact)
5. **Uphill Running**: Forward lean increases, step freq may decrease
6. **Downhill Running**: Backward lean, higher impact force

### Success Criteria

| Metric | Target | Acceptable | Notes |
|--------|--------|------------|-------|
| **Precision** | >80% | >70% | % of detected running that's actually running |
| **Recall** | >85% | >75% | % of actual running that's detected |
| **Latency** | <1s | <2s | Time to detect after running starts |
| **False Positives** | <8% | <15% | Walking/jumping misclassified as running |
| **Missed Detections** | <12% | <20% | Running not detected |

### Confusion Matrix (Expected)

|  | Predicted: Running | Predicted: Other |
|--|-------------------|-----------------|
| **Actual: Running** | 85% (TP) | 15% (FN) |
| **Actual: Walking** | 5% (FP) | 95% (TN) |
| **Actual: Jumping** | 8% (FP) | 92% (TN) |

---

## 9. Known Challenges & Mitigations

### Challenge 1: Walking-Running Transition

**Problem**: Ambiguous zone around 2.0 Hz (fast walking vs slow jogging).

**Mitigation**:
- Use **hysteresis**: Once classified as running, require step freq < 1.8 Hz to switch back to walking
- Check for flight phase (walking = 0%, running > 15%)
- Require 1-2 seconds of sustained pattern before confirming

### Challenge 2: Running with Heavy Load

**Problem**: Step frequency may decrease (1.8-2.5 Hz instead of 2.0-3.5 Hz) when carrying equipment.

**Mitigation**:
- Relax step frequency lower bound to 1.8 Hz
- Rely more on impact force (max pressure > 400)
- Check for flight phase (still present even with load)

### Challenge 3: Treadmill vs Ground Running

**Problem**: Treadmill running has less forward propulsion (acc.z lower).

**Mitigation**:
- Don't rely heavily on forward acceleration
- Focus on vertical impact and flight phase (consistent across surfaces)
- Consider allowing user to tag "treadmill mode" if needed

### Challenge 4: Sensor Sampling Rate Limitations

**Problem**: 10 Hz foot pressure may miss brief flight phases (< 100ms).

**Mitigation**:
- Use accelerometer (20 Hz) as primary for high-frequency detection
- Interpolate foot pressure data to estimate flight phase
- Require multiple consecutive windows for confirmation

### Challenge 5: Fatigue Effects

**Problem**: As runner fatigues, gait changes (step freq decreases, impact varies).

**Mitigation**:
- Allow wider threshold ranges (1.8-3.5 Hz instead of 2.0-3.5 Hz)
- Track "running degradation" as potential fatigue indicator
- Use median values over 5-second windows (smooth out irregularities)

---

## 10. Speed & Intensity Classification

### Sub-Categories

Once running is detected, classify intensity:

| Intensity | Step Frequency | Max Pressure | Avg Acc Magnitude | Use Case |
|-----------|---------------|--------------|-------------------|----------|
| **Jogging** | 2.0-2.5 Hz | 300-500 | 2-4g | Warm-up, recovery |
| **Running** | 2.5-3.0 Hz | 400-600 | 4-6g | Sustained pace |
| **Sprinting** | 3.0-3.5 Hz | 600-800+ | 6-10g | Emergency response |

### Caloric Expenditure Estimation

```javascript
function estimateCalories(runningIntensity, durationSeconds, userWeight = 80) {
    const MET = {
        'Jogging': 7.0,   // Metabolic Equivalent of Task
        'Running': 9.0,
        'Sprinting': 12.0
    };

    const met = MET[runningIntensity] || 9.0;
    const caloriesPerMinute = (met * 3.5 * userWeight) / 200;
    return caloriesPerMinute * (durationSeconds / 60);
}
```

### Fatigue Index

Track gait degradation over time:

```javascript
function calculateFatigueIndex(runningWindows) {
    const initialFreq = runningWindows[0].stepFrequency;
    const currentFreq = runningWindows[runningWindows.length - 1].stepFrequency;

    const freqDecline = ((initialFreq - currentFreq) / initialFreq) * 100;

    // Fatigue increases as step frequency drops
    if (freqDecline > 15) return 'High Fatigue';
    if (freqDecline > 8) return 'Moderate Fatigue';
    return 'Low Fatigue';
}
```

---

## 11. Integration with Existing System

### Adding to `activityDetector.js`

```javascript
// Add to detection priority order (before Walking, after Jumping)
const detectionOrder = [
    'Lying_Down',
    'Jumping',
    'Running',      // <-- Add here
    'Bent_Forward',
    'Walking',
    'Sitting',
    'Standing'
];
```

### Color Mapping for Timeline

Suggested color: **Orange** `#f97316` (orange-500) - indicates high intensity

```javascript
const activityColors = {
    'Sitting': '#22c55e',      // green-500
    'Standing': '#3b82f6',     // blue-500
    'Walking': '#06b6d4',      // cyan-500 (suggested)
    'Running': '#f97316',      // orange-500 (suggested)
    'Lying_Down': '#f59e0b',   // amber-500
    'Bent_Forward': '#8b5cf6', // violet-500
    'Jumping': '#ef4444'       // red-500
};
```

### Backend Label Storage

No changes needed - `detected_activities` dictionary already supports any activity string.

---

## 12. Next Steps

### Immediate Actions

1. **Implement basic running detector** in `activityDetector.js`
2. **Add running to activity colors** in `record.html`
3. **Collect validation data**: Record 3-5 running sessions at different speeds
4. **Test confusion with walking**: Verify clear separation at 2.0 Hz threshold

### Future Enhancements

- **Speed estimation**: Correlate step frequency with actual running speed (requires calibration)
- **Stride length calculation**: Estimate using acceleration integration
- **Running efficiency metrics**: Vertical oscillation, ground contact time
- **Training load monitoring**: Cumulative stress from running sessions

---

## 13. References

- `foot_pressure_thresholds.json` (lines 45-59): Running pressure thresholds
- `ACTIVITY_DETECTION_GUIDE.md` (lines 299-331): Running estimation details
- `SENSOR_SPECIFICATIONS.md` (lines 113-312): Accelerometer running patterns
- `DATA_DICTIONARY.md` (lines 244-296): Value ranges by activity

---

## Conclusion

**Running detection is feasible** with the current sensor suite, though slightly more challenging than walking due to higher speeds and variability. The key distinguishing features are:

1. **Higher step frequency (2.0-3.5 Hz)** - clear separation from walking (1.0-2.0 Hz)
2. **Impact spikes (acc.y > 3g or < -2g)** - unique to high-intensity movement
3. **Flight phase (20-40%)** - both feet off ground, unlike walking

**Recommended Approach**:
- Start with **threshold-based detection** using step frequency + impact detection (70-80% accuracy)
- Progress to **sensor fusion** with flight phase analysis (80-90% accuracy)
- Add **intensity classification** (jogging/running/sprinting) for richer insights

**Status**: Ready for implementation after walking detection is validated 🚀

**Priority**: Implement after walking (more common activity), but before advanced activities like crawling/climbing.
