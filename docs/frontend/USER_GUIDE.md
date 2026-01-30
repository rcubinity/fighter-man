# Firefighter Activity Recognition Frontend - User Guide

This guide explains how to use the firefighter activity recognition frontend application for recording training sessions and reviewing recorded data.

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Recording a Session](#2-recording-a-session)
3. [Managing Sessions](#3-managing-sessions)
4. [Replaying a Session](#4-replaying-a-session)
5. [Understanding Sensor Displays](#5-understanding-sensor-displays)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Getting Started

### Prerequisites

Before using the application, ensure the following are in place:

**Server Running**

The firefighter-server must be running and accessible. By default, it runs on `http://localhost:4100`. You can verify the server is running by checking for a "Connected" status in the application header.

**Browser Requirements**

Use a modern web browser with support for:
- WebRTC (camera access)
- MediaRecorder API (video recording)
- WebSocket connections

Recommended browsers:
- Google Chrome (version 90 or later) - recommended
- Mozilla Firefox (version 88 or later)
- Safari (version 14.1 or later)

**Sensors (Optional)**

If you want to capture sensor data during recording:
- Foot pressure sensors should be paired and streaming via the sensor-hub
- Accelerometer should be connected and transmitting data
- The Raspberry Pi with sensor-hub should be running

### Opening the Application

1. Open your web browser
2. Navigate to the `record.html` file (typically served via the firefighter-server)
3. When prompted, grant camera permission to enable video recording
4. The application will automatically connect to the server

### Understanding the UI Layout

The application is divided into four main areas:

```
+------------------+--------------------------------+------------------+
|                  |                                |                  |
|   LEFT SIDEBAR   |         CENTER AREA            |  RIGHT SIDEBAR   |
|                  |                                |                  |
|  - New Session   |  - Video preview (recording)   |  - Foot Pressure |
|    Controls      |  - Status indicators           |    Display       |
|  - Past Sessions |  - Activity detection          |  - Accelerometer |
|    List          |  - Recording stats             |    Display       |
|                  |  - Video playback (replay)     |                  |
|                  |                                |                  |
+------------------+--------------------------------+------------------+
|                           TIMELINE                                   |
|  - Time ruler with markers                                           |
|  - Activity track with color-coded segments                          |
|  - Playhead indicator (during replay)                                |
+----------------------------------------------------------------------+
```

**Header Bar**
- Application title: "Stage 1: Training Sessions"
- Connection status indicator showing server connectivity

**Left Sidebar**
- Session name input field
- "Start Recording" / "Stop Recording" button
- List of past sessions with timestamps and status

**Center Area**
- Shows different content based on the current mode:
  - **Idle**: Ready to record message
  - **Recording**: Live camera feed with pose skeleton overlay, recording stats
  - **Replay**: Video playback (if available) and session information

**Right Sidebar**
- Real-time foot pressure visualization
- Accelerometer, gyroscope, and angle readings

**Timeline (Bottom)**
- Time ruler showing session duration
- Activity track displaying detected activities as color-coded segments
- Playhead showing current position during replay

---

## 2. Recording a Session

### Step-by-Step Recording Instructions

**Step 1: Prepare for Recording**

When you first open the application, you will see the "Ready to Record" screen in the center area. The connection status in the header should show "Connected" with a green indicator.

If the status shows "Disconnected" (gray indicator), the server may not be running. See the Troubleshooting section for help.

**Step 2: Enter a Session Name (Optional)**

In the left sidebar, you will find a text input field labeled "Session Name (optional)". You can:

- Enter a descriptive name (e.g., "ladder_climb_drill_001")
- Leave it empty to use an auto-generated name with a timestamp

Tip: Use descriptive names that include the activity type and date for easier identification later.

**Step 3: Start Recording**

Click the red "Start Recording" button in the left sidebar. Several things happen:

1. **Camera activates**: Your browser may ask for camera permission if this is your first time. Click "Allow" to proceed.

2. **Video container appears**: The center area switches to show a live camera preview. The video is mirrored for easier self-viewing.

3. **Pose detection starts**: The application uses ML5 MoveNet to detect body pose. You will see a skeleton overlay drawn on top of the video showing detected joints and connections.

4. **Session created**: A new recording session is created on the server and begins capturing sensor data.

**Step 4: Understand the Recording Indicators**

While recording, you will see:

- **"REC" indicator**: A red badge with "REC" text appears in the top-left corner of the video preview
- **Pulsing red circle**: A large animated red circle in the center area confirms recording is active
- **"Recording..." text**: Displays below the red circle
- **Duration timer**: Shows elapsed time in MM:SS format (e.g., "02:15")
- **Foot Readings counter**: Shows the number of foot pressure data points received (green text)
- **Accel Readings counter**: Shows the number of accelerometer data points received (orange text)

**Step 5: Monitor Activity Detection**

During recording, the system automatically detects activities based on sensor data:

- **Detected Activity**: Shows the current activity name (e.g., "Standing", "Sitting")
- **Confidence percentage**: Shows how certain the system is about the detection (e.g., "85%")
- **Activity icon**: For some activities, an SVG icon visualization appears

The activity label is color-coded by confidence:
- Green: High confidence (80-100%)
- Yellow: Medium confidence (60-79%)
- Orange: Low confidence (below 60%)

**Step 6: Stop Recording**

When you have finished the training activity:

1. Click the "Stop Recording" button (the button changes appearance when recording)

2. The following happens automatically:
   - Video recording stops
   - Pose detection stops
   - Session is marked as "stopped" on the server
   - Video upload begins

**Step 7: Wait for Video Upload**

After stopping, a progress bar appears showing the video upload status:

- **Progress bar**: Shows upload percentage from 0% to 100%
- **Status text**: Displays "Uploading video... X%" during upload
- **Completion message**: Shows "Upload complete!" when finished

Important: Do not close the browser or navigate away until the upload completes. Closing early will result in lost video data.

The upload progress bar disappears automatically after completion, and the session appears in the "Past Sessions" list.

### Creating a Session Without Activity Type

The current interface allows recording without specifying an activity type. Simply:

1. Optionally enter a session name
2. Click "Start Recording"
3. Perform your activities
4. Click "Stop Recording"

The activity detection system will attempt to identify activities automatically during recording and replay.

---

## 3. Managing Sessions

### Viewing Past Sessions in the Sidebar

All recorded sessions appear in the left sidebar under "PAST SESSIONS". Each session entry shows:

- **Session name**: The name you entered or an auto-generated name
- **Timestamp**: The time the session was created
- **Status badge**: Shows "recording" (red) or "stopped" (gray)
- **Rename button**: Pencil icon for renaming
- **Delete button**: Trash icon for deletion

Sessions are sorted with the most recent at the top.

### Renaming Sessions

To rename a session:

1. Find the session in the left sidebar
2. Click the pencil icon (shows as a small button to the right of the session name)
3. A prompt dialog appears with the current name
4. Enter the new name and click OK
5. The session name updates immediately

Tip: Use clear, descriptive names like "stair_climb_morning_drill" for easy identification.

### Deleting Sessions

To delete a session:

1. Find the session in the left sidebar
2. Click the trash icon (red button)
3. A confirmation dialog appears asking you to confirm deletion
4. Click OK to permanently delete the session

Warning: Deletion is permanent. All sensor data and video associated with the session will be removed and cannot be recovered.

If you delete a session that is currently being replayed, the application returns to the idle state.

### Session Status Indicators

Sessions can have two status values:

- **recording** (red badge): The session is currently being recorded. Only one session can be recording at a time.
- **stopped** (gray badge): The session has been completed and is available for replay.

---

## 4. Replaying a Session

### Selecting a Session for Replay

To replay a recorded session:

1. Make sure you are not currently recording (stop any active recording first)
2. Click on a session name in the left sidebar
3. The application switches to replay mode

When a session loads for replay:
- Session data is fetched from the server
- Video loads (if available)
- Timeline populates with activity segments
- Sensor data windows are prepared for playback

### Playback Controls

The replay interface provides three main controls located below the session information:

**Play/Pause Button (center)**
- Shows a play icon (triangle pointing right) when paused
- Shows a pause icon (two vertical bars) when playing
- Click to toggle between play and pause states

**Previous Button (left)**
- Shows a skip-back icon
- Jumps backward to the previous sensor data window (approximately 0.5 seconds)
- Useful for reviewing specific moments

**Next Button (right)**
- Shows a skip-forward icon
- Jumps forward to the next sensor data window
- Useful for quickly navigating through the session

### Understanding the Timeline

The timeline at the bottom of the screen provides a visual overview of the entire session:

**Time Ruler**
Located at the top of the timeline area, it displays time markers at 1-second intervals (00:01, 00:02, etc.). The ruler helps you identify the exact timing of events.

**Activity Track**
Located below the time ruler, this track shows detected activities as colored horizontal bars:

| Activity     | Color  |
|--------------|--------|
| Sitting      | Green  |
| Standing     | Blue   |
| Lying_Down   | Amber  |
| Bent_Forward | Violet |
| Jumping      | Red    |

Each bar represents a period where that activity was detected. Longer bars indicate the activity was sustained for a longer duration.

**Time Range Display**
In the timeline header, you can see the start and end times of the session (e.g., "00:01 - 02:30").

**Zoom Controls**
The timeline header includes zoom buttons (- and +) for adjusting the timeline view. Note: This feature may have limited functionality in the current version.

### Video and Sensor Data Synchronization

When replaying a session with video:

**Left Side: Video Player**
- The video appears on the left side of the center area
- Standard video controls are available (play, pause, seek, volume)
- The video automatically synchronizes with sensor data playback

**Right Side: Session Information**
- Blue circle indicator (distinguishes replay from recording)
- Session name display
- Current detected activity with confidence
- Time display showing current position and total duration
- Playback controls

**Synchronization Behavior**
The system keeps video and sensor data synchronized:
- Small drift (under 2 seconds) is allowed for smooth playback
- Large drift (over 2 seconds) triggers automatic correction
- The video position updates when using Previous/Next buttons

**Sessions Without Video**
If a session does not have video (upload failed or recorded before video feature):
- A gray placeholder appears with "No video available" message
- All other replay features work normally
- Sensor data and activity detection still display

### Activity Segment Visualization

During replay, the timeline shows when different activities were detected:

- Colored bars on the activity track correspond to activity labels
- Hovering over a segment shows a tooltip with the activity name and time range
- The segment width represents the duration of that activity
- Consecutive windows with the same activity are grouped into a single segment

The playhead (red vertical line) shows the current replay position and moves across the timeline during playback.

---

## 5. Understanding Sensor Displays

### Foot Pressure Visualization

Located in the right sidebar, the foot pressure display shows data from pressure-sensitive insoles.

**Layout**
Two side-by-side panels display left and right foot data:
- LEFT panel (blue bars)
- RIGHT panel (green bars)

**18 Bars Per Foot**
Each foot has 18 vertical bars representing individual pressure sensors. The bars are arranged in a row, with height indicating pressure level:
- Taller bars = higher pressure
- Shorter bars = lower pressure
- Bars dynamically update as new data arrives

**Statistics Below Each Foot**
- **Max**: The maximum pressure value currently detected
- **Avg**: The average pressure value across all 18 sensors

**Status Indicator**
Above the foot pressure section, a timestamp shows when the last data was received (e.g., "12:34:56 PM").

### Accelerometer Values Display

Located below the foot pressure section, the accelerometer display shows motion and orientation data.

**Acceleration (m/s squared)**
Three values showing linear acceleration:
- **X** (blue): Side-to-side movement
- **Y** (green): Forward-backward movement
- **Z** (orange): Up-down movement (includes gravity, approximately 9.8 when stationary)

**Gyroscope (degrees/s)**
Three values showing rotational velocity:
- **X** (blue): Rotation around the side-to-side axis
- **Y** (green): Rotation around the front-back axis
- **Z** (orange): Rotation around the vertical axis

**Angle (degrees)**
Three values showing orientation:
- **Roll** (purple): Tilt left or right
- **Pitch** (pink): Tilt forward or backward
- **Yaw** (cyan): Rotation around the vertical axis (compass heading)

All values display with two decimal places and update in real-time during recording or replay.

### Activity Detection Display

The activity detection display appears in the center area during both recording and replay.

**Components**
- **Activity Label**: The detected activity name (e.g., "Standing", "Sitting")
- **Confidence**: Percentage showing detection certainty
- **Activity Icon**: SVG visualization of the detected posture (available for some activities)

**Confidence Color Coding**
- Green text: High confidence (80% or above)
- Yellow text: Medium confidence (60-79%)
- Orange text: Low confidence (below 60%)

### Reading Counts During Recording

While recording, the center area displays real-time counters:

- **Foot Readings**: Number of foot pressure data points received (green number)
- **Accel Readings**: Number of accelerometer data points received (orange number)

These counters help verify that sensors are actively streaming data. If the numbers stop increasing, there may be a connection issue with the sensors.

---

## 6. Troubleshooting

### Camera Not Working

**Problem: Camera permission denied**

Solution:
1. Click the lock or site settings icon in your browser's address bar (usually to the left of the URL)
2. Find "Camera" in the permissions list
3. Change the setting to "Allow"
4. Refresh the page and try recording again

**Problem: No camera found or camera not detected**

Solution:
1. Check that your camera is physically connected (for external webcams)
2. Close other applications that might be using the camera (video conferencing apps, other browser tabs)
3. Try a different browser
4. Restart your computer if the issue persists

**Problem: Camera preview is black or frozen**

Solution:
1. Check if the camera LED is on (if applicable)
2. Refresh the browser page
3. For external webcams, try unplugging and reconnecting
4. Check your system's camera privacy settings

### Connection Issues

**Problem: Connection status shows "Disconnected"**

Solution:
1. Verify the firefighter-server is running on the expected port (default: 4100)
2. Check that no firewall is blocking the connection
3. Refresh the browser page
4. Check the browser console (press F12) for error messages

**Problem: Sensor data not appearing (counters stay at zero)**

Solution:
1. Verify the Raspberry Pi with sensor-hub is running
2. Check that sensors are paired via Bluetooth
3. Confirm the Socket.IO connection is established (check server logs)
4. Restart the sensor-hub service on the Raspberry Pi

**Problem: Activity detection shows "Waiting..."**

Solution:
1. Ensure both foot pressure AND accelerometer data are streaming
2. Try moving or changing posture to trigger detection
3. Check sensor battery levels
4. Verify sensors are properly paired and within range

### Video Upload Failures

**Problem: "Upload failed" error after stopping recording**

Solution:
1. Check your network connection to the server
2. Verify the server has available disk space
3. The video is kept in browser memory - try clicking "Stop Recording" again
4. Check server logs for specific error messages

**Problem: Upload progress stuck at a percentage**

Solution:
1. Wait longer - large video files take time to upload
2. Check that your network connection is stable
3. If truly stuck for several minutes, check server logs for errors
4. As a last resort, refresh the page (note: video will be lost)

**Problem: Video file too large**

Solution:
1. The default maximum file size is 500 MB
2. Keep recording sessions under 30 minutes for reasonable file sizes
3. Contact your system administrator to increase the upload limit if needed
4. Consider splitting long training sessions into shorter recordings

### Replay Not Loading

**Problem: Clicking a session does nothing**

Solution:
1. Make sure you are not currently recording (stop recording first)
2. Check the browser console for error messages
3. Verify the server is running and accessible
4. Try refreshing the page and selecting the session again

**Problem: Video not playing during replay**

Solution:
1. Check that your browser supports WebM video format
2. Verify the video file exists on the server
3. Check network connection for streaming issues
4. Try refreshing the page

**Problem: Timeline shows no activity segments**

Solution:
1. The session may not have activity labels saved
2. Activity detection may have failed during recording
3. Verify sensor data was actually recorded (check if session has windows)
4. Check server logs for labeling errors

**Problem: Video out of sync with sensor data**

Solution:
1. Small drift (under 2 seconds) is normal and will auto-correct
2. For large persistent drift, the session timestamps may be misaligned
3. Try pausing and resuming playback
4. Report persistent issues to the development team

### Browser Compatibility Issues

**Problem: "MediaRecorder not supported" error**

Solution:
1. Update your browser to the latest version
2. Use one of the recommended browsers: Chrome 90+, Firefox 88+, Safari 14.1+
3. Internet Explorer is not supported

**Problem: Pose detection not working (no skeleton overlay)**

Solution:
1. Ensure the ML5 library loaded successfully (check browser console)
2. Try a different browser
3. Check that JavaScript is enabled
4. Verify no browser extensions are blocking scripts

---

## Additional Notes

### Best Practices for Recording

1. **Check equipment before recording**: Test camera, verify sensor connections, confirm server connectivity
2. **Position camera appropriately**: Ensure full body is visible and lighting is adequate
3. **Use descriptive session names**: Include activity type and date for easy identification
4. **Monitor sensor counts**: Verify both foot and accelerometer readings increment during recording
5. **Keep sessions reasonable length**: Under 30 minutes recommended for manageable video sizes
6. **Wait for upload completion**: Do not close the browser until "Upload complete!" appears

### Understanding Activity Detection

The activity detection system recognizes the following activities:
- Standing
- Sitting
- Bent_Forward
- Lying_Down
- Jumping

Detection requires both foot pressure and accelerometer data. Low confidence readings may indicate:
- Transitional movements between activities
- Unusual postures not in the training data
- Sensor noise or missing data
- Activities not yet supported by the model

---

**Document Version:** 2.0
**Last Updated:** January 2026
