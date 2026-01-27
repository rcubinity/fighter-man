# Fighter-Man: System Overview

A firefighter activity recognition system for training drills. Firefighters wear sensors during controlled exercises to collect data for AI model training.

---

## What Is This Project?

This system captures motion and pressure data from firefighters during training sessions to build machine learning models that can recognize activities like standing, sitting, walking, crawling, and more. The goal is to improve safety, training feedback, and fatigue detection for firefighters.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FIREFIGHTER IN TRAINING                       │
│     [Left Foot Sensor]  [Right Foot Sensor]  [Accelerometer]        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Bluetooth (BLE)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SENSOR-HUB (Raspberry Pi)                       │
│   • Reads BLE sensor data continuously                               │
│   • Buffers to SQLite for reliability                                │
│   • Transmits via Socket.IO                                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Socket.IO (/iot namespace)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   FIREFIGHTER-SERVER (Flask)                         │
│   • Receives sensor data in real-time                                │
│   • Windows into 500ms chunks → 270-dim vectors                      │
│   • Stores in Qdrant (vectors) + PostgreSQL (sessions)               │
│   • Serves REST API for frontend                                     │
│   • Broadcasts live data to connected browsers                       │
└────────────────────────┬────────────────────────────────────────────┘
                         │ Socket.IO + REST API
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Browser)                              │
│   • Shows live sensor data (foot pressure, accelerometer)            │
│   • Captures video with pose skeleton overlay                        │
│   • Detects activities in real-time                                  │
│   • Manages recording sessions                                       │
│   • Replays past sessions with timeline                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## The Three Components

### 1. sensor-hub (Raspberry Pi)

**Role:** Collects raw sensor data from wearables and transmits to server.

| Aspect | Details |
|--------|---------|
| **Location** | Raspberry Pi in the field |
| **Language** | Python 3.7+ |
| **Key Tech** | asyncio, bleak (BLE), python-socketio |
| **Database** | SQLite (local buffer for reliability) |

**What It Does:**
- Connects to 3 BLE sensors via Bluetooth
- Left foot pressure (18 sensors)
- Right foot pressure (18 sensors)
- WT901BLE67 accelerometer/IMU (acceleration, gyroscope, angles)
- Buffers data locally in SQLite
- Transmits real-time via Socket.IO
- Falls back to HTTP webhooks if connection fails

**Key Files:**
```
sensor-hub/
├── main.py                 # Entry point, orchestrates async monitoring
├── sensors/
│   ├── foot_sensor.py      # BLE foot pressure interface
│   └── accel_sensor.py     # BLE accelerometer interface
├── lib/
│   └── socket_client.py    # Socket.IO client
└── senders/                # Background retry logic
```

---

### 2. firefighter-server (Backend)

**Role:** Central backend that receives, processes, stores, and serves data.

| Aspect | Details |
|--------|---------|
| **Location** | Server (Docker or cloud) |
| **Language** | Python 3.11+ |
| **Key Tech** | Flask, Flask-SocketIO, SQLAlchemy |
| **Databases** | Qdrant (vectors), PostgreSQL (metadata) |

**What It Does:**
- Receives sensor data from sensor-hub via Socket.IO
- Accumulates readings into 500ms time windows
- Converts windows to 270-dimensional vectors for ML
- Stores vectors in Qdrant with similarity search capability
- Stores session metadata in PostgreSQL
- Handles video uploads and streaming
- Provides REST API for all frontend operations
- Broadcasts live sensor data to connected frontends

**Key Files:**
```
firefighter-server/
├── server.py               # Flask app with all endpoints
├── lib/
│   ├── vector_store.py     # Qdrant operations, windowing logic
│   ├── database.py         # PostgreSQL session management
│   └── config.py           # Configuration classes
└── tests/
    └── realistic_activity_client.py  # Test data generator
```

**Vector Format (270 dimensions):**
- 10 foot readings × 18 values = 180 dimensions
- 10 accel readings × 9 values = 90 dimensions
- Normalized to unit length

---

### 3. frontend (Browser UI)

**Role:** User interface for recording, viewing, and analyzing training sessions.

| Aspect | Details |
|--------|---------|
| **Location** | Web browser |
| **Language** | JavaScript (Vanilla ES6+) |
| **Key Tech** | p5.js, ml5.js (MoveNet), Socket.IO, Tailwind CSS |
| **Database** | None (stateless) |

**What It Does:**
- Create and manage recording sessions
- Display live camera feed with pose skeleton overlay
- Show real-time sensor visualizations (foot pressure bars, accel values)
- Perform client-side activity detection (Standing, Sitting, Lying, etc.)
- Record video with skeleton overlay
- Upload recorded video to server
- Replay past sessions with synchronized video and sensor timeline

**Key Files:**
```
frontend/
├── record.html             # Main single-page application
├── js/
│   ├── poseSketch.js       # p5.js camera + skeleton visualization
│   ├── activityDetector.js # Rule-based activity recognition
│   └── videoRecorder.js    # MediaRecorder wrapper
└── docs/                   # User guides
```

**Detected Activities:**
- Standing, Sitting, Lying_Down, Bent_Forward, Jumping

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| **BLE Communication** | bleak | Bluetooth sensor connectivity |
| **Edge Runtime** | Python asyncio | Concurrent sensor monitoring |
| **Real-time Transport** | Socket.IO | Bidirectional streaming |
| **Backend Framework** | Flask | REST API and WebSocket handling |
| **Vector Database** | Qdrant | 270-dim vector storage and similarity search |
| **Relational Database** | PostgreSQL | Session metadata and structured data |
| **Pose Detection** | ml5.js (MoveNet) | Real-time skeleton tracking |
| **Graphics** | p5.js | Canvas-based visualization |
| **Styling** | Tailwind CSS | Utility-first CSS framework |
| **Containerization** | Docker Compose | Multi-service deployment |

---

## Port Configuration

| Service | Port | Protocol |
|---------|------|----------|
| firefighter-server | 4100 | HTTP + Socket.IO |
| Qdrant REST | 6333 | HTTP |
| Qdrant gRPC | 6334 | gRPC |
| PostgreSQL | 5432 | TCP |
| sensor-hub | N/A | Outbound only |
| frontend | Any | Static files |

---

## Data Flow

### Recording Session

```
1. User creates session in frontend
2. Frontend connects to server via Socket.IO
3. Sensor-hub streams BLE data to server
4. Server broadcasts data to frontend (live display)
5. Server accumulates into 500ms windows
6. Windows converted to vectors, stored in Qdrant
7. Frontend records video with skeleton overlay
8. Video uploaded to server when session ends
```

### Replay Session

```
1. User selects past session in frontend
2. Frontend fetches session data from server REST API
3. Video streams with HTTP Range requests (seeking)
4. Sensor data synchronized with video playhead
5. Timeline shows activity segments color-coded
```

---

## Quick Reference

### Start the Server
```bash
cd firefighter-server
docker-compose up -d          # Start Qdrant + PostgreSQL
source venv/bin/activate
python server.py
```

### Send Test Data
```bash
cd firefighter-server
source venv/bin/activate
python tests/realistic_activity_client.py --activity Standing --duration 300
```

### Open Frontend
```bash
# Open in browser
open frontend/record.html
# Or serve via HTTP
cd frontend && python -m http.server 8080
```

---

## Further Reading

- [sensor-hub docs](../sensor-hub/docs/important_documents.md)
- [firefighter-server docs](../firefighter-server/docs/important_documents.md)
- [frontend docs](../frontend/docs/README.md)
- [API endpoints](../firefighter-server/docs/api_endpoints.md)
- [Project goals](../firefighter-server/docs/project_goals.md)
