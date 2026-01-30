# Deployment Guide

This guide explains how to deploy the firefighter activity recognition system for both local development and production use.

## System Architecture

```
                            FIELD (Firefighter)
┌─────────────────────────────────────────────────────────────────────┐
│  [Left Foot Pressure]  [Right Foot Pressure]  [IMU Accelerometer]   │
│           │                    │                    │               │
│           └────────────────────┼────────────────────┘               │
│                                │ Bluetooth BLE                      │
│                                ▼                                    │
│                     ┌──────────────────┐                            │
│                     │  RASPBERRY PI    │                            │
│                     │  (sensor-hub)    │                            │
│                     │  Python + BLE    │                            │
│                     └────────┬─────────┘                            │
│                              │ WiFi                                 │
└──────────────────────────────┼──────────────────────────────────────┘
                               │ Socket.IO (:4100/iot)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        SERVER                                       │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  firefighter-server (Flask + Socket.IO)  :4100             │    │
│  └───────────────────────────┬────────────────────────────────┘    │
│              ┌───────────────┼───────────────┐                      │
│              ▼               ▼               ▼                      │
│       ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│       │  Qdrant  │    │PostgreSQL│    │  Videos  │                 │
│       │  :6333   │    │  :5432   │    │  (disk)  │                 │
│       │ vectors  │    │ sessions │    │  .webm   │                 │
│       └──────────┘    └──────────┘    └──────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               │ Socket.IO + REST API
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BROWSER                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  record.html (frontend)                                     │    │
│  │  - Webcam + ml5.js MoveNet pose detection                  │    │
│  │  - Live sensor visualization                                │    │
│  │  - Video recording + upload                                 │    │
│  │  - Session management + replay                              │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **sensor-hub** | Raspberry Pi | Collects BLE sensor data, sends to server via Socket.IO |
| **firefighter-server** | Server | Flask API + Socket.IO, processes and stores data |
| **frontend** | Browser | Recording UI with webcam pose detection |
| **Qdrant** | Docker | Vector database for 270-dimensional sensor windows |
| **PostgreSQL** | Docker | Session metadata storage |

---

## Local Development Setup

Use this to test without real sensors.

### Step 1: Start Docker Containers

```bash
cd firefighter-server/docker

# Start databases
docker-compose up -d qdrant postgres

# Verify they're running
docker ps
# Should see: firefighter-qdrant (6333) and firefighter-postgres (5432)
```

### Step 2: Configure and Start Server

```bash
cd firefighter-server

# Copy example env (if not already done)
cp .env.example .env

# Install dependencies (first time only)
pip install -r requirements.txt

# Run server
python -m app.main

# Server now running at http://localhost:4100
```

### Step 3: Open Frontend

```bash
# Option A: Open directly
open frontend/record.html

# Option B: Serve via HTTP (recommended)
cd frontend
python -m http.server 8080
# Visit http://localhost:8080/record.html
```

### Step 4: Test Without Sensors

The frontend works without sensor data. You can:
- Start/stop recording sessions
- Use webcam for pose detection
- Record video

Sensor visualizations will show zeros until sensor-hub connects.

---

## Production Deployment

For real deployment with Raspberry Pi and sensors.

### Network Requirements

All devices must be on same network (or server must be accessible from Pi):

```
[Raspberry Pi] ──WiFi──► [Server :4100] ◄──WiFi/LAN── [Browser]
```

### Step 1: Server Setup

On your server machine (local computer, AWS EC2, DigitalOcean, etc.):

```bash
# Clone repo
git clone <repo-url>
cd fighter-man/firefighter-server

# Start Docker containers
cd docker
docker-compose up -d

# Configure environment
cd ..
cp .env.example .env
# Edit .env - for production, set:
#   DEBUG=false
#   SECRET_KEY=<generate-secure-key>

# Install dependencies
pip install -r requirements.txt

# Run server (use screen/tmux for persistence)
python -m app.main
```

**Note your server IP** (e.g., `192.168.1.100` or public IP if cloud)

### Step 2: Raspberry Pi Setup

SSH into your Raspberry Pi:

```bash
ssh pi@<raspberry-pi-ip>

# Install system dependencies
sudo apt update
sudo apt install python3-pip bluetooth bluez

# Clone repo
git clone <repo-url>
cd fighter-man/sensor-hub

# Install Python dependencies
pip3 install -r requirements.txt

# Find your sensors' MAC addresses
sudo python3 scanner.py
# Note the MAC addresses displayed

# Configure environment
cp .env.example .env
```

Edit `.env` on Raspberry Pi:

```bash
# Set your sensor MAC addresses (from scanner.py output)
LEFT_FOOT_MAC=XX:XX:XX:XX:XX:XX
RIGHT_FOOT_MAC=XX:XX:XX:XX:XX:XX
ACCELEROMETER_MAC=XX:XX:XX:XX:XX:XX

# IMPORTANT: Point to your server IP
SOCKETIO_SERVER_URL=http://192.168.1.100:4100

# Identify this device
SOCKETIO_DEVICE_KEY=firefighter_pi_001
```

Run sensor-hub:

```bash
# Run (use screen/tmux for persistence)
python3 main.py

# You should see:
# [Socket.IO] Connecting to http://192.168.1.100:4100...
# [Socket.IO] Connected successfully
# [PRIORITY] Connecting to left foot sensor...
```

### Step 3: Frontend Setup

On any computer that can reach the server:

Edit `frontend/js/config.js`:

```javascript
const CONFIG = {
    SERVER_URL: 'http://192.168.1.100:4100',  // Your server IP
    // ... rest of config
};
```

Open in browser:

```bash
cd frontend
python -m http.server 8080
# Visit http://localhost:8080/record.html
```

---

## Configuration Reference

### Server Configuration

File: `firefighter-server/.env`

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_PORT` | 4100 | HTTP/WebSocket port |
| `DEBUG` | true | Debug mode (set false in production) |
| `SECRET_KEY` | dev-key | Session secret (change in production) |
| `QDRANT_HOST` | localhost | Qdrant vector DB host |
| `QDRANT_PORT` | 6333 | Qdrant port |
| `POSTGRES_HOST` | localhost | PostgreSQL host |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `POSTGRES_PASSWORD` | dev_password | DB password |
| `ALLOWED_DEVICE_KEYS` | firefighter_pi_001 | Allowed sensor-hub device IDs (comma-separated) |

### Sensor Hub Configuration

File: `sensor-hub/.env`

| Variable | Default | Description |
|----------|---------|-------------|
| `LEFT_FOOT_MAC` | (required) | BLE MAC address of left foot sensor |
| `RIGHT_FOOT_MAC` | XX:XX:XX:XX:XX:XX | BLE MAC of right foot sensor (XX to skip) |
| `ACCELEROMETER_MAC` | XX:XX:XX:XX:XX:XX | BLE MAC of IMU sensor (XX to skip) |
| `SOCKETIO_SERVER_URL` | http://localhost:4100 | Server address |
| `SOCKETIO_DEVICE_KEY` | firefighter_pi_001 | Device identifier |
| `SOCKETIO_ENABLED` | true | Enable Socket.IO transmission |
| `FOOT_THROTTLE` | 2 | Process every Nth foot packet |
| `ACCEL_THROTTLE` | 5 | Process every Nth accelerometer packet |

### Frontend Configuration

File: `frontend/js/config.js`

```javascript
const CONFIG = {
    SERVER_URL: 'http://localhost:4100',  // Change for production
    // ...
};
```

---

## Ports Summary

| Service | Port | Protocol |
|---------|------|----------|
| Firefighter Server | 4100 | HTTP + WebSocket |
| Qdrant REST API | 6333 | HTTP |
| Qdrant gRPC | 6334 | gRPC |
| PostgreSQL | 5432 | TCP |
| Frontend (dev server) | 8080 | HTTP |

---

## Verification

### Check Server Health

```bash
curl http://localhost:4100/health
# Should return: {"status": "ok", ...}
```

### Check Qdrant

```bash
curl http://localhost:6333/collections
# Should list collections
```

### Check Sensor-Hub Connection

In server logs, look for:
```
[Socket.IO] Device firefighter_pi_001 connected
```

### Check Data Flow

In browser console:
```javascript
// Enable Socket.IO debug
localStorage.debug = 'socket.io-client:*';
// Refresh page, watch for foot_data and accel_data events
```

---

## Troubleshooting

### Sensor-Hub can't connect to server
- Verify server IP is correct in `sensor-hub/.env`
- Ensure port 4100 is open (check firewall)
- Verify `SOCKETIO_DEVICE_KEY` is in server's `ALLOWED_DEVICE_KEYS`

### BLE sensors won't connect
- Run `sudo python3 scanner.py` to find correct MAC addresses
- Ensure Bluetooth is enabled: `sudo systemctl start bluetooth`
- Reset Bluetooth adapter: `sudo hciconfig hci0 reset`
- Check sensors are powered on and in range

### Frontend shows no sensor data
- Check browser console for Socket.IO connection errors
- Verify `CONFIG.SERVER_URL` matches server address
- Check server logs for incoming sensor data

### Docker containers won't start
- Check Docker is running: `docker ps`
- Check ports are not in use: `lsof -i :6333` and `lsof -i :5432`
- View container logs: `docker logs firefighter-qdrant`

### Database connection errors
- Ensure PostgreSQL container is healthy: `docker ps`
- Check credentials match between server `.env` and Docker compose
- Try recreating containers: `docker-compose down && docker-compose up -d`
