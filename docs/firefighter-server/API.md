# Firefighter Server API Reference

This document describes all REST endpoints and Socket.IO events provided by the firefighter-server.

## Base URL

```
http://localhost:4100
```

## REST API

### Health & Configuration

#### `GET /health`

Check server health and database connections.

**Response:**
```json
{
  "status": "healthy",
  "server": "running",
  "qdrant": {
    "status": "healthy",
    "collection": "sensor_windows",
    "points_count": 1234
  },
  "postgres": {
    "status": "healthy",
    "host": "localhost"
  },
  "active_session": "uuid-or-null"
}
```

#### `GET /api/activity-types`

Get list of valid activity types for Stage 1 data collection.

**Response:**
```json
[
  "Walking",
  "Running",
  "Crawling",
  "Climbing",
  "Standing",
  "Kneeling",
  "Sitting",
  "Carrying",
  "Hose_Operation",
  "Idle"
]
```

---

### Sessions

#### `POST /api/sessions`

Create a new recording session.

**Request Body:**
```json
{
  "name": "optional session name",
  "activity_type": "Walking"
}
```

- `name`: Optional. Auto-generated if omitted (e.g., `recording_20250130_143022`)
- `activity_type`: Optional. Must be one of the valid activity types.

**Response (201):**
```json
{
  "id": "uuid",
  "name": "Session Name",
  "activity_type": "Walking",
  "status": "recording",
  "created_at": "2025-01-30T14:30:22.000000+00:00",
  "stopped_at": null,
  "video_file_path": null,
  "video_duration_seconds": null,
  "video_size_bytes": null
}
```

**Side Effects:**
- Auto-stops any existing active session
- Emits `session_started` Socket.IO event

---

#### `GET /api/sessions`

List all sessions (newest first).

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Session Name",
    "activity_type": "Walking",
    "status": "stopped",
    "created_at": "2025-01-30T14:30:22.000000+00:00",
    "stopped_at": "2025-01-30T14:35:22.000000+00:00",
    "video_file_path": "uuid.webm",
    "video_duration_seconds": 300.5,
    "video_size_bytes": 15234567
  }
]
```

---

#### `GET /api/sessions/active`

Get the currently active (recording) session.

**Response:**
```json
{
  "id": "uuid",
  "name": "Session Name",
  "status": "recording",
  ...
}
```

Returns `null` if no active session.

---

#### `GET /api/sessions/{session_id}`

Get session details with window summary.

**Response:**
```json
{
  "id": "uuid",
  "name": "Session Name",
  "activity_type": "Walking",
  "status": "stopped",
  "created_at": "...",
  "stopped_at": "...",
  "window_count": 42,
  "windows": [
    {
      "id": "window-uuid",
      "start_time": 1706624422000,
      "end_time": 1706624422500,
      "foot_count": 8,
      "accel_count": 6,
      "label": "Walking"
    }
  ]
}
```

---

#### `PUT /api/sessions/{session_id}`

Update session metadata or window labels.

**Request Body:**
```json
{
  "name": "New Name",
  "status": "completed",
  "labels": {
    "window-uuid-1": "Walking",
    "window-uuid-2": "Standing"
  }
}
```

All fields are optional. The `labels` field updates activity labels for specific windows in Qdrant.

**Response:** Updated session object.

---

#### `DELETE /api/sessions/{session_id}`

Delete a session and all its data.

**Response:**
```json
{
  "message": "Session deleted",
  "windows_deleted": 42
}
```

---

#### `POST /api/sessions/{session_id}/stop`

Stop the current recording session.

**Response:** Updated session object with `status: "stopped"` and `stopped_at` timestamp.

**Side Effects:**
- Flushes remaining sensor data to Qdrant
- Clears detected activities for the session
- Emits `session_stopped` Socket.IO event

---

### Replay

#### `GET /api/sessions/{session_id}/replay`

Get windows with raw sensor data for replay (paginated).

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `offset` | int | 0 | Starting window index |
| `limit` | int | 20 | Number of windows (max 100) |

**Response:**
```json
{
  "session": { ... },
  "windows": [
    {
      "id": "window-uuid",
      "start_time": 1706624422000,
      "end_time": 1706624422500,
      "foot_count": 8,
      "accel_count": 6,
      "label": "Walking",
      "raw_data": {
        "foot": [
          {
            "timestamp": "2025-01-30T14:30:22.100",
            "device": "LEFT_FOOT",
            "data": {
              "foot": "LEFT",
              "values": [1.2, 3.4, ...],
              "max": 45.2,
              "avg": 12.3
            }
          }
        ],
        "accel": [
          {
            "timestamp": "2025-01-30T14:30:22.150",
            "device": "ACCELEROMETER",
            "data": {
              "acc": {"x": 0.1, "y": -0.2, "z": 9.8},
              "gyro": {"x": 1.2, "y": -0.5, "z": 0.3},
              "angle": {"roll": 2.1, "pitch": -1.3, "yaw": 45.2}
            }
          }
        ]
      }
    }
  ],
  "total_windows": 100,
  "offset": 0,
  "limit": 20,
  "has_more": true
}
```

---

#### `GET /api/sessions/{session_id}/windows`

Get all windows metadata (lightweight, no raw data).

Used for timeline rendering.

**Response:**
```json
[
  {
    "window_id": "uuid",
    "session_id": "uuid",
    "label": "Walking",
    "start_time": 1706624422000,
    "end_time": 1706624422500,
    "foot_count": 8,
    "accel_count": 6
  }
]
```

---

### Export

#### `GET /api/sessions/{session_id}/export`

Export session data for ML training or analysis.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `format` | string | `json` | Export format: `json` or `csv` |
| `include_raw` | string | `false` | Include raw sensor data |

**JSON Response:**
```json
{
  "session": { ... },
  "windows": [ ... ],
  "window_count": 42
}
```

**CSV Response:**
Downloads a CSV file with columns: `id`, `start_time`, `end_time`, `foot_count`, `accel_count`, `label`

---

### Media (Video)

#### `POST /api/sessions/{session_id}/upload-video`

Upload video file for a session.

**Content-Type:** `multipart/form-data`

**Form Data:**
- `video`: Video file (webm, mp4, avi, mov)

**Response:**
```json
{
  "success": true,
  "video_file_path": "uuid.webm",
  "size_bytes": 15234567
}
```

---

#### `GET /api/sessions/{session_id}/video`

Stream video file for a session.

**Headers:**
- Supports HTTP Range requests for seeking

**Response:**
- `video/webm` content
- 206 Partial Content for range requests
- 200 OK for full file

---

### Search

#### `POST /api/query/similar`

Find sensor patterns similar to a reference window.

**Request Body:**
```json
{
  "window_id": "reference-window-uuid",
  "session_id": "optional-filter-session",
  "label": "optional-filter-label",
  "limit": 10
}
```

**Response:**
```json
{
  "reference_id": "window-uuid",
  "similar_windows": [
    {
      "id": "similar-uuid",
      "score": 0.95,
      "session_id": "session-uuid",
      "start_time": 1706624422000,
      "end_time": 1706624422500,
      "label": "Walking"
    }
  ]
}
```

---

## Socket.IO API

### Namespace

All Socket.IO events use the `/iot` namespace:

```javascript
const socket = io('http://localhost:4100/iot');
```

### Client Events (Browser/Device -> Server)

#### `authenticate`

Authenticate a device connection.

**Payload:**
```json
{
  "device_key": "firefighter_pi_001"
}
```

**Response Events:**
- `auth_success` with `{device_key, session_id}`
- `auth_error` with `{message}` (then disconnects)

---

#### `foot_pressure_data`

Send foot sensor reading (from Raspberry Pi).

**Payload:**
```json
{
  "timestamp": "2025-01-30T14:30:22.100",
  "device": "LEFT_FOOT",
  "data": {
    "foot": "LEFT",
    "max": 45.2,
    "avg": 12.3,
    "active_count": 12,
    "values": [1.2, 3.4, 5.6, ...]
  }
}
```

---

#### `accelerometer_data`

Send accelerometer reading (from Raspberry Pi).

**Payload:**
```json
{
  "timestamp": "2025-01-30T14:30:22.150",
  "device": "ACCELEROMETER",
  "data": {
    "acc": {"x": 0.1, "y": -0.2, "z": 9.8},
    "gyro": {"x": 1.2, "y": -0.5, "z": 0.3},
    "angle": {"roll": 2.1, "pitch": -1.3, "yaw": 45.2}
  }
}
```

---

#### `activity_detected`

Send detected activity from frontend (for window labeling).

**Payload:**
```json
{
  "session_id": "uuid",
  "activity": "Standing",
  "confidence": 85,
  "timestamp": "2025-01-30T14:30:22.000"
}
```

---

### Server Events (Server -> Clients)

#### `foot_data`

Broadcast foot sensor data to all connected browsers.

**Payload:** Same as `foot_pressure_data` input.

---

#### `accel_data`

Broadcast accelerometer data to all connected browsers.

**Payload:** Same as `accelerometer_data` input.

---

#### `session_started`

Emitted when a new recording session is created.

**Payload:**
```json
{
  "session_id": "uuid",
  "name": "Session Name",
  "activity_type": "Walking"
}
```

---

#### `session_stopped`

Emitted when a recording session is stopped.

**Payload:**
```json
{
  "session_id": "uuid"
}
```

---

## Error Responses

All error responses follow a consistent format:

```json
{
  "error": "Error message describing the problem"
}
```

Common HTTP status codes:
- `400` - Invalid request (missing required field, invalid value)
- `404` - Resource not found (session, window, video)
- `500` - Internal server error

---

## Rate Limits

No explicit rate limits are enforced. However:
- Sensor data arrives at ~30 Hz from devices
- Socket.IO events are throttled on the frontend to prevent UI spam
- Video uploads have a configurable maximum size (default 500 MB)
