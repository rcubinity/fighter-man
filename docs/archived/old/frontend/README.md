# Frontend Documentation

Welcome to the Firefighter Activity Recognition frontend documentation. This interface allows operators to record training sessions with synchronized video and sensor data, then replay them for analysis.

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Requirements](#system-requirements)
3. [File Structure](#file-structure)
4. [Detailed Guides](#detailed-guides)
5. [Getting Help](#getting-help)

---

## Quick Start

Get up and running in 3 simple steps:

### 1. Start the Backend Server

Make sure the firefighter-server is running:

```bash
cd firefighter-server
python server.py
```

Server should be accessible at `http://localhost:4100`

### 2. Open the Recording Interface

Open `record.html` in a modern web browser:

```bash
# From the frontend directory
open record.html  # macOS
# OR
xdg-open record.html  # Linux
# OR
start record.html  # Windows
```

### 3. Grant Camera Permission

When prompted, allow camera access for video recording. You can still use the application for sensor-only recording if you decline.

---

## System Requirements

### Browser Compatibility

The frontend requires a modern web browser with support for:
- MediaRecorder API (video recording)
- WebSocket/Socket.IO (real-time sensor data)
- ES6 JavaScript features

**Supported Browsers:**
- ✅ Chrome 90+ (Recommended)
- ✅ Firefox 88+
- ✅ Safari 14.1+
- ✅ Edge 90+

**Note:** HTTPS or localhost is required for camera access.

### Hardware Requirements

- **Camera:** Webcam or integrated camera for video recording
- **Network:** Stable connection to firefighter-server
- **Storage:** Browser should have sufficient disk space for video uploads

---

## File Structure

```
frontend/
├── record.html                    # Main recording/replay application
└── js/
    ├── activityDetector.js       # Real-time activity recognition
    ├── videoRecorder.js          # Camera access & video upload
    └── poseSketch.js             # p5.js camera + skeleton visualization

docs/frontend/                     # Documentation (centralized)
├── README.md                      # This file (getting started)
├── ARCHITECTURE.md                # System architecture
├── RECORDING_GUIDE.md             # How to record sessions
├── REPLAY_GUIDE.md                # How to replay sessions
├── ACTIVITY_DETECTION.md          # Activity recognition details
├── VIDEO_RECORDING.md             # Video capture technical details
├── API_INTEGRATION.md             # Server communication
└── TROUBLESHOOTING.md             # Common issues and solutions
```

---

## Detailed Guides

### For Operators

If you're recording and replaying training sessions:

- **[Recording Guide](RECORDING_GUIDE.md)** - Step-by-step instructions for recording sessions
- **[Replay Guide](REPLAY_GUIDE.md)** - How to replay and analyze recorded sessions
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions

### For Developers

If you're working on the frontend code:

- **[Architecture](ARCHITECTURE.md)** - System design and component overview
- **[Activity Detection](ACTIVITY_DETECTION.md)** - How activity recognition works
- **[Video Recording](VIDEO_RECORDING.md)** - MediaRecorder API implementation
- **[API Integration](API_INTEGRATION.md)** - Communication with backend server

---

## Getting Help

### Quick Troubleshooting

**Can't connect to server?**
- Check that firefighter-server is running at `http://localhost:4100/health`
- Verify Socket.IO connection (status shown in top-right corner)

**Camera not working?**
- Check browser permissions (click lock icon in address bar)
- Close other applications using the camera
- See [Troubleshooting Guide](TROUBLESHOOTING.md) for more details

**No sensor data appearing?**
- Ensure Raspberry Pi with sensors is running
- Check that sensor-hub is streaming to server
- Verify Socket.IO connection status (should show "Connected")

### Additional Resources

- **Server Documentation:** `/firefighter-server/docs/`
- **Sensor Documentation:** `/sensor-hub/docs/`
- **Issue Tracker:** Report bugs and request features via your project repository

---

## Project Purpose

This frontend is part of the Firefighter Activity Recognition system, designed to:

1. **Record Training Sessions** - Capture sensor data and video during firefighter training
2. **Detect Activities** - Recognize activities (Standing, Sitting, Crawling, etc.) in real-time
3. **Replay & Analyze** - Review sessions with synchronized video and sensor visualization
4. **Support ML Training** - Provide labeled data for machine learning models

The system uses foot pressure sensors (18 per foot) and a 9-axis IMU (accelerometer + gyroscope) to detect firefighter activities during training drills.

---

**Document Version:** 1.0
**Last Updated:** December 24, 2025
