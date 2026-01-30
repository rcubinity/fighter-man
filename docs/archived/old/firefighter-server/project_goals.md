# Project Goals - What We're Solving

## Overview

This project aims to improve firefighter safety and performance through AI-powered activity recognition using wearable sensors.

---

## The Problems We're Solving

### 1. Safety Monitoring (Save Lives)

**Problem:** Firefighter goes down (injured/unconscious) → No one knows

**Solution with AI:**

```
AI detects: "Firefighter was moving... now IDLE for 2 minutes"
         |
         v
Alert: "Firefighter #3 may be down!"
         |
         v
Command center sends rescue team immediately
```

**Impact:** Faster rescue = Lives saved

---

### 2. Training Feedback (Improve Skills)

**Problem:** Instructor can't watch every trainee simultaneously

**Solution with AI:**

```
After drill, AI report shows:

Trainee A:
|-- Walking:     40% of time
|-- Crawling:    30% of time  [Good technique]
|-- Idle:        5% of time

Trainee B:
|-- Walking:     60% of time
|-- Crawling:    10% of time  [Needs more practice]
|-- Idle:        20% of time  [Too much rest]
```

**Impact:** Targeted training → Better firefighters

---

### 3. Fatigue Detection (Prevent Accidents)

**Problem:** Tired firefighters make mistakes → Injuries

**Solution with AI:**

```
AI monitors movement patterns over time:

Start of shift:  Sharp, quick movements
After 2 hours:   Slower, weaker patterns
         |
         v
Alert: "Firefighter showing fatigue signs"
         |
         v
Commander: "Take a break, rotate teams"
```

**Impact:** Prevent exhaustion-related accidents

---

### 4. Performance Analytics (Better Teams)

**Problem:** No data on how firefighters actually move during emergencies

**Solution with AI:**

```
Analyze 100 training sessions:

"Top performers spend:
 - 25% climbing
 - 30% crawling
 - Less than 5% idle"

"Struggling teams spend:
 - 40% walking (inefficient)
 - 20% idle (hesitation)"
```

**Impact:** Data-driven training programs

---

### 5. Incident Reconstruction (Learn & Improve)

**Problem:** After an incident, hard to know what happened

**Solution with AI:**

```
Timeline reconstruction:

10:00 - Team entered building
10:05 - Firefighter #2 started climbing
10:08 - Firefighter #2 fell (sudden movement change)
10:09 - Team stopped, rescue began
```

**Impact:** Learn from incidents → Prevent future ones

---

## Summary Table

| Problem          | AI Solution             | Benefit            |
| ---------------- | ----------------------- | ------------------ |
| Firefighter down | Motion stop detection   | Faster rescue      |
| Training quality | Activity breakdown      | Better skills      |
| Fatigue          | Pattern degradation     | Prevent accidents  |
| Team performance | Data analytics          | Efficient training |
| Incidents        | Timeline reconstruction | Learn & improve    |

---

## The Big Picture

```
TODAY (Training Phase)
|-- Collect sensor data during drills
|-- Label activities manually
|-- Train AI model

TOMORROW (Deployment Phase)
|-- Firefighters wear sensors on real calls
|-- AI monitors in real-time
|-- Command center gets live insights
|-- SAFER FIREFIGHTERS
```

---

## Success Metrics

| Metric                            | Target                 |
| --------------------------------- | ---------------------- |
| Activity recognition accuracy     | >90%                   |
| "Firefighter down" detection time | <30 seconds            |
| False alarm rate                  | <5%                    |
| Training data collected           | 1000+ labeled sessions |

---

## Who Benefits?

| Stakeholder              | Benefit                              |
| ------------------------ | ------------------------------------ |
| **Firefighters**         | Safer on the job, better training    |
| **Commanders**           | Real-time team awareness             |
| **Training Instructors** | Data-driven feedback                 |
| **Fire Departments**     | Reduced injuries, better performance |
| **Families**             | Their firefighters come home safe    |

---

**Document Version:** 1.0
**Last Updated:** December 2, 2025
