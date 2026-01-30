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
        // Show video container (pre-loaded during init)
        const videoContainer = document.getElementById('video-container');
        videoContainer.classList.remove('hidden');
        videoContainer.style.visibility = 'visible';
        videoContainer.style.position = 'relative';
        videoContainer.style.left = '0';

        // Use the pre-loaded pose sketch from InitLoader
        if (InitLoader.preloadedPoseSketch) {
            poseSketch = InitLoader.preloadedPoseSketch;
            console.log('[Pose] Using pre-loaded pose sketch');
        } else {
            // Fallback: create new sketch if not pre-loaded
            console.log('[Pose] Creating new pose sketch (fallback)...');
            poseSketch = createPoseSketch('video-container', {
                width: 640,
                height: 480,
                mirror: true,
                showSkeleton: true,
                showKeypoints: true,
                confidenceThreshold: 0.3
            });
        }

        // Get the canvas stream (should be ready immediately if pre-loaded)
        console.log('[Video] Getting pose sketch canvas stream...');
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

        // Clear session name input after successful start
        document.getElementById('sessionName').value = '';

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
        // Stop server-side session with retry logic
        let response;
        let lastError;
        for (let attempt = 1; attempt <= 3; attempt++) {
            try {
                response = await fetch(`${SERVER_URL}/api/sessions/${sessionId}/stop`, {
                    method: 'POST'
                });
                if (response.ok) break;
                lastError = new Error(`HTTP ${response.status}`);
            } catch (fetchError) {
                lastError = fetchError;
                console.warn(`[Recording] Stop attempt ${attempt} failed:`, fetchError.message);
                if (attempt < 3) {
                    await new Promise(resolve => setTimeout(resolve, 500)); // Wait 500ms before retry
                }
            }
        }

        if (!response || !response.ok) {
            throw lastError || new Error('Failed to stop session after retries');
        }

        isRecording = false;
        stopRecordingTimer();

        // Clear detection state
        if (activityDetector) {
            activityDetector.reset();
        }

        // Don't stop pose sketch - keep it running for next recording
        // Just hide the video container
        const videoContainer = document.getElementById('video-container');
        videoContainer.style.visibility = 'hidden';
        videoContainer.style.position = 'absolute';
        videoContainer.style.left = '-9999px';
        console.log('[Pose] Pose sketch hidden (kept alive for next recording)');

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

        // Show video container and recording indicator
        videoContainer.classList.remove('hidden');
        videoContainer.style.visibility = 'visible';
        videoContainer.style.position = 'relative';
        videoContainer.style.left = '0';
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

        // Hide video preview (keep it in DOM for reuse) and recording indicator
        videoContainer.style.visibility = 'hidden';
        videoContainer.style.position = 'absolute';
        videoContainer.style.left = '-9999px';
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
