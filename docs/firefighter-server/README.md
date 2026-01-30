# Firefighter Server

Flask backend server for the Firefighter Activity Recognition system. Receives sensor data via Socket.IO, processes it into vector embeddings, and provides REST APIs for session management, replay, and data export.

## Overview

The server acts as the central hub for:
- Receiving real-time sensor data from Raspberry Pi devices
- Broadcasting live data to connected browser clients
- Accumulating sensor readings into time-windowed vectors
- Storing vectors in Qdrant for similarity search
- Managing recording sessions in PostgreSQL
- Handling video uploads and streaming

## Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose (for Qdrant and PostgreSQL)

### 1. Start Infrastructure Services

```bash
cd firefighter-server/docker
docker-compose up -d
```

This starts:
- **Qdrant** (vector database) on ports 6333/6334
- **PostgreSQL** (session metadata) on port 5432

### 2. Set Up Python Environment

```bash
cd firefighter-server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment

Copy the example environment file and adjust as needed:

```bash
cp .env.example .env
```

Key environment variables:
- `SERVER_HOST` / `SERVER_PORT` - Server binding (default: 0.0.0.0:4100)
- `QDRANT_HOST` / `QDRANT_PORT` - Vector database connection
- `POSTGRES_*` - Database connection settings
- `DEVICE_KEYS` - Comma-separated list of authorized device keys

### 4. Run the Server

```bash
python server.py
```

The server will:
- Initialize connections to Qdrant and PostgreSQL
- Restore any active recording session from previous run
- Listen on port 4100 for HTTP and Socket.IO connections

## Project Structure

```
firefighter-server/
├── server.py              # Application entry point
├── app_state.py           # Shared application state (singleton)
├── routes/                # Flask Blueprints (modular endpoints)
│   ├── __init__.py        # Blueprint registration
│   ├── health.py          # Health check and activity types
│   ├── sessions.py        # Session CRUD operations
│   ├── export.py          # Data export (JSON/CSV)
│   ├── replay.py          # Replay data with pagination
│   ├── search.py          # Similarity search queries
│   ├── media.py           # Video upload and streaming
│   └── socket_handlers.py # Socket.IO event handlers
├── lib/
│   ├── config.py          # Configuration classes
│   ├── constants.py       # Application constants
│   ├── database.py        # PostgreSQL models and repository
│   └── vector_store.py    # Qdrant wrapper with windowing
├── docker/
│   └── docker-compose.yml # Qdrant + PostgreSQL setup
├── data/
│   ├── videos/            # Uploaded session videos
│   └── sessions/          # Session data exports
└── tests/
    └── realistic_activity_client.py  # Test data generator
```

## Key Concepts

### Recording Sessions

A session represents a single training recording. Sessions have:
- Unique UUID identifier
- Name (auto-generated or user-provided)
- Activity type (optional, for Stage 1 labeled data)
- Status: `recording` or `stopped`
- Video file (optional)

### Sensor Data Windows

Raw sensor data is accumulated into 500ms time windows:
- Each window contains up to 10 foot readings and 10 accelerometer readings
- Windows are converted to 270-dimensional vectors for storage
- Vector composition: 180 dims (foot) + 90 dims (accelerometer)

### Activity Labels

Supported activity types for Stage 1:
- Walking, Running, Crawling, Climbing
- Standing, Kneeling, Sitting
- Carrying, Hose_Operation, Idle

## Testing

### Send Test Data

Generate realistic sensor data without physical hardware:

```bash
source venv/bin/activate
python tests/realistic_activity_client.py --activity Standing --duration 300
```

### Run API Tests

```bash
pytest tests/
```

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Code structure and data flow
- [API.md](./API.md) - REST and Socket.IO API reference
