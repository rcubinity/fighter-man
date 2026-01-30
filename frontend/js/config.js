/**
 * @file config.js
 * @description Application configuration constants
 */

const CONFIG = {
    // Server
    SERVER_URL: 'http://localhost:4100',

    // Camera & ML5
    CAMERA_TIMEOUT_MS: 30000,  // 30s to allow user time to grant permission
    ML5_MODEL_TIMEOUT_MS: 15000,  // 15s for model loading

    // Video Recording
    VIDEO_MAX_SIZE_MB: 500,

    // Replay
    REPLAY_BATCH_SIZE: 20,
    REPLAY_PRELOAD_OFFSET: 10,
    REPLAY_BASE_INTERVAL_MS: 100,

    // Recording
    RECORDING_TIMER_INTERVAL_MS: 1000,

    // Pose Data
    POSE_SEND_INTERVAL_MS: 500,  // Send pose data every 500ms to match sensor windows

    // Socket.IO
    SOCKET_RECONNECTION_ATTEMPTS: 5,
    SOCKET_RECONNECTION_DELAY_MS: 1000,
    SOCKET_CONNECT_TIMEOUT_MS: 10000,
};

// Backward compatibility - keep SERVER_URL working as standalone variable
const SERVER_URL = CONFIG.SERVER_URL;
