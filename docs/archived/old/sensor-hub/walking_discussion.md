# Walking Detection Discussion

## Overview

This document discusses the feasibility, implementation strategy, and validation approach for detecting **walking** activity using the available sensor suite (foot pressure sensors + 9-axis IMU).

**Status**: Estimated activity requiring real-world validation ⚠️
**Expected Accuracy**: 85-95% with sensor fusion
**Priority**: High (common firefighter activity)

---

## 1. Why Walking Detection Matters

Walking is a fundamental activity for firefighters:
- **Navigation**: Moving through buildings, scenes, and terrain
- **Assessment**: Walking around to evaluate situations
- **Equipment transport**: Carrying gear while walking
- **Fatigue monitoring**: Gait changes can indicate exhaustion
- **Context switching**: Transition between standing and more intense activities

Detecting walking enables:
- Activity timeline segmentation
- Caloric expenditure estimation
- Gait analysis for fatigue/injury detection
- Contextual understanding of firefighter operations

---

## 2. Available Sensor Data

### Foot Pressure Sensors (18 per foot, ~10 Hz)

**Walking-Relevant Metrics:**
- `avg_pressure`: Average pressure across active sensors (80-300 for walking)
- `max_pressure`: Peak pressure during heel strike (200-500)
- `active_count`: Number of sensors with pressure > threshold (8-18)
- `variance`: Temporal variance in pressure readings (50-200 indicates movement)
- `left_pressure` / `right_pressure`: Asymmetry analysis (< 100 diff for normal gait)

**Key Pattern**: Alternating pressure between left and right feet at step frequency

### Accelerometer/IMU (WT901BLE67, ~20 Hz)

**Walking-Relevant Metrics:**
- `acc.x`, `acc.y`, `acc.z`: Linear acceleration (periodic vertical bounce at step freq)
- `gyro.x`, `gyro.y`, `gyro.z`: Angular velocity (±10-30°/s oscillation)
- `angle.roll`, `angle.pitch`, `angle.yaw`: Body orientation (near 0° for upright walking)

**Key Pattern**: Regular periodic oscillation in vertical axis at 1-2 Hz (step frequency)

---

## 3. Walking Characteristics & Thresholds

### Foot Pressure Thresholds

From `foot_pressure_thresholds.json`:

| Parameter | Walking Range | Confidence Weight | Notes |
|-----------|---------------|-------------------|-------|
| **Step Frequency** | **1.0-2.0 Hz** | **HIGH** ⭐⭐⭐ | 60-120 steps/min (most distinctive) |
| Variance | 50-200 | HIGH ⭐⭐⭐ | Dynamic gait pattern |
| Average Pressure | 80-300 | MEDIUM ⭐⭐ | Moderate contact |
| Max Pressure | 200-500 | MEDIUM ⭐⭐ | Heel strike force |
| Active Sensors | 8-18 | MEDIUM ⭐⭐ | Multiple contact points |
| Left-Right Asymmetry | < 100 | LOW ⭐ | Balanced gait (healthy walker) |

**Confidence Calculation:**
```
Strong Confidence (>80%):
  variance > 80 AND step_frequency IN [1.0, 2.0]

Moderate Confidence (60-80%):
  avg IN [100, 250] AND active_count > 10

Weak Confidence (40-60%):
  variance > 50
```

### Accelerometer Thresholds

From `ACTIVITY_DETECTION_GUIDE.md`:

| Feature | Walking Pattern | Detection Method |
|---------|----------------|------------------|
| **Vertical Acc (Z)** | **±1-2g periodic** | FFT peak at 1-2 Hz |
| Lateral Acc (X, Y) | < 0.5g sinusoidal | Smooth sway |
| Gyroscope | ±10-30°/s periodic | Low angular velocity |
| Roll | ±5-10° oscillation | Weight shift side-to-side |
| Pitch | ±5-10° oscillation | Forward/backward tilt |
| Yaw | Gradual change | Turning direction |
| **Upright Posture** | **angles near 0°** | Not lying/sitting/bent ⭐⭐⭐ |

**Key Insight**: Walking requires upright posture (distinguishes from crawling/lying) + periodic motion (distinguishes from standing)

---

## 4. Detection Algorithm

### Option 1: Threshold-Based (Recommended for MVP)

**Advantages**: Fast, interpretable, no training data required
**Expected Accuracy**: 70-80%

```javascript
function detectWalking(footData, accelData) {
    // Step 1: Check upright posture (required)
    const isUpright = (
        Math.abs(accelData.angle.roll) < 15 &&
        Math.abs(accelData.angle.pitch) < 15 &&
        accelData.acc.y > 0.7 && accelData.acc.y < 1.3
    );

    if (!isUpright) return { activity: null, confidence: 0 };

    // Step 2: Calculate pressure variance over window
    const variance = calculateVariance(footData.pressures);

    // Step 3: Estimate step frequency (FFT or zero-crossing)
    const stepFreq = estimateStepFrequency(footData.pressures);

    // Step 4: Check walking criteria
    if (variance > 80 && stepFreq >= 1.0 && stepFreq <= 2.0) {
        return { activity: 'Walking', confidence: 85 };
    } else if (variance > 50 && stepFreq >= 0.8 && stepFreq <= 2.2) {
        return { activity: 'Walking', confidence: 60 };
    }

    return { activity: null, confidence: 0 };
}
```

### Option 2: Sensor Fusion (Best Accuracy)

**Advantages**: 85-95% accuracy, robust to sensor noise
**Expected Accuracy**: 85-95%

```javascript
function detectWalkingFusion(footData, accelData, windowSize = 500) {
    // Extract features from both sensors
    const footFeatures = {
        variance: calculateVariance(footData.pressures),
        stepFreq: estimateStepFrequency(footData.pressures),
        avgPressure: footData.avg_pressure,
        asymmetry: Math.abs(footData.left - footData.right)
    };

    const accelFeatures = {
        isUpright: isUprightPosture(accelData),
        verticalOscillation: calculateOscillation(accelData.acc.z),
        gyroMagnitude: Math.sqrt(
            accelData.gyro.x**2 +
            accelData.gyro.y**2 +
            accelData.gyro.z**2
        )
    };

    // Score each feature
    let score = 0;

    // Foot pressure scoring (50% weight)
    if (footFeatures.stepFreq >= 1.0 && footFeatures.stepFreq <= 2.0) score += 25;
    if (footFeatures.variance > 80) score += 15;
    if (footFeatures.avgPressure >= 100 && footFeatures.avgPressure <= 250) score += 10;

    // Accelerometer scoring (50% weight)
    if (accelFeatures.isUpright) score += 20;
    if (accelFeatures.verticalOscillation > 0.5) score += 15;
    if (accelFeatures.gyroMagnitude >= 10 && accelFeatures.gyroMagnitude <= 50) score += 15;

    // Convert score to confidence
    const confidence = Math.min(score, 100);

    if (confidence >= 70) {
        return { activity: 'Walking', confidence };
    }

    return { activity: null, confidence: 0 };
}
```

---

## 5. Feature Engineering

### Critical Features (Importance Ranking)

1. **Step Frequency (1-2 Hz)** ⭐⭐⭐⭐⭐
   - Most distinctive feature
   - Can be calculated from both sensors
   - Methods: FFT, autocorrelation, zero-crossing rate

2. **Upright Posture** ⭐⭐⭐⭐⭐
   - Essential to distinguish from crawling/lying
   - `angle.roll` and `angle.pitch` near 0°
   - `acc.y` (vertical axis) ~ 1g

3. **Pressure Variance** ⭐⭐⭐⭐
   - Indicates dynamic vs static activity
   - Walking: 50-200, Standing: < 30

4. **Vertical Oscillation** ⭐⭐⭐
   - Periodic bounce in `acc.z` at step frequency
   - Amplitude: ±1-2g

5. **Left-Right Alternation** ⭐⭐
   - Complementary pattern in foot pressure
   - Requires time-series analysis (cross-correlation)

### Feature Calculation Methods

**Step Frequency Estimation:**
```javascript
function estimateStepFrequency(pressureWindow, samplingRate = 10) {
    // Method 1: Zero-crossing (fast, simple)
    const mean = pressureWindow.reduce((a, b) => a + b) / pressureWindow.length;
    let crossings = 0;
    for (let i = 1; i < pressureWindow.length; i++) {
        if ((pressureWindow[i-1] - mean) * (pressureWindow[i] - mean) < 0) {
            crossings++;
        }
    }
    const frequency = (crossings / 2) / (pressureWindow.length / samplingRate);
    return frequency;

    // Method 2: FFT (more accurate, slower)
    // const fft = calculateFFT(pressureWindow);
    // const peakFreq = findPeakFrequency(fft, 0.5, 3.0); // Search 0.5-3 Hz range
    // return peakFreq;
}
```

**Variance Calculation:**
```javascript
function calculateVariance(values) {
    const mean = values.reduce((a, b) => a + b) / values.length;
    const variance = values.reduce((sum, val) => sum + (val - mean) ** 2, 0) / values.length;
    return variance;
}
```

---

## 6. Distinguishing Walking from Similar Activities

### Walking vs. Standing

| Feature | Walking | Standing |
|---------|---------|----------|
| Variance | 50-200 | < 30 |
| Step Frequency | 1-2 Hz | N/A (no periodicity) |
| Gyroscope | ±10-30°/s periodic | < 10°/s random |

**Key**: Variance and periodicity are decisive

### Walking vs. Running

| Feature | Walking | Running |
|---------|---------|---------|
| Step Frequency | 1.0-2.0 Hz | 2.0-3.5 Hz |
| Max Pressure | 200-500 | 400-800 (higher impact) |
| Vertical Acc | ±1-2g | ±3-8g (higher jumps) |
| Flight Phase | None | Both feet off ground |

**Key**: Step frequency and impact force separate them

### Walking vs. Crawling

| Feature | Walking | Crawling |
|---------|---------|----------|
| Posture | Upright (angles ~0°) | Horizontal (pitch >70°) |
| Foot Pressure | High (8-18 sensors) | Very low (0-5 sensors) |
| Y-axis Acc | ~1g (vertical) | ~0g (horizontal) |

**Key**: Posture is decisive

---

## 7. Implementation Roadmap

### Phase 1: Basic Threshold Detection (Week 1) ✅

**Goal**: Detect walking with >70% accuracy using simple thresholds

**Tasks**:
- [ ] Add walking thresholds to `activityDetector.js`
- [ ] Implement variance calculation
- [ ] Implement step frequency estimation (zero-crossing method)
- [ ] Add upright posture check
- [ ] Test with simulated data

**Expected Outcome**: Walking detection works in ideal conditions

### Phase 2: Data Collection (Week 2) ⚠️

**Goal**: Collect real walking data from multiple users

**Tasks**:
- [ ] Record 10+ walking sessions (different speeds, terrains)
- [ ] Label ground truth activity manually
- [ ] Store in training dataset
- [ ] Analyze actual step frequencies and variance ranges

**Expected Outcome**: Validation of estimated thresholds

### Phase 3: Sensor Fusion (Week 3) 🎯

**Goal**: Achieve 85-95% accuracy with combined sensors

**Tasks**:
- [ ] Implement feature scoring system
- [ ] Tune weights for each feature based on collected data
- [ ] Add cross-sensor correlation (foot pressure + accel alignment)
- [ ] Test on validation set

**Expected Outcome**: Production-ready walking detection

### Phase 4: Edge Cases & Refinement (Week 4) 🔧

**Goal**: Handle challenging scenarios

**Tasks**:
- [ ] Test walking with heavy load (carrying equipment)
- [ ] Test walking on stairs/inclines
- [ ] Test slow walking vs standing transitions
- [ ] Implement hysteresis (require 1-2s of stable pattern before confirming)

**Expected Outcome**: Robust detection in real firefighter scenarios

---

## 8. Validation Metrics

### Test Scenarios

1. **Normal Walking**: Flat surface, moderate pace (1.5 Hz), no load
2. **Slow Walking**: Cautious pace (1.0 Hz), looking around
3. **Fast Walking**: Urgent pace (2.0 Hz), purposeful
4. **Walking with Load**: Carrying equipment (asymmetric pressure OK)
5. **Walking Upstairs**: Forward pitch increases, higher impact
6. **Walking Downstairs**: Backward pitch, controlled descent

### Success Criteria

| Metric | Target | Acceptable | Notes |
|--------|--------|------------|-------|
| **Precision** | >85% | >75% | % of detected walking that's actually walking |
| **Recall** | >90% | >80% | % of actual walking that's detected |
| **Latency** | <1s | <2s | Time to detect after walking starts |
| **False Positives** | <5% | <10% | Running/standing misclassified as walking |
| **Missed Detections** | <10% | <15% | Walking not detected |

### Confusion Matrix (Expected)

|  | Predicted: Walking | Predicted: Other |
|--|-------------------|-----------------|
| **Actual: Walking** | 90% (TP) | 10% (FN) |
| **Actual: Standing** | 3% (FP) | 97% (TN) |
| **Actual: Running** | 5% (FP) | 95% (TN) |

---

## 9. Known Challenges & Mitigations

### Challenge 1: Slow Walking vs. Standing

**Problem**: At very slow speeds (< 1 Hz), walking becomes hard to distinguish from standing with small movements.

**Mitigation**:
- Require sustained periodicity (>2 seconds of consistent pattern)
- Check for alternating left/right pressure (standing is symmetric)
- Use gyroscope oscillation as tiebreaker

### Challenge 2: Walking with Heavy Load

**Problem**: Asymmetric load (e.g., carrying hose on one side) breaks left-right balance assumption.

**Mitigation**:
- Relax asymmetry threshold (allow > 100 difference)
- Rely more on step frequency and upright posture
- Add "Carrying" sub-category if needed

### Challenge 3: Terrain Variations

**Problem**: Stairs, inclines, uneven ground change gait patterns.

**Mitigation**:
- Allow wider variance ranges (40-250 instead of 50-200)
- Use pitch angle to detect stairs (upward = positive pitch, downward = negative)
- Consider separate "Walking_Stairs" category if important

### Challenge 4: Sensor Noise & Dropouts

**Problem**: BLE connection issues can cause missing packets at ~10-20 Hz.

**Mitigation**:
- Interpolate missing values (linear interpolation over gaps < 200ms)
- Require minimum data completeness (>80% of expected samples in window)
- Use median instead of mean for variance calculation (robust to outliers)

---

## 10. Next Steps

### Immediate Actions

1. **Implement basic threshold detector** in `activityDetector.js` (add to existing detection logic)
2. **Collect validation data**: Record 5 walking sessions to validate thresholds
3. **Add walking to activity color map** in `record.html` (suggest color: `#06b6d4` cyan-500)

### Future Enhancements

- **Gait analysis**: Extract stride length, cadence, symmetry for health monitoring
- **Fatigue detection**: Detect gait irregularities (variance increases, frequency decreases)
- **Speed estimation**: Correlate step frequency with actual speed (requires calibration)
- **Terrain classification**: Distinguish flat/stairs/incline walking

---

## 11. References

- `foot_pressure_thresholds.json` (lines 30-44): Walking pressure thresholds
- `ACTIVITY_DETECTION_GUIDE.md` (lines 266-298): Walking estimation details
- `SENSOR_SPECIFICATIONS.md` (lines 113-312): Accelerometer walking patterns
- `DATA_DICTIONARY.md` (lines 244-296): Value ranges by activity

---

## Conclusion

**Walking detection is feasible and well-documented** with the current sensor suite. The key is combining:

1. **Step frequency detection** (1-2 Hz) - most distinctive feature
2. **Upright posture validation** - essential differentiator
3. **Pressure variance** - confirms dynamic movement

Start with **threshold-based detection** for quick MVP (70-80% accuracy), then progress to **sensor fusion** for production deployment (85-95% accuracy).

**Status**: Ready for implementation 🚀
