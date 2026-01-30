/**
 * @file initLoader.js
 * @description Loading screen initialization logic
 * Handles sequential initialization of camera, ML5 model, socket, and sessions
 */

const InitLoader = {
    // Pre-loaded resources
    preloadedCamera: null,
    preloadedBodyPose: null,
    preloadedPoseSketch: null,

    // Track errors for "Continue Anyway" button
    hasErrors: false,

    /**
     * Update a step's state in the loading UI
     * @param {string} stepId - Step element ID (e.g., 'step-camera')
     * @param {string} state - State: 'pending', 'loading', 'success', 'error'
     * @param {string} statusText - Status text to display
     */
    updateStep(stepId, state, statusText) {
        const step = document.getElementById(stepId);
        if (!step) return;

        // Remove all state classes
        step.classList.remove('pending', 'loading', 'success', 'error');
        // Add new state
        step.classList.add(state);

        // Update status text
        const statusEl = step.querySelector('.step-status');
        if (statusEl) {
            statusEl.textContent = statusText;
        }
    },

    /**
     * Initialize camera access
     * @returns {Promise<MediaStream|null>}
     */
    async initCamera() {
        this.updateStep('step-camera', 'loading', 'Requesting permission...');

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                },
                audio: false
            });

            this.preloadedCamera = stream;
            this.updateStep('step-camera', 'success', 'Camera ready');
            console.log('[InitLoader] Camera initialized successfully');
            return stream;
        } catch (err) {
            console.warn('[InitLoader] Camera access failed:', err.message);
            this.updateStep('step-camera', 'error', err.name === 'NotAllowedError' ? 'Permission denied' : err.message);
            this.hasErrors = true;
            return null;
        }
    },

    /**
     * Initialize ML5 MoveNet pose detection model
     * @returns {Promise<object|null>}
     */
    async initML5Model() {
        this.updateStep('step-ml5', 'loading', 'Loading MoveNet model...');

        return new Promise((resolve) => {
            const timeout = setTimeout(() => {
                console.warn('[InitLoader] ML5 model load timeout');
                this.updateStep('step-ml5', 'error', 'Load timeout');
                this.hasErrors = true;
                resolve(null);
            }, CONFIG.ML5_MODEL_TIMEOUT_MS);

            try {
                // Load the model without video - we'll attach video later
                const bodyPose = ml5.bodyPose('MoveNet', () => {
                    clearTimeout(timeout);
                    this.preloadedBodyPose = bodyPose;
                    this.updateStep('step-ml5', 'success', 'Model loaded');
                    console.log('[InitLoader] ML5 MoveNet model loaded successfully');
                    resolve(bodyPose);
                });
            } catch (err) {
                clearTimeout(timeout);
                console.warn('[InitLoader] ML5 model load failed:', err.message);
                this.updateStep('step-ml5', 'error', err.message);
                this.hasErrors = true;
                resolve(null);
            }
        });
    },

    /**
     * Initialize Socket.IO connection
     * @returns {Promise<object|null>}
     */
    async initSocket() {
        this.updateStep('step-socket', 'loading', 'Connecting to server...');

        return new Promise((resolve) => {
            const timeout = setTimeout(() => {
                console.warn('[InitLoader] Socket connection timeout');
                this.updateStep('step-socket', 'error', 'Connection timeout');
                this.hasErrors = true;
                resolve(null);
            }, CONFIG.SOCKET_CONNECT_TIMEOUT_MS);

            try {
                const iotSocket = io(`${SERVER_URL}/iot`, {
                    transports: ['websocket', 'polling'],
                    reconnection: true,
                    reconnectionAttempts: CONFIG.SOCKET_RECONNECTION_ATTEMPTS,
                    reconnectionDelay: CONFIG.SOCKET_RECONNECTION_DELAY_MS
                });

                iotSocket.on('connect', () => {
                    clearTimeout(timeout);
                    this.updateStep('step-socket', 'success', 'Connected');
                    console.log('[InitLoader] Socket connected to /iot namespace');

                    // Set up remaining socket handlers (from socketManager.js)
                    this.setupSocketHandlers(iotSocket);

                    // Store socket for later use
                    window.iotSocket = iotSocket;
                    resolve(iotSocket);
                });

                iotSocket.on('connect_error', (error) => {
                    clearTimeout(timeout);
                    console.warn('[InitLoader] Socket connection error:', error.message);
                    this.updateStep('step-socket', 'error', 'Connection failed');
                    this.hasErrors = true;

                    // Still store socket for potential reconnection
                    window.iotSocket = iotSocket;
                    resolve(null);
                });
            } catch (err) {
                clearTimeout(timeout);
                console.warn('[InitLoader] Socket initialization failed:', err.message);
                this.updateStep('step-socket', 'error', err.message);
                this.hasErrors = true;
                resolve(null);
            }
        });
    },

    /**
     * Set up socket event handlers
     * @param {object} iotSocket - Socket.IO socket instance
     */
    setupSocketHandlers(iotSocket) {
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

        // Listen for live sensor data
        iotSocket.on('foot_data', (data) => {
            updateFootDisplay(data);

            if (activityDetector && isRecording) {
                activityDetector.updateFootData(data.data);
                const result = activityDetector.detectActivity();
                if (result.confidence > 0) {
                    updateActivityDisplay(result.activity, result.confidence);
                }
            }
        });

        iotSocket.on('accel_data', (data) => {
            updateAccelDisplay(data);

            if (activityDetector && isRecording) {
                activityDetector.updateAccelData(data.data);
                const result = activityDetector.detectActivity();
                updateActivityDisplay(result.activity, result.confidence);

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
    },

    /**
     * Initialize the pose sketch (camera + ML5 in p5.js canvas)
     * This pre-warms everything so recording starts instantly
     * @returns {Promise<object|null>}
     */
    async initPoseSketch() {
        // Update steps - camera first since it's at the top
        this.updateStep('step-camera', 'loading', 'Requesting permission...');
        this.updateStep('step-ml5', 'pending', 'Waiting...');
        this.updateStep('step-video', 'pending', 'Waiting...');

        return new Promise((resolve) => {
            // Temporarily show mainApp (needed for p5.js to create canvas properly)
            // It will be hidden behind the loading screen anyway
            const mainApp = document.getElementById('mainApp');
            mainApp.classList.remove('hidden');
            mainApp.style.visibility = 'hidden';

            // Show video container (hidden visually but needs to exist for p5)
            const videoContainer = document.getElementById('video-container');
            videoContainer.classList.remove('hidden');
            videoContainer.style.visibility = 'hidden';
            videoContainer.style.position = 'absolute';
            videoContainer.style.left = '-9999px';

            console.log('[InitLoader] Creating pose sketch...');

            try {
                this.preloadedPoseSketch = createPoseSketch('video-container', {
                    width: 640,
                    height: 480,
                    mirror: true,
                    showSkeleton: true,
                    showKeypoints: true,
                    confidenceThreshold: 0.3,
                    // Callbacks for status updates
                    onCameraReady: () => {
                        this.updateStep('step-camera', 'success', 'Camera ready');
                        this.updateStep('step-ml5', 'loading', 'Loading MoveNet...');
                    },
                    onCameraError: (err) => {
                        this.updateStep('step-camera', 'error', err || 'Camera failed');
                    },
                    onModelReady: () => {
                        this.updateStep('step-ml5', 'success', 'Model loaded');
                        this.updateStep('step-video', 'loading', 'Starting pose detection...');
                    },
                    onModelError: (err) => {
                        this.updateStep('step-ml5', 'error', err || 'Model failed');
                    },
                    onReady: () => {
                        this.updateStep('step-video', 'success', 'Video ready');
                    }
                });

                // Wait for sketch to be ready
                const checkReady = (attempts = 0) => {
                    if (poseSketchReady) {
                        this.updateStep('step-video', 'success', 'Video ready');
                        console.log('[InitLoader] Pose sketch ready');
                        resolve(this.preloadedPoseSketch);
                    } else if (attempts < 500) { // 50 seconds max (includes user permission time)
                        setTimeout(() => checkReady(attempts + 1), 100);
                    } else {
                        console.warn('[InitLoader] Pose sketch timeout');
                        this.updateStep('step-video', 'error', 'Video timeout');
                        this.hasErrors = true;
                        resolve(null);
                    }
                };

                checkReady();
            } catch (err) {
                console.error('[InitLoader] Failed to create pose sketch:', err);
                this.updateStep('step-camera', 'error', err.message);
                this.updateStep('step-video', 'error', err.message);
                this.hasErrors = true;
                resolve(null);
            }
        });
    },

    /**
     * Load sessions from API
     * @returns {Promise<Array|null>}
     */
    async initSessions() {
        this.updateStep('step-sessions', 'loading', 'Fetching sessions...');

        try {
            const response = await fetch(`${SERVER_URL}/api/sessions`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            sessions = await response.json();
            renderSessions();

            this.updateStep('step-sessions', 'success', `${sessions.length} session(s) loaded`);
            console.log('[InitLoader] Sessions loaded:', sessions.length);
            return sessions;
        } catch (err) {
            console.warn('[InitLoader] Failed to load sessions:', err.message);
            this.updateStep('step-sessions', 'error', err.message);
            this.hasErrors = true;
            return null;
        }
    },

    /**
     * Transition from loading screen to main app
     */
    showMainApp() {
        const loadingScreen = document.getElementById('loadingScreen');
        const mainApp = document.getElementById('mainApp');

        // Ensure video container is hidden but kept in DOM
        const videoContainer = document.getElementById('video-container');
        if (videoContainer) {
            videoContainer.classList.add('hidden');
            videoContainer.style.visibility = 'hidden';
            videoContainer.style.position = 'absolute';
            videoContainer.style.left = '-9999px';
        }

        // Fade out loading screen
        loadingScreen.classList.add('fade-out');

        // Show main app (reset visibility that was set during initPoseSketch)
        mainApp.classList.remove('hidden');
        mainApp.style.visibility = 'visible';

        // Remove loading screen from DOM after transition
        setTimeout(() => {
            loadingScreen.style.display = 'none';
        }, 500);

        // Update connection status based on socket state
        if (window.iotSocket && window.iotSocket.connected) {
            updateConnectionStatus(true);
        } else {
            updateConnectionStatus(false);
        }

        console.log('[InitLoader] Main app revealed');
    },

    /**
     * Run the full initialization sequence
     */
    async run() {
        console.log('[InitLoader] Starting initialization sequence...');

        // Initialize foot sensor bars (sync operation)
        initFootBars();

        // Initialize activity detector
        activityDetector = new ActivityDetector();

        // Initialize video recorder if supported
        if (VideoRecorder.isSupported()) {
            videoRecorder = new VideoRecorder();
            console.log('[InitLoader] VideoRecorder initialized');
        } else {
            console.warn('[InitLoader] Video recording not supported in this browser');
        }

        // Step 1: Initialize Pose Sketch (camera + ML5 + canvas all in one)
        // This handles camera permission and ML5 model loading together
        await this.initPoseSketch();

        // Step 2: Socket Connection
        await this.initSocket();

        // Step 3: Load Sessions
        await this.initSessions();

        // Check for active session
        checkActiveSession();

        // Show "Continue Anyway" button if there were errors
        if (this.hasErrors) {
            const btn = document.getElementById('continueAnywayBtn');
            if (btn) {
                btn.classList.remove('hidden');
            }
            console.log('[InitLoader] Initialization completed with errors - showing continue button');
        } else {
            // All successful - wait 1s then transition to main app
            console.log('[InitLoader] Initialization completed successfully, showing app in 1s...');
            setTimeout(() => {
                this.showMainApp();
            }, 1000);
        }
    }
};
