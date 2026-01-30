# Sensor Hub Architecture

This document describes the internal architecture of the sensor-hub component, including the BLE communication model, data pipeline, and key design patterns.

## Code Organization

The sensor hub was recently refactored to extract common BLE logic into a base class, reducing code duplication between foot and accelerometer sensors.

### Entry Point: `main.py`

The main module orchestrates:
1. Loading configuration from environment
2. Initializing SQLite databases
3. Establishing Socket.IO connection
4. Creating sensor instances
5. Running concurrent monitoring loops

```python
async def main():
    config = Config.from_env()

    # Initialize databases
    init_databases(config.database)

    # Initialize Socket.IO
    init_socket(config.socket)

    # Create sensors with staggered connections
    left_foot = FootSensor(config.ble.left_foot_mac, "LEFT_FOOT", ...)
    tasks.append(asyncio.create_task(left_foot.monitor_loop()))
    await asyncio.sleep(3)  # Stagger to avoid BLE stack overload

    right_foot = FootSensor(config.ble.right_foot_mac, "RIGHT_FOOT", ...)
    # ... similar for accelerometer

    await asyncio.gather(*tasks)
```

### Sensors Directory: `sensors/`

The sensor implementation follows an inheritance hierarchy:

```
BLESensorBase (abstract)
    ├── FootSensor
    └── AccelSensor
```

#### `ble_sensor_base.py`

Abstract base class providing common BLE operations:

```python
class BLESensorBase(ABC):
    def __init__(self, mac_address, device_name, data_callback, throttle, max_retries):
        self.mac = mac_address
        self.name = device_name
        self.data_callback = data_callback
        self.throttle = throttle
        self.max_retries = max_retries

    @abstractmethod
    def _notification_handler(self, sender, raw_data):
        """Parse incoming BLE data (sensor-specific)"""
        pass

    @abstractmethod
    async def _start_notifications(self):
        """Enable BLE notifications (sensor-specific)"""
        pass

    async def connect(self):
        """Scan, connect, retry on failure"""

    async def start_monitoring(self):
        """Begin receiving notifications"""

    async def stop_monitoring(self):
        """Clean disconnect"""

    async def monitor_loop(self, duration=None):
        """Main loop: connect + monitor until stopped"""
```

#### `foot_sensor.py`

Foot sensor implementation (text protocol):

```python
class FootSensor(BLESensorBase):
    def _notification_handler(self, sender, raw_data):
        # Decode UTF-8 text
        # Buffer until newline
        # Parse comma-separated values
        # Call data_callback with formatted output

    async def _start_notifications(self):
        # Enable notifications on FOOT_NOTIFY_UUID
        # Send 'begin' command
```

#### `accel_sensor.py`

Accelerometer implementation (binary protocol):

```python
class AccelSensor(BLESensorBase):
    def _notification_handler(self, sender, raw_data):
        # Buffer binary data
        # Extract 20-byte packets
        # Parse binary format
        # Call data_callback with formatted output

    async def _start_notifications(self):
        # Discover UUIDs (device variants exist)
        # Enable notifications
        # Start keep-alive task
```

#### `constants.py`

All BLE-related constants:

| Constant | Value | Purpose |
|----------|-------|---------|
| `BLE_SCAN_TIMEOUT` | 10.0s | Time to scan for device |
| `BLE_CONNECT_TIMEOUT` | 15.0s | Connection establishment timeout |
| `BLE_RETRY_DELAY` | 3.0s | Delay between retry attempts |
| `ACCEL_PACKET_SIZE` | 20 bytes | Accelerometer packet size |
| `ACCEL_KEEPALIVE_INTERVAL` | 1.0s | Keep-alive frequency |

## Data Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      BLE Sensor Device                          │
│                 (Foot Pressure / Accelerometer)                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │ BLE Notifications
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BLESensorBase._notification_handler()        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  1. Buffer incoming bytes                               │   │
│   │  2. Check throttle (skip if packet_count % throttle)    │   │
│   │  3. Parse protocol-specific format                      │   │
│   │  4. Create output dict with timestamp                   │   │
│   │  5. Call data_callback (async)                          │   │
│   └─────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Handler (main.py)                       │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  handle_foot_data() / handle_accel_data()               │   │
│   │    1. Save to SQLite database (backup)                  │   │
│   │    2. Emit via Socket.IO (if connected)                 │   │
│   │    3. Print to stdout (debug logging)                   │   │
│   └─────────────────────────────────────────────────────────┘   │
└───────────────┬───────────────────────────────┬─────────────────┘
                │                               │
                ▼                               ▼
┌───────────────────────────┐   ┌────────────────────────────────┐
│     SQLite Database       │   │      Socket.IO Client          │
│  (FootDatabase /          │   │  (SocketIOClient)              │
│   AccelDatabase)          │   │                                │
│                           │   │  Emits to /iot namespace:      │
│  Stores raw records       │   │  - foot_pressure_data          │
│  for retry/backup         │   │  - accelerometer_data          │
└───────────────────────────┘   └────────────────────────────────┘
```

## Connection State Machine

Each sensor follows this connection lifecycle:

```
┌─────────┐
│  INIT   │
└────┬────┘
     │ connect()
     ▼
┌─────────────┐     Device not found     ┌─────────────┐
│  SCANNING   │─────────────────────────▶│   RETRY     │
└──────┬──────┘                          └──────┬──────┘
       │ Device found                           │ retry < max_retries
       ▼                                        │
┌─────────────┐                                 │
│ CONNECTING  │◀────────────────────────────────┘
└──────┬──────┘
       │ Connected
       ▼
┌─────────────┐
│ STABILIZING │ (200ms wait)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  CONNECTED  │
└──────┬──────┘
       │ start_monitoring()
       ▼
┌─────────────┐
│ MONITORING  │◀────────┐
└──────┬──────┘         │
       │                │ still connected
       │ monitor_loop() │
       └────────────────┘
       │
       │ disconnect or error
       ▼
┌─────────────┐
│  STOPPED    │
└─────────────┘
```

## Throttling

Sensors can generate data faster than needed. Throttling reduces load:

```python
self.packet_count += 1
if self.packet_count % self.throttle != 0:
    return  # Skip this packet

# Process packet
```

| Sensor | Default Throttle | Input Rate | Output Rate |
|--------|------------------|------------|-------------|
| Foot | 1 (none) | ~30 Hz | ~30 Hz |
| Accel | 5 | ~100 Hz | ~20 Hz |

## Concurrent Monitoring

The `asyncio` library enables monitoring multiple sensors simultaneously:

```python
# Create tasks (non-blocking)
tasks = [
    asyncio.create_task(left_foot.monitor_loop()),
    asyncio.create_task(right_foot.monitor_loop()),
    asyncio.create_task(accelerometer.monitor_loop()),
]

# Wait for all (blocks until Ctrl+C or error)
await asyncio.gather(*tasks)
```

Staggered starts (3-second delays) prevent BLE stack contention:

```python
# Start left foot
tasks.append(asyncio.create_task(left_foot.monitor_loop()))
await asyncio.sleep(3)

# Then right foot
tasks.append(asyncio.create_task(right_foot.monitor_loop()))
await asyncio.sleep(3)

# Then accelerometer
tasks.append(asyncio.create_task(accelerometer.monitor_loop()))
```

## Socket.IO Client

The `SocketIOClient` class wraps python-socketio:

```python
class SocketIOClient:
    def __init__(self, server_url, device_key, namespace):
        self.sio = socketio.Client()
        self.server_url = server_url
        self.device_key = device_key
        self.namespace = namespace

    def connect(self):
        self.sio.connect(self.server_url, namespaces=[self.namespace])
        self.sio.emit('authenticate', {'device_key': self.device_key})

    def emit(self, event, data):
        self.sio.emit(event, data, namespace=self.namespace)
```

Events emitted:
- `authenticate` - On connection, with device key
- `foot_pressure_data` - Each foot reading
- `accelerometer_data` - Each accel reading

## SQLite Storage

Local SQLite databases provide backup storage:

```python
class FootDatabase:
    def save_record(self, data):
        # INSERT INTO foot_readings (timestamp, device, data_json)

    def get_unsent(self, limit=100):
        # SELECT * FROM foot_readings WHERE sent = 0

    def mark_sent(self, ids):
        # UPDATE foot_readings SET sent = 1 WHERE id IN (...)
```

Database files:
- `data/foot_data.db` - Foot pressure readings
- `data/accel_data.db` - Accelerometer readings

## Configuration Classes

Configuration is loaded from environment via dataclasses:

```python
@dataclass
class BLEConfig:
    left_foot_mac: str
    right_foot_mac: Optional[str]
    accelerometer_mac: Optional[str]
    foot_throttle: int
    accel_throttle: int
    connection_retries: int

@dataclass
class SocketConfig:
    enabled: bool
    server_url: str
    device_key: str
    namespace: str

@dataclass
class Config:
    ble: BLEConfig
    socket: SocketConfig
    database: DatabaseConfig

    @classmethod
    def from_env(cls):
        # Load from os.environ
```

## Error Handling

### Connection Failures

Each sensor retries connection up to `max_retries` times:

```python
for attempt in range(1, self.max_retries + 1):
    try:
        device = await BleakScanner.find_device_by_address(self.mac)
        if not device:
            if attempt < self.max_retries:
                await asyncio.sleep(BLE_RETRY_DELAY)
                continue
            return False
        # ... connect
    except Exception as e:
        if attempt < self.max_retries:
            await asyncio.sleep(BLE_RETRY_DELAY)
        else:
            return False
```

### Runtime Errors

Notification handler errors are caught to prevent crashing:

```python
def _notification_handler(self, sender, raw_data):
    try:
        # Parse data
    except Exception as e:
        print(f"[{self.name}] Notification error: {e}")
        # Continue receiving
```

### Graceful Shutdown

Ctrl+C triggers cleanup:

```python
async def cleanup_tasks(tasks, socket_client):
    for task in tasks:
        if not task.done():
            task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    if socket_client:
        socket_client.disconnect()
```

## Extensibility

To add a new sensor type:

1. Create `sensors/new_sensor.py` extending `BLESensorBase`
2. Implement `_notification_handler()` for protocol parsing
3. Implement `_start_notifications()` for BLE setup
4. Add MAC address config in `lib/config.py`
5. Instantiate in `main.py` with appropriate handler
