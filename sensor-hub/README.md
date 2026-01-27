# Sensor Hub

BLE sensor monitoring system for Raspberry Pi. Collects data from foot pressure sensors and accelerometer IMU, stores locally in SQLite, and broadcasts via Socket.IO.

## Quick Start

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Find sensor MAC addresses
python3 scanner.py

# Configure .env with MAC addresses
cp .env.example .env
nano .env

# Run
python3 main.py
```

## Structure

```
sensor-hub/
├── main.py              # Entry point - monitors all sensors
├── scanner.py           # BLE device discovery utility
├── sensors/             # BLE sensor interfaces
│   ├── foot_sensor.py   # Foot pressure sensor
│   ├── accel_sensor.py  # Accelerometer IMU (WT901BLE67)
│   ├── parsers.py       # Data parsing functions
│   └── constants.py     # BLE timeouts and UUIDs
├── lib/                 # Shared utilities
│   ├── config.py        # Configuration management
│   ├── socket_client.py # Socket.IO client
│   └── database/        # SQLite backup layer
├── senders/             # Background data transmission
│   ├── base.py          # Base sender with retry logic
│   ├── foot_sender.py   # Foot data sender
│   └── accel_sender.py  # Accelerometer sender
├── tests/               # Test scripts
├── .env.example         # Configuration template
└── requirements.txt     # Python dependencies
```

## Documentation

See [docs/sensor-hub/](../docs/sensor-hub/) for detailed documentation:
- `important_documents.md` - Full developer guide
- `ARCHITECTURE.md` - System architecture
- `DATA_DICTIONARY.md` - Data formats
- `SENSOR_SPECIFICATIONS.md` - Hardware specs
