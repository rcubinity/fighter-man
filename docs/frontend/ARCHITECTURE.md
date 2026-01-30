# Frontend Architecture

This document describes the internal architecture of the frontend component, including module organization, state management, and data flow.

## Code Organization

The frontend was recently refactored from inline JavaScript in `record.html` into modular ES6 files for better maintainability.

### Module Loading Order

Scripts are loaded in a specific order in `record.html` due to dependencies:

```html
<!-- External libraries (no dependencies) -->
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/p5.min.js"></script>
<script src="https://unpkg.com/ml5@1/dist/ml5.min.js"></script>

<!-- Standalone modules (no dependencies on our code) -->
<script src="js/activityDetector.js"></script>
<script src="js/videoRecorder.js"></script>
<script src="js/poseSketch.js"></script>

<!-- Core modules (order matters) -->
<script src="js/config.js"></script>        <!-- No dependencies -->
<script src="js/state.js"></script>          <!-- Uses CONFIG -->
<script src="js/dom.js"></script>            <!-- No dependencies -->
<script src="js/utils.js"></script>          <!-- No dependencies -->
<script src="js/sensorDisplay.js"></script>  <!-- Uses state vars -->
<script src="js/activityDisplay.js"></script> <!-- Uses state vars -->
<script src="js/socketManager.js"></script>  <!-- Uses CONFIG, state, display -->
<script src="js/recordingManager.js"></script> <!-- Uses everything -->
<script src="js/sessionManager.js"></script>   <!-- Uses everything -->
<script src="js/replayManager.js"></script>    <!-- Uses everything -->
<script src="js/timelineRenderer.js"></script> <!-- Uses state vars -->
<script src="js/app.js"></script>              <!-- Entry point -->
```

## Module Responsibilities

### Core Infrastructure

#### `config.js`
Configuration constants. Single source of truth for settings.

```javascript
const CONFIG = {
    SERVER_URL: 'http://localhost:4100',
    REPLAY_BATCH_SIZE: 20,
    // ... other settings
};
```

#### `state.js`
Centralized mutable state. All modules read/write to these global variables.

```javascript
// Recording state
let isRecording = false;
let currentSessionId = null;
let recordingStartTime = null;

// Replay state
let replayWindows = [];
let replayCurrentWindowIndex = 0;
let isReplaying = false;

// Managers
let activityDetector = null;
let videoRecorder = null;
let poseSketch = null;
```

#### `dom.js`
DOM element references (currently minimal, stores element selectors).

#### `utils.js`
Utility functions like `formatTime()` and `throttle()`.

### Communication

#### `socketManager.js`
Handles Socket.IO connection and event routing.

```javascript
function connectSocket() {
    const iotSocket = io(`${SERVER_URL}/iot`, {
        transports: ['websocket', 'polling'],
        reconnection: true,
    });

    // Connection events
    iotSocket.on('connect', () => updateConnectionStatus(true));
    iotSocket.on('disconnect', () => updateConnectionStatus(false));

    // Sensor data events -> display updates
    iotSocket.on('foot_data', (data) => {
        updateFootDisplay(data);
        if (activityDetector && isRecording) {
            activityDetector.updateFootData(data.data);
        }
    });

    iotSocket.on('accel_data', (data) => {
        updateAccelDisplay(data);
        if (activityDetector && isRecording) {
            activityDetector.updateAccelData(data.data);
            const result = activityDetector.detectActivity();
            updateActivityDisplay(result.activity, result.confidence);
        }
    });
}
```

### Display Modules

#### `sensorDisplay.js`
Updates foot pressure bars and accelerometer values.

```javascript
function updateFootDisplay(data) {
    // Update 18 bars for left or right foot
    // Update max/avg values
    // Increment reading counts if recording
}

function updateAccelDisplay(data) {
    // Update acc X/Y/Z values
    // Update gyro X/Y/Z values
    // Update angle roll/pitch/yaw
}
```

#### `activityDisplay.js`
Shows detected activity with confidence and SVG icons.

```javascript
const activitySvgMap = {
    'Sitting': `<svg>...</svg>`,
    'Standing': `<svg>...</svg>`,
};

function updateActivityDisplay(activity, confidence) {
    // Update activity label with color coding
    // Show corresponding SVG icon
}
```

#### `timelineRenderer.js`
Renders timeline with time markers and activity segments.

```javascript
function updateTimeline(session) {
    // Generate time markers (1 second intervals)
    // Group consecutive windows with same label
    // Render colored activity segment bars
}
```

### Flow Control

#### `recordingManager.js`
Manages recording lifecycle.

```javascript
async function startRecording() {
    // 1. Show video container
    // 2. Create p5.js pose sketch with camera
    // 3. Create session on server
    // 4. Start video recording
    // 5. Update UI state
}

async function stopRecording() {
    // 1. Stop server session
    // 2. Stop pose sketch
    // 3. Stop and upload video
    // 4. Update UI state
}
```

#### `sessionManager.js`
CRUD operations for sessions.

```javascript
async function loadSessions() {
    // Fetch all sessions from API
    // Render session list in sidebar
}

async function selectSession(sessionId) {
    // Stop any active replay
    // Fetch replay data and metadata
    // Initialize replay state
    // Load video if available
    // Update timeline
}
```

#### `replayManager.js`
Playback control for session replay.

```javascript
function startReplay() {
    // Set isReplaying = true
    // Start video playback
    // Start timer for sensor data playback
}

function playNextReading() {
    // Get current window from buffer
    // Display foot/accel readings
    // Advance reading index
    // Preload next batch if needed
}
```

### Standalone Components

#### `activityDetector.js`
Rule-based activity detection from pose landmarks.

```javascript
class ActivityDetector {
    updateFootData(data) { /* buffer foot data */ }
    updateAccelData(data) { /* buffer accel data */ }
    detectActivity() {
        // Analyze pose landmarks
        // Return {activity, confidence}
    }
}
```

#### `videoRecorder.js`
MediaRecorder wrapper for video capture.

```javascript
class VideoRecorder {
    async startRecording(sessionId) { /* start MediaRecorder */ }
    async stopRecording() { /* stop and get blob */ }
    async uploadVideoWithProgress(sessionId, onProgress) { /* upload to server */ }
}
```

#### `poseSketch.js`
p5.js sketch for camera + skeleton overlay.

```javascript
function createPoseSketch(containerId, options) {
    // Create p5 instance
    // Initialize camera capture
    // Load ml5 MoveNet model
    // Draw skeleton on canvas
    // Return control object with getCanvasStream()
}
```

## Data Flow

### Recording Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         Socket.IO                                │
│                 (foot_data / accel_data events)                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     socketManager.js                             │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  Event Handler                                          │   │
│   │    1. Call updateFootDisplay() / updateAccelDisplay()   │   │
│   │    2. If recording: update activityDetector             │   │
│   │    3. If recording: emit activity_detected to server    │   │
│   └─────────────────────────────────────────────────────────┘   │
└───────────────┬───────────────────────────────┬─────────────────┘
                │                               │
                ▼                               ▼
┌───────────────────────────┐   ┌────────────────────────────────┐
│    sensorDisplay.js       │   │     activityDetector.js        │
│  - Update pressure bars   │   │  - Buffer sensor data          │
│  - Update accel values    │   │  - Analyze pose landmarks      │
│  - Increment counters     │   │  - Return activity + confidence│
└───────────────────────────┘   └───────────────┬────────────────┘
                                                │
                                                ▼
                                ┌────────────────────────────────┐
                                │     activityDisplay.js         │
                                │  - Show activity label         │
                                │  - Color-code confidence       │
                                │  - Display SVG icon            │
                                └────────────────────────────────┘
```

### Replay Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     sessionManager.js                            │
│                    selectSession(sessionId)                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────────────┐
│ GET /replay   │   │ GET /windows  │   │ GET /video            │
│ (raw data)    │   │ (metadata)    │   │ (HTTP stream)         │
└───────┬───────┘   └───────┬───────┘   └───────────┬───────────┘
        │                   │                       │
        ▼                   ▼                       ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────────────┐
│ replayWindows │   │ updateTimeline│   │ <video> element       │
│ (state.js)    │   │ (renderer.js) │   │ src = video URL       │
└───────┬───────┘   └───────────────┘   └───────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     replayManager.js                             │
│                     playNextReading()                            │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  Timer Loop (100ms intervals)                           │   │
│   │    1. Get current window from buffer                    │   │
│   │    2. Parse raw_data JSON                               │   │
│   │    3. Call updateFootDisplay() with reading             │   │
│   │    4. Call updateAccelDisplay() with reading            │   │
│   │    5. Update playhead position                          │   │
│   │    6. Sync video if drift detected                      │   │
│   │    7. Advance index, preload if needed                  │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## State Management

The frontend uses simple global variables in `state.js` rather than a framework:

**Recording State:**
- `isRecording` - Boolean flag
- `currentSessionId` - Active session UUID
- `recordingStartTime` - Timestamp for duration display
- `recordingTimer` - setInterval handle
- `footReadingCount` / `accelReadingCount` - Counters

**Replay State:**
- `replayWindows` - Loaded windows with raw data
- `replayWindowsMetadata` - Lightweight metadata for timeline
- `replayCurrentWindowIndex` - Current playback position
- `isReplaying` - Boolean flag
- `replayTimer` - setInterval handle
- `replaySessionDuration` - Total duration in seconds

**Managers:**
- `activityDetector` - ActivityDetector instance
- `videoRecorder` - VideoRecorder instance
- `poseSketch` - p5.js sketch control object

## Event Handling

HTML onclick handlers are exposed via `window` in `app.js`:

```javascript
window.toggleRecording = toggleRecording;
window.selectSession = selectSession;
window.deleteSession = deleteSession;
window.renameSession = renameSession;
window.replayControl = replayControl;
window.zoomTimeline = zoomTimeline;
```

This allows HTML like:
```html
<button onclick="toggleRecording()">Start Recording</button>
<button onclick="selectSession('uuid')">Session Name</button>
```

## Video Recording Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Camera    │────▶│  p5.js      │────▶│  Canvas     │
│   (WebRTC)  │     │  + MoveNet  │     │  (skeleton) │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               │ captureStream()
                                               ▼
                                        ┌─────────────┐
                                        │ MediaStream │
                                        └──────┬──────┘
                                               │
                                               │ new MediaRecorder(stream)
                                               ▼
                                        ┌─────────────┐
                                        │ MediaRecorder│
                                        └──────┬──────┘
                                               │
                                               │ ondataavailable
                                               ▼
                                        ┌─────────────┐
                                        │ Blob chunks │
                                        └──────┬──────┘
                                               │
                                               │ new Blob(chunks, type)
                                               ▼
                                        ┌─────────────┐
                                        │ Video Blob  │
                                        └──────┬──────┘
                                               │
                                               │ FormData + fetch
                                               ▼
                                        ┌─────────────┐
                                        │   Server    │
                                        │ /upload-video│
                                        └─────────────┘
```

## CSS Architecture

Styles use a combination of:
- **Tailwind CSS** (via CDN) - Utility classes in HTML
- **Custom CSS** (`css/record.css`) - Component-specific styles

Custom styles handle:
- Recording pulse animation
- Sensor bar transitions
- Video container positioning
- Recording indicator overlay

## Error Handling

Errors are handled at the module level with:
- Console logging for debugging
- User alerts for critical failures
- Graceful degradation where possible

```javascript
try {
    await videoRecorder.startRecording(sessionId);
} catch (error) {
    console.warn('[Video] Failed to start:', error.message);
    // Continue without video recording
}
```
