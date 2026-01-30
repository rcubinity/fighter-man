# Frontend Socket Events

This document describes the Socket.IO events used by the frontend to communicate with the firefighter-server.

## Connection

The frontend connects to the `/iot` namespace:

```javascript
const socket = io('http://localhost:4100/iot', {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000
});
```

## Events Received (Server to Frontend)

### `connect`

Fired when Socket.IO connection is established.

**Handler:**
```javascript
socket.on('connect', () => {
    updateConnectionStatus(true);
});
```

**UI Effect:** Connection indicator turns green.

---

### `disconnect`

Fired when Socket.IO connection is lost.

**Payload:** `reason` (string) - Disconnect reason

**Handler:**
```javascript
socket.on('disconnect', (reason) => {
    updateConnectionStatus(false);
});
```

**UI Effect:** Connection indicator turns gray.

---

### `foot_data`

Real-time foot pressure sensor data broadcast from server.

**Payload:**
```json
{
  "timestamp": "2025-01-30T14:30:22.100",
  "device": "LEFT_FOOT",
  "data": {
    "foot": "LEFT",
    "values": [1.2, 3.4, 5.6, ...],
    "max": 45.2,
    "avg": 12.3,
    "active_count": 12
  }
}
```

**Handler:**
```javascript
socket.on('foot_data', (data) => {
    // 1. Update sensor display
    updateFootDisplay(data);

    // 2. If recording: feed to activity detector
    if (activityDetector && isRecording) {
        activityDetector.updateFootData(data.data);
        const result = activityDetector.detectActivity();
        if (result.confidence > 0) {
            updateActivityDisplay(result.activity, result.confidence);
        }
    }
});
```

**UI Effect:**
- Updates 18 pressure bars for left or right foot
- Updates max/avg values
- Increments reading count during recording

---

### `accel_data`

Real-time accelerometer/IMU data broadcast from server.

**Payload:**
```json
{
  "timestamp": "2025-01-30T14:30:22.150",
  "device": "ACCELEROMETER",
  "data": {
    "acc": {"x": 0.1, "y": -0.2, "z": 9.8},
    "gyro": {"x": 1.2, "y": -0.5, "z": 0.3},
    "angle": {"roll": 2.1, "pitch": -1.3, "yaw": 45.2}
  }
}
```

**Handler:**
```javascript
socket.on('accel_data', (data) => {
    // 1. Update sensor display
    updateAccelDisplay(data);

    // 2. If recording: run activity detection
    if (activityDetector && isRecording) {
        activityDetector.updateAccelData(data.data);
        const result = activityDetector.detectActivity();
        updateActivityDisplay(result.activity, result.confidence);

        // 3. Send detected activity to server for labeling
        if (currentSessionId && result.confidence > 0) {
            socket.emit('activity_detected', {
                session_id: currentSessionId,
                activity: result.activity,
                confidence: result.confidence,
                timestamp: new Date().toISOString()
            });
        }
    }
});
```

**UI Effect:**
- Updates acceleration X/Y/Z values
- Updates gyroscope X/Y/Z values
- Updates angle roll/pitch/yaw values
- Triggers activity detection during recording

---

### `session_started`

Notification that a new recording session was created (by this or another client).

**Payload:**
```json
{
  "session_id": "uuid",
  "name": "Session Name",
  "activity_type": "Walking"
}
```

**Handler:**
```javascript
socket.on('session_started', (data) => {
    throttledLoadSessions();  // Refresh session list
});
```

**UI Effect:** Session list is refreshed to show new session.

---

### `session_stopped`

Notification that a recording session was stopped.

**Payload:**
```json
{
  "session_id": "uuid"
}
```

**Handler:**
```javascript
socket.on('session_stopped', (data) => {
    throttledLoadSessions();  // Refresh session list
});
```

**UI Effect:** Session list is refreshed to show updated status.

---

## Events Emitted (Frontend to Server)

### `activity_detected`

Sends detected activity from pose analysis to server for window labeling.

**Emitted when:** Accelerometer data is received during recording and activity detector has sufficient confidence.

**Payload:**
```json
{
  "session_id": "uuid",
  "activity": "Standing",
  "confidence": 85,
  "timestamp": "2025-01-30T14:30:22.000"
}
```

**Purpose:** The server uses this to label sensor data windows with the detected activity type.

---

## Connection Status Handling

The frontend tracks connection status and displays it in the header:

```javascript
function updateConnectionStatus(connected) {
    const status = document.getElementById('connectionStatus');
    if (connected) {
        status.innerHTML = `
            <span class="w-2 h-2 rounded-full bg-green-500"></span>
            <span class="text-green-500">Connected</span>
        `;
    } else {
        status.innerHTML = `
            <span class="w-2 h-2 rounded-full bg-gray-500"></span>
            <span class="text-gray-500">Disconnected</span>
        `;
    }
}
```

## Reconnection Behavior

Socket.IO is configured with automatic reconnection:

| Setting | Value | Description |
|---------|-------|-------------|
| `reconnection` | `true` | Enable auto-reconnection |
| `reconnectionAttempts` | 5 | Max retry attempts |
| `reconnectionDelay` | 1000ms | Initial delay between retries |

On reconnection failure, the connection indicator remains gray until manually refreshing the page.

## Event Throttling

Session list updates from `session_started` and `session_stopped` are throttled to prevent rapid UI refreshes:

```javascript
const throttledLoadSessions = throttle(() => loadSessions(), 2000);
```

This limits session list refreshes to at most once every 2 seconds.

## Data Rates

During active sensor monitoring:

| Event | Frequency | Data Size |
|-------|-----------|-----------|
| `foot_data` | ~30 Hz (per foot) | ~200 bytes |
| `accel_data` | ~20-30 Hz | ~150 bytes |

The frontend processes all events without throttling to maintain real-time display accuracy.
