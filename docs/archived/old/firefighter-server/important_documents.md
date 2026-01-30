# Firefighter Server - Developer Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Use Cases](#use-cases)
3. [System Requirements](#system-requirements)
4. [Installation](#installation)
5. [Running the Server](#running-the-server)
6. [API Reference](#api-reference)
7. [Socket.IO Events](#socketio-events)
8. [Data Models](#data-models)
9. [Configuration](#configuration)
10. [Testing](#testing)
11. [Troubleshooting](#troubleshooting)

---

## Project Overview

### Purpose

The Firefighter Server is a real-time data collection and storage system designed for training AI models to recognize firefighter activities. It receives sensor data from wearable devices (foot pressure sensors and accelerometers) via Socket.IO and stores them in a Qdrant vector database for similarity search and ML training.

### Technology Stack

| Component | Technology |
|-----------|------------|
| Web Framework | Flask 3.0+ |
| Real-time Communication | Flask-SocketIO 5.3+ |
| Vector Database | Qdrant (Docker) |
| Data Processing | NumPy |
| Production Server | Gunicorn + Eventlet |
| Video Codec | WebM (VP9/VP8) |

### Architecture

```
                    ┌─────────────────────────────────────┐
                    │         FIREFIGHTER SERVER          │
                    │                                     │
┌──────────┐        │  ┌─────────────┐  ┌─────────────┐  │
│          │ Socket │  │             │  │             │  │
│ Pi with  │───────▶│  │  Socket.IO  │─▶│   Vector    │  │
│ Sensors  │  .IO   │  │  Handler    │  │   Store     │  │
│          │        │  │             │  │  (Qdrant)   │  │
└──────────┘        │  └─────────────┘  └─────────────┘  │
                    │         │                │         │
┌──────────┐        │         ▼                ▼         │
│ Browser  │  HTTP  │  ┌─────────────────────────────┐  │
│ (Video)  │───────▶│  │        REST API             │  │
│          │ Upload │  │  /api/sessions, /api/video  │  │
└──────────┘        │  │                             │  │
                    │  └─────────────────────────────┘  │
                    │         │                │         │
                    │         ▼                ▼         │
┌──────────┐        │  ┌─────────────┐  ┌─────────────┐  │
│          │  REST  │  │             │  │             │  │
│ Annotation│◀──────│  │  PostgreSQL │  │ File System │  │
│   Tool   │  API   │  │  (Metadata) │  │   (Videos)  │  │
│          │        │  │             │  │             │  │
└──────────┘        │  └─────────────┘  └─────────────┘  │
                    │                                     │
                    └─────────────────────────────────────┘
```

---

## Use Cases

### Use Case 1: Real-time Data Collection

**Actor:** Raspberry Pi with BLE sensors
**Description:** Collect sensor data during firefighter training sessions

**Flow:**
1. Pi connects to server via Socket.IO (`/iot` namespace)
2. Pi authenticates with device key
3. Operator creates a recording session via REST API
4. Pi sends foot pressure data (10-20Hz) and accelerometer data (20-100Hz)
5. Server accumulates data into 500ms time windows
6. Windows are stored as vectors in Qdrant
7. Operator stops session when training complete

### Use Case 2: Session Management

**Actor:** Training operator / Admin
**Description:** Manage recording sessions

**Operations:**
- Create new session before training starts
- Monitor active session status
- Stop session when training complete
- View session details and data statistics
- Delete old/invalid sessions

### Use Case 3: Data Export for Annotation

**Actor:** Annotation tool / ML Engineer
**Description:** Export recorded data for labeling

**Flow:**
1. Request session export via REST API
2. Receive time-ordered sensor windows
3. Each window contains raw foot + accelerometer readings
4. Apply activity labels (Walking, Running, Crawling, etc.)
5. Update labels back to server via PUT endpoint

### Use Case 4: Similarity Search

**Actor:** ML Engineer / Annotation tool
**Description:** Find similar movement patterns

**Flow:**
1. Select a reference time window
2. Query for similar windows across all sessions
3. Server returns windows ranked by similarity score
4. Use for:
   - Finding unlabeled data similar to labeled examples
   - Detecting anomalies
   - Quality checking annotations

### Use Case 5: Video Recording and Synchronization

**Actor:** Browser-based frontend, Training operator
**Description:** Record synchronized video during training sessions

**Flow:**
1. Operator opens recording UI in browser
2. Browser requests camera access via MediaRecorder API
3. Operator creates session via REST API
4. Video recording starts simultaneously with sensor streaming
5. Session recorded with both sensor data and video
6. Video stops and uploads to server on session stop
7. Video file stored on filesystem, path stored in PostgreSQL
8. During replay, video plays synchronized with sensor timeline

**Benefits:**
- Visual validation of sensor data
- Activity labeling reference (see what firefighter was actually doing)
- Training review and analysis
- Future ML integration: pose detection from video

---

## System Requirements

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 10 GB | 50+ GB SSD |
| Network | 100 Mbps | 1 Gbps |

### Software

| Software | Version |
|----------|---------|
| Python | 3.11+ |
| Docker | 20.0+ |
| OS | Linux (Ubuntu 22.04+), macOS, Windows with WSL2 |

---

## Installation

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd firefighter-server
```

### Step 2: Start Qdrant (Vector Database)

```bash
# Pull and run Qdrant container
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/data/qdrant:/qdrant/storage \
  qdrant/qdrant

# Verify Qdrant is running
curl http://localhost:6333/health
# Expected: {"status":"ok"}
```

### Step 3: Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy example config (if exists) or edit .env directly
cp .env.example .env  # optional

# Edit configuration
nano .env
```

Key settings to configure:
```bash
SERVER_PORT=4100
QDRANT_HOST=localhost
QDRANT_PORT=6333
ALLOWED_DEVICE_KEYS=firefighter_pi_001,firefighter_pi_002
```

---

## Running the Server

### Development Mode

```bash
# Using start script
./start.sh

# Or manually
source venv/bin/activate
python server.py
```

Server starts at: `http://localhost:4100`

### Production Mode (Docker)

```bash
# Start both Qdrant and Server
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Production Mode (Manual)

```bash
source venv/bin/activate
gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:4100 server:app
```

---

## API Reference

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "server": "running",
  "qdrant": {
    "status": "healthy",
    "collection": "sensor_windows",
    "points_count": 1250
  },
  "active_session": "uuid-of-active-session"
}
```

---

### Sessions

#### Create Session

```http
POST /api/sessions
Content-Type: application/json

{
  "name": "training_session_001"
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "training_session_001",
  "created_at": "2025-12-01T10:30:00.000Z",
  "status": "recording"
}
```

#### List Sessions

```http
GET /api/sessions
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "training_session_001",
    "created_at": "2025-12-01T10:30:00.000Z",
    "status": "recording"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "training_session_002",
    "created_at": "2025-12-01T09:00:00.000Z",
    "status": "stopped"
  }
]
```

#### Get Session Details

```http
GET /api/sessions/:id
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "training_session_001",
  "created_at": "2025-12-01T10:30:00.000Z",
  "status": "stopped",
  "window_count": 120,
  "windows": [
    {
      "id": "window-uuid-1",
      "start_time": 1701423000000,
      "end_time": 1701423000500,
      "foot_count": 5,
      "accel_count": 10,
      "label": "Walking"
    }
  ]
}
```

#### Update Session

```http
PUT /api/sessions/:id
Content-Type: application/json

{
  "name": "renamed_session",
  "status": "completed",
  "labels": {
    "window-uuid-1": "Walking",
    "window-uuid-2": "Running",
    "window-uuid-3": "Crawling"
  }
}
```

#### Stop Session

```http
POST /api/sessions/:id/stop
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "stopped",
  "stopped_at": "2025-12-01T11:00:00.000Z"
}
```

#### Delete Session

```http
DELETE /api/sessions/:id
```

**Response:**
```json
{
  "message": "Session deleted",
  "windows_deleted": 120
}
```

---

### Export

#### Export Session Data

```http
GET /api/sessions/:id/export?format=json&include_raw=true
```

**Query Parameters:**
| Parameter | Values | Default | Description |
|-----------|--------|---------|-------------|
| format | json, csv | json | Export format |
| include_raw | true, false | false | Include raw sensor readings |

**Response (JSON):**
```json
{
  "session": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "training_session_001"
  },
  "window_count": 120,
  "windows": [
    {
      "id": "window-uuid-1",
      "start_time": 1701423000000,
      "end_time": 1701423000500,
      "foot_count": 5,
      "accel_count": 10,
      "label": "Walking",
      "raw_data": {
        "foot": [
          {
            "timestamp": "2025-12-01T10:30:00.100Z",
            "device": "LEFT_FOOT",
            "data": {
              "foot": "LEFT",
              "max": 150.5,
              "avg": 75.2,
              "active_count": 12,
              "values": [10.0, 20.5, ...]
            }
          }
        ],
        "accel": [
          {
            "timestamp": "2025-12-01T10:30:00.050Z",
            "device": "ACCELEROMETER",
            "data": {
              "acc": {"x": 0.1, "y": -0.2, "z": 9.8},
              "gyro": {"x": 1.5, "y": -2.3, "z": 0.5},
              "angle": {"roll": 5.2, "pitch": -3.1, "yaw": 180.0}
            }
          }
        ]
      }
    }
  ]
}
```

---

### Similarity Search

#### Find Similar Windows

```http
POST /api/query/similar
Content-Type: application/json

{
  "window_id": "window-uuid-1",
  "session_id": "optional-filter-by-session",
  "label": "optional-filter-by-label",
  "limit": 10
}
```

**Response:**
```json
{
  "reference_id": "window-uuid-1",
  "similar_windows": [
    {
      "id": "window-uuid-42",
      "score": 0.95,
      "session_id": "session-uuid",
      "start_time": 1701423500000,
      "end_time": 1701423500500,
      "label": "Walking"
    },
    {
      "id": "window-uuid-87",
      "score": 0.89,
      "session_id": "session-uuid",
      "start_time": 1701424000000,
      "end_time": 1701424000500,
      "label": null
    }
  ]
}
```

---

### Video Management

#### Upload Video

```http
POST /api/sessions/:id/upload-video
Content-Type: multipart/form-data

video=@recording.webm
```

**Response (200):**
```json
{
  "success": true,
  "video_file_path": "550e8400-e29b-41d4-a716-446655440000.webm",
  "size_bytes": 12582912
}
```

**Example:**
```bash
# Upload video for session
curl -X POST http://localhost:4100/api/sessions/{session_id}/upload-video \
  -F "video=@recording.webm"

# Response
{
  "success": true,
  "video_file_path": "550e8400-e29b-41d4-a716-446655440000.webm",
  "size_bytes": 12582912
}
```

#### Stream Video

```http
GET /api/sessions/:id/video
Range: bytes=0-1024  (optional)
```

**Response (200 Full Video):**
```
Content-Type: video/webm
Content-Length: 12582912
Accept-Ranges: bytes

<video binary data>
```

**Response (206 Partial Content with Range):**
```
Content-Type: video/webm
Content-Range: bytes 0-1024/12582912
Content-Length: 1024
Accept-Ranges: bytes

<partial video data>
```

**Example:**
```bash
# Stream full video
curl http://localhost:4100/api/sessions/{session_id}/video \
  --output video.webm

# Request partial content (for seeking)
curl -H "Range: bytes=0-1024" \
  http://localhost:4100/api/sessions/{session_id}/video \
  --output video_chunk.webm

# Browser automatically sends Range headers for seeking support
```

---

## Socket.IO Events

### Namespace: `/iot`

#### Client → Server

| Event | Payload | Description |
|-------|---------|-------------|
| `authenticate` | `{"device_key": "firefighter_pi_001"}` | Authenticate device |
| `foot_pressure_data` | See below | Send foot sensor reading |
| `accelerometer_data` | See below | Send accelerometer reading |

**Foot Pressure Data:**
```json
{
  "timestamp": "2025-12-01T10:30:00.100Z",
  "device": "LEFT_FOOT",
  "data": {
    "foot": "LEFT",
    "max": 150.5,
    "avg": 75.2,
    "active_count": 12,
    "values": [10.0, 20.5, 30.2, 40.1, 50.5, 60.3, 70.8, 80.2, 90.1, 100.5, 110.2, 120.3, 130.1, 140.5, 145.2, 148.3, 150.0, 149.5]
  }
}
```

**Accelerometer Data:**
```json
{
  "timestamp": "2025-12-01T10:30:00.050Z",
  "device": "ACCELEROMETER",
  "data": {
    "acc": {"x": 0.1, "y": -0.2, "z": 9.8},
    "gyro": {"x": 1.5, "y": -2.3, "z": 0.5},
    "angle": {"roll": 5.2, "pitch": -3.1, "yaw": 180.0}
  }
}
```

#### Server → Client

| Event | Payload | Description |
|-------|---------|-------------|
| `auth_success` | `{"device_key": "...", "session_id": "..."}` | Authentication successful |
| `auth_error` | `{"message": "Invalid device key"}` | Authentication failed |
| `session_started` | `{"session_id": "...", "name": "..."}` | New session started |
| `session_stopped` | `{"session_id": "..."}` | Session stopped |

---

## Data Models

### Sensor Window (Qdrant Document)

Each time window (500ms) is stored as a vector in Qdrant:

| Field | Type | Description |
|-------|------|-------------|
| id | string | UUID |
| vector | float[270] | Normalized sensor values |
| session_id | string | Parent session UUID |
| device | string | Device identifier |
| start_time | float | Window start (ms since epoch) |
| end_time | float | Window end (ms since epoch) |
| foot_count | int | Number of foot readings |
| accel_count | int | Number of accel readings |
| label | string | Activity label (nullable) |
| raw_data | string | JSON of raw readings |

### Vector Composition (270 dimensions)

```
[0-179]   : 10 foot readings × 18 pressure values = 180 dims
[180-269] : 10 accel readings × 9 values (acc xyz, gyro xyz, angle rpy) = 90 dims
```

### Video Metadata (Sessions Extension)

Sessions can optionally include video recordings. Video metadata is stored in PostgreSQL:

| Field | Type | Description |
|-------|------|-------------|
| `video_file_path` | TEXT | Filename of video file (e.g., "550e8400.webm") |
| `video_duration_seconds` | REAL | Video length in seconds |
| `video_size_bytes` | INTEGER | File size in bytes |

**Example Session with Video:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "ladder_climb_001",
  "created_at": "2025-12-24T10:30:00.000Z",
  "stopped_at": "2025-12-24T10:32:15.000Z",
  "status": "stopped",
  "video_file_path": "550e8400-e29b-41d4-a716-446655440000.webm",
  "video_duration_seconds": 135.0,
  "video_size_bytes": 12582912,
  "window_count": 270
}
```

**Video-Sensor Synchronization:**

Video timestamps are synchronized with sensor data using `session.created_at` as the anchor point:

```
session.created_at = "2025-12-24T10:30:00.000Z"  (t=0)
sensor_reading_at  = "2025-12-24T10:30:15.500Z"  (t=15.5s)
video.currentTime  = 15.5 seconds

Formula: videoTime = (sensorTimestamp - created_at) / 1000
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_HOST` | 0.0.0.0 | Server bind address |
| `SERVER_PORT` | 4100 | Server port |
| `DEBUG` | true | Debug mode |
| `SECRET_KEY` | dev-secret-key | Flask secret key |
| `QDRANT_HOST` | localhost | Qdrant host |
| `QDRANT_PORT` | 6333 | Qdrant port |
| `QDRANT_COLLECTION` | sensor_windows | Collection name |
| `VECTOR_DIMENSION` | 270 | Vector size |
| `WINDOW_SIZE_MS` | 500 | Time window duration |
| `ALLOWED_DEVICE_KEYS` | (empty) | Comma-separated device keys |
| `VIDEO_STORAGE_PATH` | ./data/videos | Directory for video files |
| `VIDEO_MAX_SIZE_MB` | 500 | Maximum video file size (MB) |
| `VIDEO_ALLOWED_FORMATS` | webm | Allowed video formats |

### Sample .env File

```bash
# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=4100
DEBUG=false
SECRET_KEY=your-production-secret-key-here

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=sensor_windows

# Video
VIDEO_STORAGE_PATH=./data/videos
VIDEO_MAX_SIZE_MB=500
VIDEO_ALLOWED_FORMATS=webm

# Security
ALLOWED_DEVICE_KEYS=firefighter_pi_001,firefighter_pi_002,firefighter_pi_003
```

---

## Testing

### Run All Tests

```bash
./run_tests.sh
```

### Individual Tests

```bash
# API endpoint tests
python tests/test_api.py

# Simulated Pi client (sends data for 30 seconds)
python tests/test_client.py --duration 30

# Full integration test
python tests/test_integration.py
```

### Test with Custom Server

```bash
python tests/test_api.py --server http://production-server:4100
python tests/test_client.py --server http://production-server:4100 --duration 60
```

---

## Troubleshooting

### Qdrant Connection Failed

**Error:** `Connection refused to localhost:6333`

**Solution:**
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# If not running, start it
docker start qdrant

# Or create new container
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### Socket.IO Connection Refused

**Error:** `Client cannot connect to server`

**Solution:**
1. Check server is running: `curl http://localhost:4100/health`
2. Check firewall allows port 4100
3. Verify CORS settings if connecting from browser

### No Windows Created

**Error:** `Session shows 0 windows after sending data`

**Cause:** Window size is 500ms. If data sent for less time, no complete windows.

**Solution:**
- Send data for at least 1 second
- Check server logs for "Stored window" messages

### Authentication Failed

**Error:** `auth_error: Invalid device key`

**Solution:**
1. Check `ALLOWED_DEVICE_KEYS` in `.env`
2. Empty value = accept all devices
3. Add your device key to the list

### High Memory Usage

**Cause:** Large number of active windows in memory

**Solution:**
1. Call `/api/sessions/:id/stop` to flush windows
2. Increase server RAM
3. Reduce `WINDOW_SIZE_MS` for smaller windows

---

## Support

For issues or questions:
1. Check this documentation
2. Review code comments
3. Check `todo.md` for known issues
4. Contact development team

---

**Document Version:** 1.0
**Last Updated:** December 1, 2025
