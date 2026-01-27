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
cd firefighter-server

# 1. Starting docker
docker-compose up -d

# 2. Activate virtual environment
source venv/bin/activate

# 3. Start the server
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

**Start the server:**
```bash
cd '/Users/apple/Herd/neuronso/fighter-man/firefighter-server' && source venv/bin/activate && python server.py
```

**Send test data:**
```bash
cd '/Users/apple/Herd/neuronso/fighter-man/firefighter-server' && source venv/bin/activate && python tests/realistic_activity_client.py --activity Standing --duration 300
```

## Quick Links

- **[System Overview](./docs/SYSTEM_OVERVIEW.md)** - Start here! Architecture, components, and how they work together
- [sensor-hub docs](./sensor-hub/docs/important_documents.md)
- [firefighter-server docs](./firefighter-server/docs/important_documents.md)
- [frontend docs](./frontend/docs/README.md)
