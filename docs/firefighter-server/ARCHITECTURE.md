# Firefighter Server Architecture

This document describes the internal architecture of the firefighter-server component, including code organization, data flow, and key design decisions.

## Code Organization

The server was recently refactored from a monolithic `server.py` into modular Flask Blueprints for better maintainability and testability.

### Entry Point: `server.py`

The main entry point initializes all components:

```python
# Flask app with CORS and Socket.IO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Initialize shared state
AppState.init(config)

# Register blueprints and handlers
register_blueprints(app)
register_socket_handlers(socketio)
```

### Shared State: `app_state.py`

The `AppState` class provides singleton access to shared resources:

```python
class AppState:
    vector_store: VectorStore = None      # Qdrant client
    db: Database = None                    # PostgreSQL connection
    session_repo: SessionRepository = None # Session operations
    current_session_id: str = None         # Active recording session
    detected_activities: Dict = {}         # Frontend activity detections
    config = None                          # Application configuration
```

This pattern replaces global variables and makes dependencies explicit.

### Routes Directory: `routes/`

Each Blueprint handles a specific domain:

| Blueprint | File | URL Prefix | Purpose |
|-----------|------|------------|---------|
| `health_bp` | `health.py` | `/` | Health checks, activity types |
| `sessions_bp` | `sessions.py` | `/api` | Session CRUD |
| `export_bp` | `export.py` | `/api` | Data export |
| `replay_bp` | `replay.py` | `/api` | Replay data fetching |
| `search_bp` | `search.py` | `/api` | Similarity queries |
| `media_bp` | `media.py` | `/api` | Video upload/streaming |

Socket.IO handlers are in `socket_handlers.py` and registered separately.

### Library Directory: `lib/`

Core business logic and infrastructure:

| Module | Purpose |
|--------|---------|
| `config.py` | Configuration dataclasses with env parsing |
| `constants.py` | Magic numbers and configuration values |
| `database.py` | SQLAlchemy models and repository pattern |
| `vector_store.py` | Qdrant operations with windowing logic |

## Data Flow

### Recording Flow

```
                                    ┌─────────────────┐
                                    │   Raspberry Pi   │
                                    │   (sensor-hub)   │
                                    └────────┬────────┘
                                             │ Socket.IO
                                             │ foot_pressure_data
                                             │ accelerometer_data
                                             ▼
┌────────────────────────────────────────────────────────────────┐
│                      socket_handlers.py                        │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ handle_foot_data() / handle_accel_data()                 │ │
│  │   1. Broadcast to UI clients (socketio.emit)             │ │
│  │   2. Get activity label from AppState                    │ │
│  │   3. Add reading to VectorStore                          │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────┐
│                       vector_store.py                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ add_reading()                                             │ │
│  │   1. Parse timestamp                                      │ │
│  │   2. Get/create active window for session                 │ │
│  │   3. Add reading to window (foot or accel list)           │ │
│  │   4. Check if 500ms elapsed                               │ │
│  │   5. If complete: _store_window() → Qdrant               │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │     Qdrant      │
                                    │  270-dim vector │
                                    │   + payload     │
                                    └─────────────────┘
```

### Vector Composition

Each window is converted to a 270-dimensional vector:

```
┌──────────────────────────────────────────────────────────────┐
│                    270-Dimensional Vector                     │
├─────────────────────────────────┬────────────────────────────┤
│     Foot Segment (180 dims)     │   Accel Segment (90 dims)  │
├─────────────────────────────────┼────────────────────────────┤
│ 10 readings × 18 values/reading │ 10 readings × 9 values     │
│ (pressure sensors × readings)   │ (acc, gyro, angle × 3 axes)│
└─────────────────────────────────┴────────────────────────────┘
```

Each sensor reading contributes:
- **Foot**: 18 pressure sensor values
- **Accel**: 9 values (acc_xyz, gyro_xyz, roll/pitch/yaw)

### Replay Flow

```
┌─────────────┐     GET /api/sessions/{id}/replay      ┌─────────────┐
│   Browser   │ ──────────────────────────────────────▶│   replay.py │
│  (frontend) │                                        └──────┬──────┘
│             │                                               │
│             │     GET /api/sessions/{id}/windows            │
│             │ ──────────────────────────────────────▶ (metadata only)
│             │                                               │
│             │     GET /api/sessions/{id}/video              │
│             │ ──────────────────────────────────────▶│   media.py  │
│             │◀────────────── (HTTP Range streaming) ───────┘
└─────────────┘
```

The replay endpoint returns paginated windows with raw sensor data for playback. The windows endpoint returns lightweight metadata for timeline rendering.

## Database Schema

### PostgreSQL: `sessions` Table

```sql
CREATE TABLE sessions (
    id              VARCHAR(36) PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    activity_type   VARCHAR(50),
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    stopped_at      TIMESTAMP WITH TIME ZONE,
    status          VARCHAR(20) NOT NULL DEFAULT 'recording',
    updated_at      TIMESTAMP WITH TIME ZONE,
    video_file_path TEXT,
    video_duration_seconds FLOAT,
    video_size_bytes INTEGER
);

-- Indexes for common queries
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_activity_type ON sessions(activity_type);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
```

### Qdrant: `sensor_windows` Collection

Each point in the collection has:
- **Vector**: 270 floats (normalized)
- **Payload**:
  - `session_id`: UUID string
  - `device`: Device identifier
  - `start_time`: Window start (ms timestamp)
  - `end_time`: Window end (ms timestamp)
  - `foot_count`: Number of foot readings
  - `accel_count`: Number of accel readings
  - `label`: Activity label (optional)
  - `raw_data`: JSON string of original readings

## Configuration

Configuration is loaded from environment variables via dataclasses in `lib/config.py`:

```python
@dataclass
class ServerConfig:
    host: str
    port: int
    debug: bool
    secret_key: str

@dataclass
class QdrantConfig:
    host: str
    port: int
    collection: str
    vector_dimension: int  # 270
    window_size_ms: int    # 500

@dataclass
class PostgresConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
```

## Constants

All magic numbers are centralized in `lib/constants.py`:

| Constant | Value | Purpose |
|----------|-------|---------|
| `SOCKETIO_NAMESPACE` | `/iot` | Socket.IO namespace for devices |
| `FOOT_SENSOR_VALUES` | 18 | Pressure sensors per foot |
| `ACCEL_SENSOR_VALUES` | 9 | Values per accel reading |
| `MAX_READINGS_PER_WINDOW` | 10 | Readings per 500ms window |
| `TOTAL_VECTOR_DIM` | 270 | Vector dimension for Qdrant |
| `DEFAULT_WINDOW_SIZE_MS` | 500 | Time window duration |

## Error Handling

Each Blueprint handles errors consistently:

```python
@sessions_bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(session.to_dict())
```

## Threading Model

The server uses Flask-SocketIO with `async_mode="threading"`:
- Development-friendly and stable
- Each Socket.IO connection handled in its own thread
- For high-concurrency production, switch to `gevent` or `eventlet`

## Extensibility

To add new functionality:

1. **New endpoint**: Create a Blueprint in `routes/`, register in `__init__.py`
2. **New Socket event**: Add handler in `socket_handlers.py`
3. **New constant**: Add to `lib/constants.py`
4. **New config**: Add dataclass field in `lib/config.py`
