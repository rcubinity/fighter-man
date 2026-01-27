/**
 * @file recordingManager.js
 * @description Recording flow control including start, stop, timer, and UI updates
 */

/**
 * Check if there's an active session on the server and sync UI state
 * @returns {Promise<void>}
 */
async function checkActiveSession() {
    // Don't run if already recording
    if (isRecording) return;

    try {
        const response = await fetch(`${SERVER_URL}/api/sessions/active`);
        const session = await response.json();

        if (session && session.status === 'recording') {
            // Restore recording state from server
            currentSessionId = session.id;
            isRecording = true;
            recordingStartTime = new Date(session.created_at).getTime();
            updateRecordingUI(true, session.activity_type);
            startRecordingTimer();
            console.log('[Session] Restored active session:', session.id);
        }
    } catch (error) {
        console.error('Failed to check active session:', error);
    }
}

/**
 * Toggle recording state (start or stop)
 * @returns {Promise<void>}
 */
async function toggleRecording() {
    if (isRecording) {
        await stopRecording();
    } else {
        await startRecording();
    }
}

/**
 * Start a new recording session
 * @returns {Promise<void>}
 */
async function startRecording() {
    const sessionName = document.getElementById('sessionName').value;

    try {
        // Show video container first
        const videoContainer = document.getElementById('video-container');
        videoContainer.classList.remove('hidden');

        // Create p5.js pose sketch with camera and skeleton
        console.log('[Pose] Creating p5.js pose sketch...');
        poseSketch = createPoseSketch('video-container', {
            width: 640,
            height: 480,
            mirror: true,
            showSkeleton: true,
            showKeypoints: true,
            confidenceThreshold: 0.3
        });

        // Wait for the sketch to be ready and get the canvas stream
        console.log('[Video] Waiting for pose sketch canvas to be ready...');
        const canvasStream = await poseSketch.getCanvasStream();
        console.log('[Video] Got canvas stream with skeleton overlay');

        // Initialize video recorder with the canvas stream
        if (videoRecorder) {
            videoRecorder.stream = canvasStream;
            console.log('[Video] VideoRecorder stream set to canvas stream');
        }

        // Create session on server
        const response = await fetch(`${SERVER_URL}/api/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: sessionName || undefined
            })
        });

        if (!response.ok) {
            throw new Error('Failed to create session');
        }

        const session = await response.json();
        currentSessionId = session.id;
        isRecording = true;
        recordingStartTime = Date.now();
        footReadingCount = 0;
        accelReadingCount = 0;

        // Start video recording with canvas stream
        if (videoRecorder && videoRecorder.stream) {
            try {
                await videoRecorder.startRecording(session.id);
                console.log('[Video] Recording started with skeleton overlay');
            } catch (error) {
                console.warn('[Video] Failed to start recording:', error.message);
            }
        }

        // Reset activity detector
        if (activityDetector) {
            activityDetector.reset();
        }
        document.getElementById('activityLabel').textContent = 'Waiting...';
        document.getElementById('activityConfidence').textContent = '';

        // Update UI (show recording indicator)
        updateRecordingUI(true);
        startRecordingTimer();

        console.log('Recording started:', session);
    } catch (error) {
        console.error('Failed to start recording:', error);
        alert('Failed to start recording: ' + error.message);

        // Clean up on error
        if (poseSketch) {
            poseSketch.stop();
            poseSketch = null;
        }
    }
}

/**
 * Stop the current recording session
 * @returns {Promise<void>}
 */
async function stopRecording() {
    if (!currentSessionId) return;

    const sessionId = currentSessionId;

    try {
        // Stop server-side session
        const response = await fetch(`${SERVER_URL}/api/sessions/${sessionId}/stop`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to stop session');
        }

        isRecording = false;
        stopRecordingTimer();

        // Clear detection state
        if (activityDetector) {
            activityDetector.reset();
        }

        // Stop pose sketch (p5.js)
        if (poseSketch) {
            poseSketch.stop();
            poseSketch = null;
            console.log('[Pose] Pose sketch stopped');
        }

        updateRecordingUI(false);

        // Stop and upload video
        if (videoRecorder && videoRecorder.getState() === 'recording') {
            try {
                console.log('[Video] Stopping recording...');
                await videoRecorder.stopRecording();

                // Show upload progress UI
                const uploadProgress = document.getElementById('upload-progress');
                const uploadProgressBar = document.getElementById('video-upload-progress');
                const uploadStatus = document.getElementById('upload-status');
                uploadProgress.classList.remove('hidden');
                uploadStatus.textContent = 'Uploading video...';

                console.log('[Video] Uploading...');
                await videoRecorder.uploadVideoWithProgress(sessionId, (percent, loaded, total) => {
                    uploadProgressBar.value = percent;
                    uploadStatus.textContent = `Uploading video... ${percent.toFixed(1)}%`;
                });

                uploadStatus.textContent = 'Upload complete!';
                console.log('[Video] Upload successful');

                // Hide progress after 2 seconds
                setTimeout(() => {
                    uploadProgress.classList.add('hidden');
                    videoRecorder.destroy();
                }, 2000);

            } catch (error) {
                console.error('[Video] Upload failed:', error.message);
                const uploadStatus = document.getElementById('upload-status');
                uploadStatus.textContent = 'Upload failed: ' + error.message;
                // Allow user to see error message
                setTimeout(() => {
                    document.getElementById('upload-progress').classList.add('hidden');
                    if (videoRecorder) videoRecorder.destroy();
                }, 5000);
            }
        } else if (videoRecorder) {
            videoRecorder.destroy();
        }

        // Don't call loadSessions() here - socket event will handle it

        console.log('Recording stopped');
        currentSessionId = null;
    } catch (error) {
        console.error('Failed to stop recording:', error);
        alert('Failed to stop recording: ' + error.message);
    }
}

/**
 * Update recording UI state
 * @param {boolean} recording - Whether currently recording
 * @param {string} [activityType=''] - Selected activity type
 */
function updateRecordingUI(recording, activityType = '') {
    const btn = document.getElementById('recordBtn');
    const idleState = document.getElementById('idleState');
    const recordingState = document.getElementById('recordingState');
    const replayState = document.getElementById('replayState');
    const videoContainer = document.getElementById('video-container');
    const recordingIndicator = document.getElementById('recording-indicator');

    if (recording) {
        btn.innerHTML = `
            <span class="w-3 h-3 rounded bg-white"></span>
            <span>Stop Recording</span>
        `;
        btn.className = btn.className.replace('bg-red-600 hover:bg-red-700', 'bg-gray-600 hover:bg-gray-700');

        idleState.classList.add('hidden');
        replayState.classList.add('hidden');
        recordingState.classList.remove('hidden');
        document.getElementById('selectedActivity').textContent = activityType;

        // Show recording indicator (video container already shown by startRecording)
        recordingIndicator.classList.remove('hidden');
    } else {
        btn.innerHTML = `
            <span class="w-3 h-3 rounded-full bg-white"></span>
            <span>Start Recording</span>
        `;
        btn.className = btn.className.replace('bg-gray-600 hover:bg-gray-700', 'bg-red-600 hover:bg-red-700');

        idleState.classList.remove('hidden');
        recordingState.classList.add('hidden');
        replayState.classList.add('hidden');

        // Hide video preview and recording indicator
        videoContainer.classList.add('hidden');
        recordingIndicator.classList.add('hidden');
    }
}

/**
 * Start the recording duration timer
 */
function startRecordingTimer() {
    // Prevent multiple timers
    if (recordingTimer) {
        clearInterval(recordingTimer);
    }
    recordingTimer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
        const seconds = (elapsed % 60).toString().padStart(2, '0');
        document.getElementById('recordingDuration').textContent = `${minutes}:${seconds}`;
    }, CONFIG.RECORDING_TIMER_INTERVAL_MS);
}

/**
 * Stop the recording duration timer
 */
function stopRecordingTimer() {
    if (recordingTimer) {
        clearInterval(recordingTimer);
        recordingTimer = null;
    }
}
