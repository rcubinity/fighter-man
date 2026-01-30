# Frontend

Browser-based user interface for the Firefighter Activity Recognition system. Provides live sensor visualization, video recording with pose detection, and session replay capabilities.

## Overview

The frontend is a single-page application that enables:
- Creating and managing recording sessions
- Live visualization of foot pressure and accelerometer data
- Video capture with real-time pose skeleton overlay (MoveNet)
- Client-side activity detection
- Session replay with synchronized video and sensor timeline

## Quick Start

### Option 1: Open Directly

Open `record.html` directly in a browser:

```bash
open /path/to/frontend/record.html
```

Note: Some features may be limited due to file:// protocol restrictions.

### Option 2: Local HTTP Server (Recommended)

Serve via HTTP for full functionality:

```bash
cd frontend
python -m http.server 8080
# Then open: http://localhost:8080/record.html
```

### Prerequisites

- Modern browser with WebRTC support (Chrome, Firefox, Edge)
- Firefighter server running on `http://localhost:4100`

## Project Structure

```
frontend/
├── record.html              # Main HTML page (single-page app)
├── css/
│   └── record.css           # Custom styles
└── js/
    ├── app.js               # Application entry point
    ├── config.js            # Configuration constants
    ├── state.js             # Centralized state management
    ├── dom.js               # DOM element references
    ├── utils.js             # Utility functions
    ├── socketManager.js     # Socket.IO connection handling
    ├── sessionManager.js    # Session CRUD operations
    ├── recordingManager.js  # Recording flow control
    ├── replayManager.js     # Replay playback control
    ├── sensorDisplay.js     # Sensor data visualization
    ├── activityDisplay.js   # Activity detection display
    ├── timelineRenderer.js  # Timeline UI rendering
    ├── poseSketch.js        # p5.js camera + skeleton
    ├── activityDetector.js  # Rule-based activity detection
    └── videoRecorder.js     # MediaRecorder wrapper
```

## Features

### Recording Mode

1. Click "Start Recording" to begin a new session
2. Camera activates with pose skeleton overlay
3. Live sensor data displays in the right sidebar
4. Activity is detected in real-time from pose data
5. Click "Stop Recording" to end and upload video

### Replay Mode

1. Select a past session from the left sidebar
2. Video plays with synchronized sensor data
3. Timeline shows activity segments color-coded
4. Use playback controls (play/pause, prev/next)

### Live Sensor Display

**Foot Pressure:**
- 18 vertical bars per foot showing pressure distribution
- Max and average values displayed below
- Updates at ~30 Hz when sensors connected

**Accelerometer:**
- Acceleration (X, Y, Z) in m/s^2
- Gyroscope (X, Y, Z) in degrees/s
- Angles (Roll, Pitch, Yaw) in degrees

### Activity Detection

The frontend performs client-side activity detection using pose landmarks:

| Activity | Detection Criteria |
|----------|-------------------|
| Standing | Upright posture, shoulders above hips |
| Sitting | Knees bent, torso upright |
| Lying_Down | Horizontal body position |
| Bent_Forward | Shoulders lower than normal standing |
| Jumping | Sudden vertical movement |

Detection results are sent to the server to label sensor windows.

## External Dependencies

Loaded via CDN in `record.html`:

| Library | Version | Purpose |
|---------|---------|---------|
| Socket.IO | 4.7.2 | Real-time communication |
| p5.js | 1.9.0 | Canvas rendering |
| ml5.js | 1.x | MoveNet pose detection |
| Tailwind CSS | CDN | Utility-first styling |

## Configuration

Edit `js/config.js` to change settings:

```javascript
const CONFIG = {
    SERVER_URL: 'http://localhost:4100',
    CAMERA_TIMEOUT_MS: 5000,
    ML5_MODEL_TIMEOUT_MS: 10000,
    VIDEO_MAX_SIZE_MB: 500,
    REPLAY_BATCH_SIZE: 20,
    REPLAY_PRELOAD_OFFSET: 10,
    REPLAY_BASE_INTERVAL_MS: 100,
    RECORDING_TIMER_INTERVAL_MS: 1000,
    SOCKET_RECONNECTION_ATTEMPTS: 5,
    SOCKET_RECONNECTION_DELAY_MS: 1000,
};
```

## UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Header: Title + Connection Status                              │
├──────────────┬────────────────────────────┬─────────────────────┤
│              │                            │                     │
│  Left        │   Center                   │   Right             │
│  Sidebar     │   Area                     │   Sidebar           │
│              │                            │                     │
│  - Session   │   - Video/Pose Preview     │   - Foot Pressure   │
│    Name      │   - Recording State        │     Visualization   │
│  - Record    │   - Replay Controls        │   - Accelerometer   │
│    Button    │   - Activity Display       │     Values          │
│  - Past      │                            │                     │
│    Sessions  │                            │                     │
│              │                            │                     │
├──────────────┴────────────────────────────┴─────────────────────┤
│  Timeline: Time markers + Activity segments + Playhead          │
└─────────────────────────────────────────────────────────────────┘
```

## Browser Compatibility

| Browser | Support | Notes |
|---------|---------|-------|
| Chrome | Full | Recommended |
| Firefox | Full | |
| Safari | Partial | WebRTC may require permissions |
| Edge | Full | |

## Troubleshooting

### Camera Not Working

- Check browser permissions for camera access
- Ensure no other app is using the camera
- Try a different browser

### Not Connecting to Server

- Verify server is running on port 4100
- Check browser console for CORS errors
- Ensure `SERVER_URL` in config matches server address

### Video Upload Fails

- Check file size is under limit (500 MB default)
- Verify server has write permissions to video directory
- Check browser console for upload errors

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Code structure and module interactions
- [SOCKET_EVENTS.md](./SOCKET_EVENTS.md) - Socket.IO event reference
