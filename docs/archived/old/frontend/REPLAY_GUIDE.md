# Replay Guide

This guide explains how to replay recorded training sessions with synchronized video and sensor data visualization.

## Table of Contents

1. [Loading a Session](#loading-a-session)
2. [Replay Interface](#replay-interface)
3. [Playback Controls](#playback-controls)
4. [Timeline Navigation](#timeline-navigation)
5. [Video Synchronization](#video-synchronization)
6. [Advanced Features](#advanced-features)

---

## Loading a Session

### Selecting a Session

1. **Open the application** (`record.html`)
2. **Find your session** in the left sidebar
   - Sessions are listed in chronological order (newest first)
   - Session name and timestamp are shown
3. **Click on the session name** to load it

### What Happens Next

When you select a session:
1. Application switches to replay mode
2. Session data loads from server
3. Video loads (if available)
4. Timeline builds with activity segments
5. Sensor data windows load
6. Ready to play!

---

## Replay Interface

### Two-Column Layout

The replay interface uses a side-by-side layout:

```
┌─────────────────────┬─────────────────────────┐
│                     │                         │
│   Video Player      │   🔵 Blue Circle        │
│   (640x480)         │   Replaying...          │
│                     │                         │
│   [Video plays here]│   Session: ladder_001   │
│                     │                         │
│                     │   Detected Activity:    │
│   OR                │      Standing (85%)     │
│                     │                         │
│   ▶️ Placeholder    │   Session Activity:     │
│   (No video)        │      Climbing           │
│                     │                         │
│                     │   00:15 / 02:30        │
│                     │                         │
│                     │   ⏮  ▶  ⏭             │
│                     │                         │
└─────────────────────┴─────────────────────────┘
              Timeline (bottom)
    ├──────────────────────────────────────┤
    00:00  00:30  01:00  01:30  02:00  02:30
```

### Left Side: Video Display

**With Video:**
- Video player with native browser controls
- Seekable timeline built into video player
- Play/pause via video controls or playback buttons

**Without Video:**
- Gray placeholder box
- Play icon (▶️)
- "Replay Mode" heading
- "No video available" message

### Right Side: Session Info

**Top Section:**
- Blue circle indicator (replay mode)
- "Replaying..." heading
- Session name

**Middle Section:**
- **Detected Activity:** Real-time activity from sensor data
  - Activity name (Standing, Sitting, etc.)
  - Confidence percentage
  - SVG icon visualization
- **Session Activity:** User-assigned activity type

**Bottom Section:**
- **Time Display:** Current time / Total duration
- **Playback Controls:** Previous, Play/Pause, Next buttons

---

## Playback Controls

### Play/Pause Button

**Play (▶):**
- Starts replay from current position
- Video plays (if available)
- Timeline playhead advances
- Sensor data updates in real-time
- Activity detection updates

**Pause (⏸):**
- Stops replay
- Video pauses
- Timeline playhead stops
- Sensor data freezes at current time

**Keyboard Shortcut:** Spacebar (toggles play/pause)

### Previous Button (⏮)

- Jumps to previous sensor data window
- Typically ~500ms intervals
- Updates video position accordingly

### Next Button (⏭)

- Jumps to next sensor data window
- Typically ~500ms intervals
- Updates video position accordingly

### Replay Speed

Currently, replay runs at 1x speed (real-time). Future versions may support 0.5x, 2x, etc.

---

## Timeline Navigation

### Timeline Overview

The timeline at the bottom visualizes the entire session:

```
├────┬────┬────┬────┬────┬────┬────┬────┬────┬────┤
00:00 0:30  1:00  1:30  2:00  2:30  3:00  3:30  4:00  4:30  5:00

[Green segment]  [Blue segment]  [Green segment]
   Sitting         Standing          Sitting
```

### Timeline Features

**1. Time Markers**
- Displayed every second (00:01, 00:02, ...)
- Helps identify exact timing of events

**2. Activity Segments**
- Color-coded rectangles showing detected activities
- Colors:
  - **Green:** Sitting
  - **Blue:** Standing
  - **Amber:** Lying_Down
  - **Violet:** Bent_Forward
  - **Red:** Jumping

**3. Red Playhead**
- Vertical red line shows current position
- Moves during playback
- Can be clicked/dragged to seek

### Seeking on Timeline

**Click to Seek:**
1. Click anywhere on the timeline
2. Playback jumps to that time
3. Video seeks to matching position
4. Sensor data updates for that moment

**Drag Playhead:**
1. Click and hold the red playhead
2. Drag left or right
3. Release to jump to new position

---

## Video Synchronization

### How Synchronization Works

The system keeps video and sensor data synchronized using timestamps:

```
Session Start: 2025-12-24 10:30:00.000 (t=0)
Sensor Data:   2025-12-24 10:30:15.500 (t=15.5s)
Video Time:    15.5 seconds

Formula: videoTime = (sensorTimestamp - sessionStartTime) / 1000
```

### Automatic Drift Correction

The system automatically corrects video drift:

- **Small drift (<2s):** Allowed to drift naturally
- **Large drift (>2s):** Auto-corrects to stay synchronized
- **Correction is smooth:** Minimal disruption to playback

### Manual Video Control

You can also control the video directly:

- Click on video timeline to seek
- Use video player controls (play/pause)
- Adjust volume (if video has audio)

**Note:** Manual video seeking will be corrected if it drifts >2s from sensor timeline.

---

## Advanced Features

### Activity Segment Visualization

Each activity on the timeline is clickable:

1. **Click an activity segment**
2. Playback jumps to the start of that activity
3. Video and sensors sync to that moment

**Use Case:** Quickly review all "Climbing" segments without watching entire session.

### Sensor Data Display

During replay, sensor data displays show:

**Foot Pressure:**
- Visual representation of 18 sensors per foot
- Color intensity = pressure level
- Updates in real-time during playback

**Accelerometer:**
- X, Y, Z acceleration values
- Gyroscope (rotation) values
- Angle (roll, pitch, yaw) values

### Activity Confidence

The confidence percentage shows how certain the detector is:

- **80-100%:** High confidence (green)
- **60-79%:** Medium confidence (yellow)
- **0-59%:** Low confidence (orange)

Low confidence may indicate:
- Transitional movement between activities
- Unusual activity not in training data
- Sensor noise or missing data

---

## Sessions Without Video

If a session doesn't have video (recorded before video feature, or upload failed):

**What You See:**
- Left side: Gray placeholder with "No video available"
- Right side: Normal session info and controls
- Timeline: Full activity visualization

**What Works:**
- All playback controls
- Timeline navigation
- Activity detection display
- Sensor data visualization

**What's Missing:**
- Visual confirmation of what firefighter was doing
- Cannot see equipment or environment

**Solution:** Re-record session with video enabled if visual context is needed.

---

## Tips and Tricks

### Quickly Review Activities

1. Look at timeline to see activity distribution
2. Click on an activity segment to jump to it
3. Use Next (⏭) to step through similar activities

### Compare Similar Sessions

1. Open Session A, note activity pattern
2. Open Session B, compare timeline
3. Look for differences in activity timing/duration

### Verify Sensor Accuracy

1. Play session with video
2. Watch video while monitoring detected activity
3. Check if detected activity matches visual observation
4. Report mismatches for model improvement

### Export for Analysis

Currently, replay is view-only. To export data:

1. Use backend API: `GET /api/sessions/:id/export?format=json`
2. Download sensor data + video for offline analysis
3. Import into analysis tools (Python, MATLAB, Excel)

---

## Troubleshooting

### Video Not Playing

**Problem:** Video element shows but doesn't play

**Solutions:**
- Check browser supports WebM format
- Check network connection for streaming
- Try refreshing the page
- Check browser console (F12) for errors

### Video Out of Sync

**Problem:** Video is ahead/behind sensor data by several seconds

**Solutions:**
- Small drift (<2s) is normal and auto-corrects
- Large persistent drift may indicate timestamp issue
- Check session.created_at matches video recording start
- Report to developer if issue persists

### Timeline Not Showing Activities

**Problem:** Timeline shows time markers but no activity segments

**Solutions:**
- Session may not have activity labels yet
- Activity detection may have failed during recording
- Check if sensor data was actually recorded
- Verify session has sensor windows in database

### Playback Stuttering

**Problem:** Replay is jerky or laggy

**Solutions:**
- Close other browser tabs to free memory
- Check network connection (video streaming may be slow)
- Try different browser (Chrome performs best)
- Reduce browser window size for better performance

---

For more troubleshooting, see [Troubleshooting Guide](TROUBLESHOOTING.md)

---

**Document Version:** 1.0
**Last Updated:** December 24, 2025
