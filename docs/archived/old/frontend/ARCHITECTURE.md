# Frontend Architecture

This document explains how the frontend components work together to create a unified recording and replay experience.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Breakdown](#component-breakdown)
3. [Data Flow](#data-flow)
4. [State Management](#state-management)
5. [Communication Protocols](#communication-protocols)

---

## System Overview

The frontend consists of a single-page application (`record.html`) that handles both recording and replay modes, coordinating between camera input, sensor data streams, and activity detection.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Browser)                        │
│                                                               │
│  ┌────────────────┐      ┌──────────────────┐               │
│  │   Camera API   │      │   Socket.IO      │               │
│  │  (MediaDevices)│      │     Client       │               │
│  └───────┬────────┘      └────────┬─────────┘               │
│          │                        │                          │
│          │  Video Stream          │  Sensor Data Stream      │
│          ▼                        ▼                          │
│  ┌──────────────────────────────────────────────┐           │
│  │          record.html (Main UI)                │           │
│  │  ┌───────────────┐     ┌────────────────┐   │           │
│  │  │ videoRecorder │     │  activityDet   │   │           │
│  │  │     .js       │     │   ector.js     │   │           │
│  │  └───────┬───────┘     └────────┬───────┘   │           │
│  │          │  Upload              │ Detect     │           │
│  │          │  Video               │ Activity   │           │
│  │          ▼                      ▼            │           │
│  │  ┌──────────────────────────────────────┐   │           │
│  │  │         Session Manager               │   │           │
│  │  │  (UI State, Timeline, Playback)       │   │           │
│  │  └────────┬─────────────────────────────┘   │           │
│  └───────────┼──────────────────────────────────┘           │
│              │ REST API                                      │
└──────────────┼───────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│         Firefighter Server (Flask + Socket.IO)               │
│  - Video upload/download endpoints                           │
│  - Sensor data streaming (Socket.IO /iot namespace)          │
│  - Session management (CRUD operations)                      │
│  - PostgreSQL (session metadata + video paths)               │
│  - Qdrant (sensor vector storage)                            │
│  - File System (video file storage)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. record.html (Main UI)

**Purpose:** Single-page application that orchestrates all functionality

**Responsibilities:**
- UI state management (idle, recording, replaying)
- Session list rendering and selection
- Timeline visualization with activity segments
- Real-time sensor data visualization (foot pressure, accelerometer)
- Playback controls and seek functionality

**Key Variables:**
```javascript
let currentSessionId = null;        // Active recording session ID
let activeState = 'idle';            // Current UI state
let videoRecorder = null;            // VideoRecorder instance
let replayTimer = null;              // Replay playback timer
let replayStartTime = null;          // Replay start timestamp
```

**States:**
- **idle**: No recording or replay active
- **recording**: Camera and sensors actively recording
- **stopped**: Recording finished, awaiting upload
- **uploading**: Video uploading to server
- **replaying**: Playing back a recorded session

### 2. videoRecorder.js

**Purpose:** Browser-based video recording using MediaRecorder API

**Class:** `VideoRecorder`

**Methods:**
```javascript
async init(previewElementId)          // Request camera access
async startRecording(sessionId)       // Begin video capture
async stopRecording()                 // Stop and create video blob
async uploadVideo(sessionId, blob)    // Upload via HTTP POST
async uploadVideoWithProgress(...)    // Upload with progress tracking
destroy()                             // Clean up resources
static isSupported()                  // Check browser compatibility
```

**State Flow:**
```
idle → recording → stopped → uploading → idle
```

**Configuration:**
- Resolution: 1280x720 (HD)
- Frame Rate: 30 FPS
- Bitrate: 2.5 Mbps
- Format: WebM (VP9 codec, VP8 fallback)

### 3. activityDetector.js

**Purpose:** Real-time activity recognition from sensor data

**Function:** `detectActivity(footData, accelData)`

**Inputs:**
- `footData`: Array of 36 foot pressure values (18 per foot)
- `accelData`: Object with acc, gyro, angle (9 values total)

**Outputs:**
```javascript
{
  activity: "Standing",    // Detected activity name
  confidence: 85           // Confidence percentage (0-100)
}
```

**Detected Activities:**
- Standing
- Sitting
- Bent_Forward
- Lying_Down
- Jumping

**Detection Logic:**
1. Calculate features (variance, averages, angles)
2. Apply rule-based classification
3. Return activity + confidence score

---

## Data Flow

### Recording Flow

```
1. User clicks "Start Recording"
   ↓
2. Create session on server (POST /api/sessions)
   ↓
3. Initialize video recorder → Request camera access
   ↓
4. Start video recording (MediaRecorder.start())
   ↓
5. Sensor data streams via Socket.IO
   ├─> foot_data event → Display pressure visualization
   └─> accel_data event → Display accelerometer values
   ↓
6. Activity detector processes incoming sensor data
   ↓
7. User clicks "Stop Recording"
   ↓
8. Stop video recording → Create video blob
   ↓
9. Stop session on server (POST /api/sessions/:id/stop)
   ↓
10. Upload video blob (POST /api/sessions/:id/upload-video)
    ↓
11. Server saves video file and updates session record
    ↓
12. Return to idle state
```

### Replay Flow

```
1. User selects session from list
   ↓
2. Fetch replay data (GET /api/sessions/:id/replay)
   ├─> Session metadata (name, timestamps)
   ├─> Sensor windows (time-ordered data)
   └─> Video path (if available)
   ↓
3. If video exists:
   ├─> Load video (GET /api/sessions/:id/video)
   └─> Show video player on left
   Else:
   └─> Show placeholder ("No video available")
   ↓
4. Build timeline with activity segments
   ↓
5. User clicks "Play"
   ↓
6. Start replay timer (updates every 100ms)
   ├─> Update playhead position on timeline
   ├─> Display corresponding sensor data
   ├─> Show detected activity for current time
   └─> Sync video playback (if available)
   ↓
7. User seeks on timeline
   ↓
8. Update video.currentTime to match sensor timestamp
   ↓
9. User clicks "Pause" or replay completes
   ↓
10. Stop replay timer, pause video
```

---

## State Management

### UI States

The application manages state through simple JavaScript variables and CSS classes:

```javascript
// State variables
let activeState = 'idle';            // Current mode
let currentSessionId = null;         // Active session
let videoRecorder = null;            // Video recording instance
let isReplaying = false;             // Replay active flag

// State transitions
function setState(newState) {
    activeState = newState;

    // Show/hide state-specific UI
    document.getElementById('idleState').classList.toggle('hidden', newState !== 'idle');
    document.getElementById('recordingState').classList.toggle('hidden', newState !== 'recording');
    document.getElementById('replayState').classList.toggle('hidden', newState !== 'replaying');
}
```

### Video Recorder States

```javascript
// VideoRecorder internal states
this.state = 'idle';  // idle, recording, stopped, uploading

// Allowed transitions:
// idle → recording (when startRecording called)
// recording → stopped (when stopRecording called)
// stopped → uploading (when uploadVideo called)
// uploading → idle (when upload completes)
```

### Session States (Server-side)

```javascript
// Session status field (PostgreSQL)
status: "recording"  // recording, stopped, completed
```

---

## Communication Protocols

### REST API (HTTP)

**Used for:**
- Session CRUD operations
- Video upload/download
- Fetching replay data

**Base URL:** `http://localhost:4100`

**Key Endpoints:**
- `POST /api/sessions` - Create session
- `GET /api/sessions` - List all sessions
- `GET /api/sessions/:id` - Get session details
- `PUT /api/sessions/:id` - Update session (rename)
- `DELETE /api/sessions/:id` - Delete session
- `POST /api/sessions/:id/stop` - Stop recording
- `POST /api/sessions/:id/upload-video` - Upload video file
- `GET /api/sessions/:id/video` - Stream video (supports Range requests)
- `GET /api/sessions/:id/replay` - Get replay data

### Socket.IO (WebSocket)

**Used for:**
- Real-time sensor data streaming
- Session status updates

**Namespace:** `/iot`

**Events (Server → Client):**
```javascript
socket.on('connect', () => {
    // Connection established
});

socket.on('foot_data', (data) => {
    // { data: { foot: 'L', values: [18 pressure values], max, avg } }
    updateFootVisualization(data);
});

socket.on('accel_data', (data) => {
    // { data: { acc: {x, y, z}, gyro: {x, y, z}, angle: {roll, pitch, yaw} } }
    updateAccelDisplay(data);

    // Run activity detection
    const activity = detectActivity(currentFootData, data.data);
    displayActivity(activity);
});

socket.on('session_started', (data) => {
    // { session_id, name }
    console.log('Recording started:', data.session_id);
});

socket.on('session_stopped', (data) => {
    // { session_id }
    console.log('Recording stopped:', data.session_id);
});
```

---

## Performance Considerations

### Video Recording

- **Memory Usage:** Video chunks accumulate in browser memory during recording
  - Solution: Chunks released when recording stops
  - Consideration: Very long recordings (>30 min) may use significant RAM

- **Upload Time:** Depends on video size and network speed
  - Typical: 2-5 MB/min of recording at 2.5 Mbps
  - 10-minute session ≈ 25 MB ≈ 5-10 seconds upload on good connection

### Sensor Data Streaming

- **Update Frequency:**
  - Foot pressure: 10-20 Hz (every 50-100ms)
  - Accelerometer: 20-100 Hz (every 10-50ms)

- **Rendering Optimization:**
  - Activity detection runs only when both foot and accel data available
  - UI updates throttled to avoid excessive redraws
  - Timeline uses pre-calculated activity segments (not recalculated on every frame)

### Timeline Rendering

- **Large Sessions:** Sessions with thousands of sensor windows (>30 min) render efficiently
  - SVG-based timeline with activity segment rectangles
  - Playhead updates every 100ms (smooth enough for visual sync)
  - Video sync only corrects drift >2 seconds (avoids excessive seeking)

---

## Browser Compatibility Notes

### MediaRecorder API

- **Chrome/Edge:** Excellent VP9 support
- **Firefox:** VP8 codec (slightly lower quality than VP9)
- **Safari:** Limited WebM support (may need H.264 fallback in future)

### Socket.IO

- Universally supported (uses WebSocket when available, falls back to polling)

### ES6 Features

- Arrow functions, async/await, template literals
- Requires modern browser (IE11 not supported)

---

**Document Version:** 1.0
**Last Updated:** December 24, 2025
