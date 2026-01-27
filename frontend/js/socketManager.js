/**
 * @file socketManager.js
 * @description Socket.IO connection management and event handlers
 */

/**
 * Update connection status indicator in the UI
 * @param {boolean} connected - Whether socket is connected
 */
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

/**
 * Throttled version of loadSessions to prevent rapid updates
 * Uses a lazy wrapper to defer loadSessions lookup until runtime
 * (loadSessions is defined in sessionManager.js which loads later)
 * @type {Function}
 */
const throttledLoadSessions = throttle(() => loadSessions(), 2000);

/**
 * Connect to Socket.IO server and set up event handlers
 */
function connectSocket() {
    // Connect to /iot namespace only
    const iotSocket = io(`${SERVER_URL}/iot`, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: CONFIG.SOCKET_RECONNECTION_ATTEMPTS,
        reconnectionDelay: CONFIG.SOCKET_RECONNECTION_DELAY_MS
    });

    iotSocket.on('connect', () => {
        updateConnectionStatus(true);
        console.log('[Socket.IO] Connected to /iot namespace');
    });

    iotSocket.on('disconnect', (reason) => {
        updateConnectionStatus(false);
        console.log('[Socket.IO] Disconnected:', reason);
    });

    iotSocket.on('connect_error', (error) => {
        console.error('[Socket.IO] Connection error:', error);
        updateConnectionStatus(false);
    });

    // Listen for session events (throttled to prevent rapid updates)
    iotSocket.on('session_started', (data) => {
        console.log('[Socket.IO] Session started:', data);
        throttledLoadSessions();
    });

    iotSocket.on('session_stopped', (data) => {
        console.log('[Socket.IO] Session stopped:', data);
        throttledLoadSessions();
    });

    // Listen for live sensor data (no logging - too frequent at 30Hz)
    iotSocket.on('foot_data', (data) => {
        updateFootDisplay(data);

        // Update activity detector with new foot data (ONLY during recording)
        if (activityDetector && isRecording) {
            activityDetector.updateFootData(data.data);

            // Trigger detection (if we also have accel data)
            const result = activityDetector.detectActivity();
            if (result.confidence > 0) {
                updateActivityDisplay(result.activity, result.confidence);
            }
        }
    });

    iotSocket.on('accel_data', (data) => {
        updateAccelDisplay(data);

        // Update activity detector and run detection (ONLY during recording)
        if (activityDetector && isRecording) {
            activityDetector.updateAccelData(data.data);

            // Trigger detection on every accel reading
            const result = activityDetector.detectActivity();
            updateActivityDisplay(result.activity, result.confidence);

            // Send detected activity to backend for window labeling
            if (currentSessionId && result.confidence > 0) {
                window.iotSocket.emit('activity_detected', {
                    session_id: currentSessionId,
                    activity: result.activity,
                    confidence: result.confidence,
                    timestamp: new Date().toISOString()
                });
            }
        }
    });

    // Store socket for later use
    window.iotSocket = iotSocket;
}
