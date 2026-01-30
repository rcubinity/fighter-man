# Recording Guide

This guide explains how to record firefighter training sessions with synchronized video and sensor data.

## Table of Contents

1. [Before You Start](#before-you-start)
2. [Recording a Session](#recording-a-session)
3. [Understanding the UI](#understanding-the-ui)
4. [Session Management](#session-management)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Before You Start

### Prerequisites

Before recording, ensure the following are ready:

**1. Server Running**
```bash
# Check server health
curl http://localhost:4100/health

# Should return: {"status": "ok", ...}
```

**2. Camera Connected**
- Webcam or integrated camera should be functional
- Close any other applications using the camera (Zoom, Teams, etc.)

**3. Sensors Paired and Streaming**
- Raspberry Pi with sensor-hub running
- Sensors paired via Bluetooth (foot pressure + accelerometer)
- Socket.IO connection active (check server logs)

### Opening the Application

1. Navigate to the frontend directory
2. Open `record.html` in your web browser:
   - **Chrome** (recommended)
   - **Firefox**
   - **Safari 14.1+**

3. Grant camera permission when prompted (you'll see a browser permission dialog)

---

## Recording a Session

Follow these steps to record a training session:

### Step 1: Start the Server

Ensure the firefighter-server is running:

```bash
cd firefighter-server
python server.py

# Server should output:
# * Running on http://0.0.0.0:4100
# * Socket.IO initialized
```

### Step 2: Open the Recording Interface

Open `frontend/record.html` in your browser. You should see:

- **Left sidebar:** Session list (previous sessions)
- **Center:** Idle state with "Start Recording" button
- **Top-right:** Connection status (should show "Connected" in green)

### Step 3: Grant Camera Permission

When you first open the application, your browser will ask for camera permission:

1. Click **"Allow"** when prompted
2. The video preview will appear once permission is granted
3. If you decline, you can still record sensor-only sessions (no video)

### Step 4: Start Recording

1. **(Optional)** Enter a session name in the input field
   - Default name: "recording" with timestamp
   - Example: "ladder_climb_drill_001"

2. Click the **"Start Recording"** button

3. You'll see:
   - **Red "REC" indicator** in top-left of video preview
   - **Pulsing red circle** on the right side
   - **Timer** starts counting (00:00, 00:01, ...)
   - **Sensor data** displays update in real-time
   - **Activity detection** shows detected activity with confidence

### Step 5: Perform Training Activities

Perform your training drill while recording:

- **Video camera** records the firefighter
- **Foot pressure sensors** capture weight distribution
- **Accelerometer** measures body orientation and movement
- **Activity detector** identifies activities in real-time

The system will automatically detect activities like:
- Standing
- Sitting
- Bent_Forward
- Lying_Down
- Jumping

### Step 6: Stop Recording

When the training session is complete:

1. Click the **"Stop Recording"** button

2. The following happens automatically:
   - Video recording stops
   - Video file is created from recorded chunks
   - Video uploads to server (progress bar shown)
   - Session is marked as "stopped" in database

3. Wait for upload to complete:
   - Progress bar shows upload percentage
   - "Upload complete!" message appears when done
   - Session moves to "Completed" section in sidebar

**⚠️ Important:** Do NOT close the browser during upload or you'll lose the video!

---

## Understanding the UI

### Recording View Layout

```
┌─────────────────────────────────────────────────┐
│                 Navbar (Top)                     │
│  Connected ✓                          12:34 PM   │
├────────────┬────────────────────────────────────┤
│            │                                     │
│  Session   │         Video Preview               │
│   List     │       ┌─────────────┐               │
│            │       │  🔴 REC     │               │
│  - Session │       │             │               │
│    001     │       │   Camera    │               │
│  - Session │       │    View     │               │
│    002     │       │             │               │
│            │       └─────────────┘               │
│            │                                     │
│            │     🔴 Recording...                 │
│            │                                     │
│            │     Detected Activity:              │
│            │        Standing (85%)               │
│            │                                     │
│            │     00:15    12    29              │
│            │   Duration  Foot  Accel           │
│            │                                     │
└────────────┴────────────────────────────────────┘
```

### UI Elements Explained

**1. Video Preview (Left Side)**
- Live camera feed (mirrored for easier viewing)
- Red "REC" badge when recording
- Shows what will be saved in the video file

**2. Recording Indicator (Right Side)**
- Large red pulsing circle (indicates active recording)
- "Recording..." text

**3. Session Name**
- Displays the current session name
- Can be changed later via rename

**4. Detected Activity**
- Real-time activity recognition
- Shows activity name (e.g., "Standing")
- Shows confidence percentage (0-100%)
- Updates as activities change

**5. Session Stats**
- **Duration:** Elapsed time (MM:SS format)
- **Foot Readings:** Number of foot pressure data points received
- **Accel Readings:** Number of accelerometer data points received

**6. Upload Progress (when stopping)**
- Progress bar (0-100%)
- "Uploading video... X%" status text
- "Upload complete!" when finished

---

## Session Management

### Viewing Sessions

All recorded sessions appear in the left sidebar:

- **Active Session:** Currently recording (shown in recording state)
- **Completed Sessions:** Previously recorded sessions (can be replayed)

Sessions are sorted by creation time (newest first).

### Renaming Sessions

To rename a session:

1. Hover over the session name in the sidebar
2. Click the **pencil icon** (✏️) that appears
3. Enter the new name
4. Press **Enter** or click outside to save
5. Session name updates immediately

**Example:** "recording_2025-12-24" → "ladder_climb_drill_001"

### Deleting Sessions

To delete a session:

1. Hover over the session name in the sidebar
2. Click the **trash icon** (🗑️) that appears
3. Confirm deletion in the popup dialog
4. Session and all associated data (sensor data + video) are permanently deleted

**⚠️ Warning:** Deletion cannot be undone!

### Replaying Sessions

To replay a recorded session:

1. Click on the session name in the left sidebar
2. The application switches to replay mode
3. Video (if available) appears on the left
4. Timeline visualization appears at the bottom
5. Use playback controls to navigate the session

See [Replay Guide](REPLAY_GUIDE.md) for detailed replay instructions.

---

## Best Practices

### Before Recording

1. **Check Equipment:**
   - Test camera is working (preview should show when page loads)
   - Verify sensors are paired and transmitting
   - Confirm Socket.IO connection (green "Connected" status)

2. **Frame the Shot:**
   - Position camera to capture full body movement
   - Ensure adequate lighting
   - Avoid backlight (bright window behind subject)

3. **Name Your Session:**
   - Use descriptive names: "ladder_climb_drill_001"
   - Include date for easy identification: "stair_climb_2025-12-24"
   - Avoid special characters: use letters, numbers, underscores, hyphens

### During Recording

1. **Monitor Activity Detection:**
   - Ensure activities are being detected correctly
   - If showing "Waiting...", check sensor connections

2. **Watch for Sensor Data:**
   - Foot Readings and Accel Readings counters should increment
   - If counters stop, sensor data may have disconnected

3. **Recording Duration:**
   - Keep sessions under 30 minutes to avoid large video files
   - Longer sessions create larger files (slower upload)

### After Recording

1. **Wait for Upload:**
   - Don't close browser until "Upload complete!" appears
   - Check progress bar reaches 100%

2. **Verify Session:**
   - Session should appear in left sidebar
   - Click to replay and verify video/sensors recorded correctly

3. **Review Captured Data:**
   - Check timeline shows activity segments
   - Verify video is synchronized with sensor data

---

## Troubleshooting

### Camera Issues

**Problem:** "Camera permission denied"
- **Solution:** Click the lock icon (🔒) in browser address bar
- Grant camera permission
- Refresh the page

**Problem:** "No camera found"
- **Solution:**
  - Check camera is connected (physically plugged in for external webcams)
  - Close other applications using the camera (Zoom, Teams, Skype, etc.)
  - Try a different browser
  - Restart your computer if issue persists

**Problem:** Camera preview frozen or black
- **Solution:**
  - Check camera LED is on (if applicable)
  - Refresh the browser page
  - Try unplugging and reconnecting the camera

### Sensor Data Issues

**Problem:** "No sensor data appearing"
- **Solution:**
  - Check Raspberry Pi is running sensor-hub
  - Verify Socket.IO connection (should show "Connected" in top-right)
  - Check server logs for sensor data events
  - Restart sensor-hub on Raspberry Pi

**Problem:** Activity detection shows "Waiting..."
- **Solution:**
  - Ensure both foot pressure AND accelerometer data are streaming
  - Try moving to trigger detection (standing still may not register)
  - Check sensor battery levels
  - Verify sensors are properly paired via Bluetooth

### Upload Issues

**Problem:** "Upload failed" error
- **Solution:**
  - Check network connection to server
  - Verify server has disk space available
  - Try uploading again (video is kept in browser memory)
  - Check video size (<500 MB limit)

**Problem:** Upload progress stuck at X%
- **Solution:**
  - Wait a bit longer (large files take time)
  - Check network connection is stable
  - Check server logs for errors
  - If truly stuck, refresh page (video will be lost - record again)

**Problem:** "Video file too large"
- **Solution:**
  - Recording exceeded 500 MB limit (roughly 30+ minutes at HD quality)
  - Split training into shorter sessions
  - Contact admin to increase server upload limit

### Browser Compatibility

**Problem:** "MediaRecorder not supported"
- **Solution:**
  - Update browser to latest version
  - Use Chrome 90+, Firefox 88+, or Safari 14.1+
  - Avoid Internet Explorer (not supported)

---

For more troubleshooting, see [Troubleshooting Guide](TROUBLESHOOTING.md)

---

**Document Version:** 1.0
**Last Updated:** December 24, 2025
