# Firefighter Activity Recognition - Data Pipeline

Data collection system for training an AI model that recognizes firefighter activities using wearable sensor data.

## Projects

| Folder             | Description                                                             |
| ------------------ | ----------------------------------------------------------------------- |
| sensor-hub         | Raspberry Pi - collects BLE sensor data (foot pressure + accelerometer) |
| firefighter-server | Flask server - stores data in Qdrant (vectors) + PostgreSQL (metadata)  |
| frontend           | Browser UI - recording, replay, live visualization, pose detection      |

## Quick Start

### Firefighter Server

```bash
# 1. Start Docker services (Qdrant + PostgreSQL)
cd firefighter-server/docker
docker-compose up -d

# 2. Start the server (in a new terminal)
cd firefighter-server
source venv/bin/activate
python server.py
```

### Send Test Data (in a new terminal)

```bash
cd firefighter-server

# Activate virtual environment
source venv/bin/activate

# Send test data (300 seconds of Standing activity)
python tests/realistic_activity_client.py --activity Standing --duration 300
```

## Quick Commands (Copy & Paste)

**Start Docker services (required first):**
```bash
cd '/Users/apple/Herd/neuronso/fighter-man/firefighter-server/docker' && docker-compose up -d
```

**Start the server (requires Docker services running):**
```bash
cd '/Users/apple/Herd/neuronso/fighter-man/firefighter-server' && source venv/bin/activate && python server.py
```

**Send test data:**
```bash
cd '/Users/apple/Herd/neuronso/fighter-man/firefighter-server' && source venv/bin/activate && python tests/realistic_activity_client.py --activity Standing --duration 300
```

## Quick Links

- **[System Overview](./docs/SYSTEM_OVERVIEW.md)** - Start here! Architecture, components, and how they work together
- [sensor-hub docs](./docs/sensor-hub/important_documents.md)
- [firefighter-server docs](./docs/firefighter-server/important_documents.md)
- [frontend docs](./docs/frontend/README.md)
