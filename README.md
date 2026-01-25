# Firefighter Activity Recognition - Data Pipeline

Data collection system for training an AI model that recognizes firefighter activities using wearable sensor data.

## Projects

| Folder             | Description                                                             |
| ------------------ | ----------------------------------------------------------------------- |
| sensor-hub         | Raspberry Pi - collects BLE sensor data (foot pressure + accelerometer) |
| firefighter-server | Server - stores data using Qdrant vector database                       |

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

## Quick Links

- [sensor-hub docs](./sensor-hub/docs/important_documents.md)
- [firefighter-server docs](./firefighter-server/docs/important_documents.md)
