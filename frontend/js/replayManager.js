/**
 * @file replayManager.js
 * @description Replay playback control, preloading, and synchronization
 */

/**
 * Load next batch of windows for replay
 * @param {number} offset - Starting offset for batch
 * @returns {Promise<boolean>} Whether there are more windows to load
 */
async function loadWindowsBatch(offset) {
    if (!replaySessionId) return;

    try {
        const response = await fetch(`${SERVER_URL}/api/sessions/${replaySessionId}/replay?offset=${offset}&limit=${replayBatchSize}`);
        const data = await response.json();

        // Append new windows to replay buffer
        replayWindows.push(...data.windows);

        console.log(`Loaded batch: offset=${offset}, count=${data.windows.length}, total in buffer=${replayWindows.length}`);

        return data.has_more;
    } catch (error) {
        console.error('Failed to load window batch:', error);
        return false;
    }
}

/**
 * Handle replay control actions
 * @param {string} action - Control action: 'play', 'prev', 'next'
 */
function replayControl(action) {
    if (!replaySessionId) return;

    switch (action) {
        case 'play':
            if (isReplaying) {
                pauseReplay();
            } else {
                startReplay();
            }
            break;
        case 'prev':
            // Jump back one window
            if (replayCurrentWindowIndex > 0) {
                replayCurrentWindowIndex--;
                replayReadingIndex = 0;
                console.log(`Previous window: ${replayCurrentWindowIndex}`);
                syncVideoToCurrentPosition();
            }
            break;
        case 'next':
            // Jump forward one window
            if (replayCurrentWindowIndex < replayTotalWindows - 1) {
                replayCurrentWindowIndex++;
                replayReadingIndex = 0;
                console.log(`Next window: ${replayCurrentWindowIndex}`);
                checkPreload();
                syncVideoToCurrentPosition();
            }
            break;
    }
}

/**
 * Synchronize video to current replay position
 */
function syncVideoToCurrentPosition() {
    if (!replaySessionStartTime) return;

    const replayVideo = document.getElementById('replay-video');
    if (!replayVideo || !replayVideo.src) return;

    // Calculate current position in seconds from session start
    let estimatedSeconds = 0;
    if (replayStartTime) {
        const elapsedMs = Date.now() - replayStartTime;
        estimatedSeconds = Math.floor(elapsedMs / 1000);
        if (estimatedSeconds > replaySessionDuration) {
            estimatedSeconds = replaySessionDuration;
        }
    }

    // Seek video to this position
    replayVideo.currentTime = estimatedSeconds;
    console.log('[Video] Jumped to', estimatedSeconds, 'seconds');
}

/**
 * Start replay playback
 */
function startReplay() {
    if (replayWindows.length === 0) {
        alert('No replay data loaded');
        return;
    }

    // If replay has finished, restart from beginning
    if (replayCurrentWindowIndex >= replayTotalWindows) {
        replayCurrentWindowIndex = 0;
        replayReadingIndex = 0;
        replayWindows = []; // Clear buffer to reload from start

        // Reload first batch
        loadWindowsBatch(0).then(() => {
            console.log('Restarted replay from beginning');
        });

        // Reset time display
        document.getElementById('replayCurrentTime').textContent = '00:00';
    }

    isReplaying = true;
    document.getElementById('playPauseBtn').textContent = '⏸';

    // Show playhead during replay
    const playhead = document.getElementById('playhead');
    if (playhead) {
        playhead.classList.remove('hidden');
    }

    // Track replay start time (adjust for pause/resume continuity)
    replayStartTime = Date.now() - replayPausedElapsedTime;

    // Reset activity detector for fresh replay detection
    if (activityDetector) {
        activityDetector.reset();
    }

    // Play video if available
    const replayVideo = document.getElementById('replay-video');
    if (replayVideo && replayVideo.src) {
        replayVideo.play().catch(err => {
            console.warn('[Video] Playback failed:', err.message);
        });
    }

    // Start playback loop
    const baseInterval = CONFIG.REPLAY_BASE_INTERVAL_MS;
    const interval = baseInterval / replaySpeed;

    replayTimer = setInterval(() => {
        playNextReading();
    }, interval);

    console.log('Replay started');
}

/**
 * Pause replay playback
 */
function pauseReplay() {
    // Save elapsed time before pausing
    if (replayStartTime) {
        replayPausedElapsedTime = Date.now() - replayStartTime;
    }

    isReplaying = false;
    document.getElementById('playPauseBtn').textContent = '▶';

    // Hide playhead when paused
    const playhead = document.getElementById('playhead');
    if (playhead) {
        playhead.classList.add('hidden');
    }

    if (replayTimer) {
        clearInterval(replayTimer);
        replayTimer = null;
    }

    // Pause video if available
    const replayVideo = document.getElementById('replay-video');
    if (replayVideo && replayVideo.src) {
        replayVideo.pause();
    }

    // Clear activity detector state when pausing
    if (activityDetector) {
        activityDetector.reset();
    }
}

/**
 * Play next sensor reading from replay buffer
 * @returns {Promise<void>}
 */
async function playNextReading() {
    if (replayWindows.length === 0) {
        pauseReplay();
        return;
    }

    // Check if we've reached the end of the session duration
    if (replaySessionDuration > 0 && replayStartTime) {
        const elapsedMs = Date.now() - replayStartTime;
        const elapsedSeconds = elapsedMs / 1000;

        // Debug log every 2 seconds during playback
        if (!window.lastPlaybackLog || (elapsedSeconds - window.lastPlaybackLog) >= 2) {
            console.log('[Playback] Elapsed:', elapsedSeconds.toFixed(2) + 's of', replaySessionDuration + 's',
                '| Window:', replayCurrentWindowIndex, '/', replayTotalWindows,
                '| Reading:', replayReadingIndex);
            window.lastPlaybackLog = Math.floor(elapsedSeconds / 2) * 2;
        }

        if (elapsedSeconds >= replaySessionDuration) {
            updatePlayhead();
            pauseReplay();
            console.log('Replay finished - reached session duration of', replaySessionDuration, 'seconds');
            return;
        }
    }

    // Get current window (relative to loaded buffer)
    const windowIndexInBuffer = replayCurrentWindowIndex - (replayWindows.length > 0 ? 0 : 0);
    const currentWindow = replayWindows[windowIndexInBuffer];

    if (!currentWindow) {
        // No more windows with data, but keep playing to fill the time
        updatePlayhead();
        return;
    }

    // Check if it's time to play this window based on its timestamp
    if (currentWindow.start_time && replaySessionStartTime && replayStartTime) {
        const windowOffsetMs = currentWindow.start_time - replaySessionStartTime;
        const windowOffsetSec = windowOffsetMs / 1000;
        const elapsedMs = Date.now() - replayStartTime;
        const elapsedSec = elapsedMs / 1000;

        // Debug log window timing (only for first reading of each window)
        if (replayReadingIndex === 0) {
            console.log('[Window Timing] Window', replayCurrentWindowIndex + ':', {
                windowOffsetSec: windowOffsetSec.toFixed(2) + 's',
                elapsedSec: elapsedSec.toFixed(2) + 's',
                delta: (elapsedSec - windowOffsetSec).toFixed(2) + 's',
                shouldPlay: elapsedSec >= windowOffsetSec
            });
        }

        // If we haven't reached this window's time yet, skip it
        if (elapsedSec < windowOffsetSec) {
            updatePlayhead();
            return;
        }
    }

    // Parse raw_data if it exists
    let rawData;
    if (typeof currentWindow.raw_data === 'string') {
        try {
            rawData = JSON.parse(currentWindow.raw_data);
        } catch (e) {
            console.error('Failed to parse raw_data:', e);
            replayCurrentWindowIndex++;
            replayReadingIndex = 0;
            return;
        }
    } else {
        rawData = currentWindow.raw_data;
    }

    if (!rawData) {
        // No raw data, skip to next window
        replayCurrentWindowIndex++;
        replayReadingIndex = 0;
        return;
    }

    // Get sensor arrays
    const footReadings = rawData.foot || [];
    const accelReadings = rawData.accel || [];
    const maxReadings = Math.max(footReadings.length, accelReadings.length);

    // Check if we've reached end of current window
    if (replayReadingIndex >= maxReadings) {
        replayCurrentWindowIndex++;
        replayReadingIndex = 0;

        // Reset activity detector buffer when moving to new window
        if (activityDetector) {
            activityDetector.reset();
        }

        checkPreload();
        return;
    }

    // Display current reading
    if (replayReadingIndex < footReadings.length) {
        const footReading = footReadings[replayReadingIndex];
        updateFootDisplay(footReading);
    }

    if (replayReadingIndex < accelReadings.length) {
        const accelReading = accelReadings[replayReadingIndex];
        updateAccelDisplay(accelReading);
    }

    // Display stored activity label from window (only on first reading)
    if (replayReadingIndex === 0) {
        if (currentWindow.label) {
            updateActivityDisplay(currentWindow.label, 100);
            console.log('[Replay] Displaying stored label:', currentWindow.label, 'for window at',
                Math.floor((currentWindow.start_time - replaySessionStartTime) / 1000) + 's');
        } else {
            updateActivityDisplay('Unknown', 0);
            console.log('[Replay] No label stored for window at',
                Math.floor((currentWindow.start_time - replaySessionStartTime) / 1000) + 's');
        }
    }

    // Update playhead position
    updatePlayhead();

    // Advance to next reading
    replayReadingIndex++;
}

/**
 * Check if we need to preload more windows
 * @returns {Promise<void>}
 */
async function checkPreload() {
    const windowsAhead = replayWindows.length - replayCurrentWindowIndex;

    if (windowsAhead <= replayPreloadOffset && replayWindows.length < replayTotalWindows) {
        const nextOffset = replayWindows.length;
        console.log(`Preloading windows from offset ${nextOffset}`);
        await loadWindowsBatch(nextOffset);
    }
}

/**
 * Update playhead position on timeline
 */
function updatePlayhead() {
    if (replaySessionDuration === 0) {
        console.warn('[Playhead] replaySessionDuration is 0, cannot position playhead');
        return;
    }

    // Calculate elapsed time since replay started
    let estimatedSeconds = 0;
    if (replayStartTime) {
        const elapsedMs = Date.now() - replayStartTime;
        estimatedSeconds = Math.floor(elapsedMs / 1000);
        if (estimatedSeconds > replaySessionDuration) {
            estimatedSeconds = replaySessionDuration;
        }
    }

    // Calculate position as percentage - one block ahead of displayed time
    const percentage = ((estimatedSeconds + 1) / replaySessionDuration) * 100;

    // Debug logging - log every second
    if (!window.lastLoggedSecond || window.lastLoggedSecond !== estimatedSeconds) {
        console.log('[Playhead] Position:', percentage.toFixed(2) + '%', 'at', estimatedSeconds, 'seconds',
            '| Calculation:', estimatedSeconds, '/', replaySessionDuration, '=', percentage.toFixed(2) + '%',
            '| Expected at 50%:', (replaySessionDuration * 0.5).toFixed(1) + 's');
        window.lastLoggedSecond = estimatedSeconds;
    }

    // Update playhead element
    const playhead = document.getElementById('playhead');
    if (playhead) {
        playhead.style.left = `${percentage}%`;

        const timelineScroll = document.getElementById('timelineScroll');
        if (timelineScroll && (!window.lastLoggedPlayheadPosition || window.lastLoggedPlayheadPosition !== estimatedSeconds)) {
            const scrollWidth = timelineScroll.scrollWidth;
            const expectedPixels = (percentage / 100) * scrollWidth;
            console.log('[Playhead] DOM updated: style.left =', playhead.style.left,
                '| Timeline width:', scrollWidth + 'px',
                '| Expected position:', expectedPixels.toFixed(1) + 'px from left');
            window.lastLoggedPlayheadPosition = estimatedSeconds;
        }
    } else {
        console.warn('[Playhead] Element not found');
    }

    // Update time display
    const displaySeconds = estimatedSeconds + 1;
    const minutes = Math.floor(displaySeconds / 60);
    const seconds = displaySeconds % 60;
    const timeString = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

    const currentTimeEl = document.getElementById('replayCurrentTime');
    if (currentTimeEl) {
        currentTimeEl.textContent = timeString;
    }

    // Sync video playback only if there's a large drift
    const replayVideo = document.getElementById('replay-video');
    if (replayVideo && replayVideo.src && !replayVideo.paused) {
        const timeDiff = Math.abs(replayVideo.currentTime - estimatedSeconds);
        if (timeDiff > 2.0) {
            replayVideo.currentTime = estimatedSeconds;
            console.log('[Video] Large drift detected, synced to', estimatedSeconds, 'seconds');
        }
    }
}

/**
 * Simulate receiving sensor data (for testing without actual sensors)
 */
function simulateSensorData() {
    setInterval(() => {
        if (isRecording) {
            // Simulate foot data
            updateFootDisplay({
                data: {
                    foot: Math.random() > 0.5 ? 'LEFT' : 'RIGHT',
                    values: Array(18).fill(0).map(() => Math.random() * 100),
                    max: Math.random() * 100,
                    avg: Math.random() * 50
                }
            });

            // Simulate accel data
            updateAccelDisplay({
                data: {
                    acc: { x: (Math.random() - 0.5) * 2, y: (Math.random() - 0.5) * 2, z: 9.8 + Math.random() },
                    gyro: { x: Math.random() * 10, y: Math.random() * 10, z: Math.random() * 10 },
                    angle: { roll: Math.random() * 10, pitch: Math.random() * 10, yaw: Math.random() * 360 }
                }
            });
        }
    }, 100);
}
