# API Integration

This document explains how the frontend communicates with the firefighter-server backend.

## Table of Contents

1. [Server Configuration](#server-configuration)
2. [REST API Endpoints](#rest-api-endpoints)
3. [Socket.IO Events](#socketio-events)
4. [Video Upload Format](#video-upload-format)
5. [Error Responses](#error-responses)
6. [Example Requests](#example-requests)

---

## Server Configuration

### Default Server URL

```javascript
const SERVER_URL = 'http://localhost:4100';
```

**Development:** Server runs on localhost port 4100
**Production:** Update URL to production server address

### Connection Check

```javascript
// Health check endpoint
fetch(`${SERVER_URL}/health`)
  .then(res => res.json())
  .then(data => console.log('Server status:', data));

// Expected response:
// {
//   "status": "ok",
//   "qdrant": "healthy",
//   "postgres": "healthy",
//   "active_session": null
// }
```

---

## REST API Endpoints

The frontend uses these HTTP endpoints for session management and video operations.

### Session Management

#### Create Session

**Endpoint:** `POST /api/sessions`

**Request:**
```javascript
const response = await fetch(`${SERVER_URL}/api/sessions`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'ladder_climb_drill_001',
    activity_type: 'Climbing'  // Optional
  })
});

const session = await response.json();
```

**Response:**
```json
{
  "id": "abc-123-session-id",
  "name": "ladder_climb_drill_001",
  "activity_type": "Climbing",
  "created_at": "2025-12-24T10:30:00.000Z",
  "status": "recording"
}
```

#### List All Sessions

**Endpoint:** `GET /api/sessions`

**Request:**
```javascript
const response = await fetch(`${SERVER_URL}/api/sessions`);
const sessions = await response.json();
```

**Response:**
```json
[
  {
    "id": "abc-123",
    "name": "ladder_climb_001",
    "created_at": "2025-12-24T10:30:00.000Z",
    "stopped_at": "2025-12-24T10:32:30.000Z",
    "status": "stopped",
    "video_file_path": "abc-123.webm",
    "video_size_bytes": 12582912
  },
  ...
]
```

#### Get Session Details

**Endpoint:** `GET /api/sessions/:id`

**Request:**
```javascript
const response = await fetch(`${SERVER_URL}/api/sessions/${sessionId}`);
const session = await response.json();
```

**Response:**
```json
{
  "id": "abc-123",
  "name": "ladder_climb_001",
  "activity_type": "Climbing",
  "created_at": "2025-12-24T10:30:00.000Z",
  "stopped_at": "2025-12-24T10:32:30.000Z",
  "status": "stopped",
  "video_file_path": "abc-123.webm",
  "video_duration_seconds": 150.0,
  "video_size_bytes": 12582912
}
```

#### Update Session (Rename)

**Endpoint:** `PUT /api/sessions/:id`

**Request:**
```javascript
const response = await fetch(`${SERVER_URL}/api/sessions/${sessionId}`, {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'new_session_name'
  })
});
```

**Response:**
```json
{
  "id": "abc-123",
  "name": "new_session_name",
  ...
}
```

#### Delete Session

**Endpoint:** `DELETE /api/sessions/:id`

**Request:**
```javascript
const response = await fetch(`${SERVER_URL}/api/sessions/${sessionId}`, {
  method: 'DELETE'
});
```

**Response:**
```json
{
  "success": true,
  "message": "Session deleted successfully"
}
```

**⚠️ Warning:** Deletes session metadata, sensor data, AND video file permanently.

#### Stop Recording

**Endpoint:** `POST /api/sessions/:id/stop`

**Request:**
```javascript
const response = await fetch(`${SERVER_URL}/api/sessions/${sessionId}/stop`, {
  method: 'POST'
});
```

**Response:**
```json
{
  "id": "abc-123",
  "status": "stopped",
  "stopped_at": "2025-12-24T10:32:30.000Z"
}
```

### Video Operations

#### Upload Video

**Endpoint:** `POST /api/sessions/:id/upload-video`

**Request:**
```javascript
const formData = new FormData();
formData.append('video', videoBlob, `${sessionId}.webm`);

const response = await fetch(
  `${SERVER_URL}/api/sessions/${sessionId}/upload-video`,
  {
    method: 'POST',
    body: formData
  }
);
```

**Response:**
```json
{
  "success": true,
  "video_file_path": "abc-123.webm",
  "size_bytes": 12582912
}
```

#### Stream Video (Playback)

**Endpoint:** `GET /api/sessions/:id/video`

**Request:**
```javascript
// Simple: Set video src
videoElement.src = `${SERVER_URL}/api/sessions/${sessionId}/video`;

// With Range header (for seeking):
const response = await fetch(
  `${SERVER_URL}/api/sessions/${sessionId}/video`,
  {
    headers: {
      'Range': 'bytes=0-1024'
    }
  }
);
```

**Response:**
- **Full video:** `200 OK` with video data
- **Partial (Range):** `206 Partial Content` with requested bytes

**Response Headers:**
```
Content-Type: video/webm
Content-Length: <file_size>
Accept-Ranges: bytes
Content-Range: bytes 0-1024/12582912  (if Range request)
```

### Replay Data

#### Get Replay Data

**Endpoint:** `GET /api/sessions/:id/replay`

**Request:**
```javascript
const response = await fetch(`${SERVER_URL}/api/sessions/${sessionId}/replay`);
const replayData = await response.json();
```

**Response:**
```json
{
  "session": {
    "id": "abc-123",
    "name": "ladder_climb_001",
    "created_at": "2025-12-24T10:30:00.000Z",
    "stopped_at": "2025-12-24T10:32:30.000Z",
    "video_file_path": "abc-123.webm"
  },
  "windows": [
    {
      "id": "window-1",
      "timestamp": "2025-12-24T10:30:00.500Z",
      "foot_data": [...],
      "accel_data": {...},
      "activity": "Standing",
      "confidence": 85
    },
    ...
  ]
}
```

#### Get Window Metadata (Timeline)

**Endpoint:** `GET /api/sessions/:id/windows`

**Request:**
```javascript
const response = await fetch(`${SERVER_URL}/api/sessions/${sessionId}/windows`);
const windows = await response.json();
```

**Response:**
```json
[
  {
    "timestamp": "2025-12-24T10:30:00.500Z",
    "activity": "Standing",
    "confidence": 85
  },
  {
    "timestamp": "2025-12-24T10:30:01.000Z",
    "activity": "Standing",
    "confidence": 87
  },
  ...
]
```

---

## Socket.IO Events

The frontend connects to the `/iot` namespace for real-time sensor data streaming.

### Connection

```javascript
const socket = io('http://localhost:4100/iot', {
  transports: ['websocket', 'polling']
});

// Connection events
socket.on('connect', () => {
  console.log('Socket.IO connected');
  updateConnectionStatus('Connected');
});

socket.on('disconnect', (reason) => {
  console.log('Socket.IO disconnected:', reason);
  updateConnectionStatus('Disconnected');
});
```

### Server → Client Events

#### Foot Pressure Data

**Event:** `foot_data`

**Data:**
```javascript
socket.on('foot_data', (data) => {
  // data = {
  //   data: {
  //     foot: 'L' | 'R',
  //     values: [18 pressure values],
  //     max: 45.2,
  //     avg: 12.3
  //   }
  // }

  updateFootVisualization(data.data);
});
```

**Frequency:** 10-20 Hz (every 50-100ms)

#### Accelerometer Data

**Event:** `accel_data`

**Data:**
```javascript
socket.on('accel_data', (data) => {
  // data = {
  //   data: {
  //     acc: { x: 0.1, y: 9.8, z: 0.2 },
  //     gyro: { x: 0, y: 0, z: 0 },
  //     angle: { roll: 0, pitch: 5, yaw: 0 }
  //   }
  // }

  updateAccelDisplay(data.data);

  // Run activity detection
  const activity = detectActivity(currentFootData, data.data);
  displayDetectedActivity(activity);
});
```

**Frequency:** 20-100 Hz (every 10-50ms)

#### Session Started

**Event:** `session_started`

**Data:**
```javascript
socket.on('session_started', (data) => {
  // data = {
  //   session_id: 'abc-123',
  //   name: 'ladder_climb_001'
  // }

  console.log('Recording started:', data.session_id);
});
```

#### Session Stopped

**Event:** `session_stopped`

**Data:**
```javascript
socket.on('session_stopped', (data) => {
  // data = {
  //   session_id: 'abc-123'
  // }

  console.log('Recording stopped:', data.session_id);
});
```

### Client → Server Events

#### Send Detected Activity (Optional)

**Event:** `activity_detected`

**Data:**
```javascript
socket.emit('activity_detected', {
  session_id: currentSessionId,
  activity: 'Standing',
  confidence: 85,
  timestamp: new Date().toISOString()
});
```

**Note:** Currently not used by server, but available for future features.

---

## Video Upload Format

### FormData Structure

```javascript
const formData = new FormData();
formData.append('video', videoBlob, filename);

// Breakdown:
// - Field name: 'video' (server expects this key)
// - Value: Blob object containing video data
// - Filename: Optional, defaults to `${sessionId}.webm`
```

### Content-Type

Browser automatically sets:
```
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...
```

### File Naming

Server saves video as:
```
{VIDEO_STORAGE_PATH}/{session_id}.webm

Example: /app/data/videos/abc-123-session-id.webm
```

---

## Error Responses

### HTTP Status Codes

| Code | Meaning | Common Cause |
|------|---------|--------------|
| **200** | OK | Request successful |
| **400** | Bad Request | Missing or invalid data |
| **404** | Not Found | Session or video doesn't exist |
| **500** | Server Error | Database or server issue |
| **507** | Insufficient Storage | Disk full, can't save video |

### Error Response Format

```json
{
  "error": "Detailed error message",
  "status": 400
}
```

### Common Errors

**400 - No video file provided:**
```json
{
  "error": "No video file provided"
}
```

**404 - Session not found:**
```json
{
  "error": "Session not found"
}
```

**404 - Video not found:**
```json
{
  "error": "Video not found"
}
```

**507 - Disk full:**
```json
{
  "error": "Insufficient storage space"
}
```

---

## Example Requests

### Complete Recording Flow

```javascript
// 1. Create session
const createResponse = await fetch(`${SERVER_URL}/api/sessions`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ name: 'test_session' })
});
const session = await createResponse.json();
const sessionId = session.id;

// 2. Start video recording
videoRecorder.startRecording(sessionId);

// 3. Wait for training to complete...
await new Promise(resolve => setTimeout(resolve, 10000));

// 4. Stop session
await fetch(`${SERVER_URL}/api/sessions/${sessionId}/stop`, {
  method: 'POST'
});

// 5. Stop video and upload
await videoRecorder.stopRecording();
const uploadResponse = await videoRecorder.uploadVideo(sessionId);
console.log('Upload result:', uploadResponse);

// 6. Verify session
const sessionResponse = await fetch(`${SERVER_URL}/api/sessions/${sessionId}`);
const updatedSession = await sessionResponse.json();
console.log('Video path:', updatedSession.video_file_path);
```

### Replay Flow

```javascript
// 1. Fetch replay data
const replayResponse = await fetch(`${SERVER_URL}/api/sessions/${sessionId}/replay`);
const replayData = await replayResponse.json();

// 2. Load video (if available)
if (replayData.session.video_file_path) {
  const videoElement = document.getElementById('replay-video');
  videoElement.src = `${SERVER_URL}/api/sessions/${sessionId}/video`;
}

// 3. Build timeline from windows
buildTimeline(replayData.windows);

// 4. Start playback
startReplayTimer(replayData.windows);
```

---

**Document Version:** 1.0
**Last Updated:** December 24, 2025
