/**
 * @file state.js
 * @description Centralized application state management
 */

// Recording state
let isRecording = false;
let currentSessionId = null;
let recordingStartTime = null;
let recordingTimer = null;
let footReadingCount = 0;
let accelReadingCount = 0;

// Sessions data
let sessions = [];

// Replay state
let replayWindows = [];           // Currently loaded windows with raw data
let replayWindowsMetadata = [];   // All windows metadata (lightweight)
let replayCurrentWindowIndex = 0; // Current window index
let replayReadingIndex = 0;       // Current reading within window
let replaySpeed = 1.0;            // Playback speed multiplier (1x default)
let replayPreloadOffset = CONFIG.REPLAY_PRELOAD_OFFSET;  // Preload when within N windows of end
let replayBatchSize = CONFIG.REPLAY_BATCH_SIZE;          // Windows per batch
let isReplaying = false;          // Playback active flag
let replayTimer = null;           // Interval timer for playback
let replaySessionId = null;       // Current replay session ID
let replayTotalWindows = 0;       // Total windows in session
let replaySessionDuration = 0;    // Total session duration in seconds
let replayStartTime = null;       // Timestamp when replay started
let replaySessionStartTime = null; // Session created_at timestamp in ms
let replayPausedElapsedTime = 0;  // Milliseconds elapsed before pause

// Activity detection
let activityDetector = null;

// Video recording
let videoRecorder = null;

// Pose visualization (p5.js based)
let poseSketch = null;

// Pose data collection
let lastPoseSentTime = 0;  // Timestamp of last pose data sent to server
