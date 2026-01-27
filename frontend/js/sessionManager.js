/**
 * @file sessionManager.js
 * @description Session CRUD operations and list management
 */

/**
 * Load sessions from API
 * @returns {Promise<void>}
 */
async function loadSessions() {
    try {
        const response = await fetch(`${SERVER_URL}/api/sessions`);
        sessions = await response.json();
        renderSessions();
    } catch (error) {
        console.error('Failed to load sessions:', error);
    }
}

/**
 * Render sessions list in the sidebar
 */
function renderSessions() {
    const list = document.getElementById('sessionsList');

    if (sessions.length === 0) {
        list.innerHTML = '<div class="p-4 text-gray-500 text-sm">No sessions yet</div>';
        return;
    }

    list.innerHTML = sessions.map(s => `
        <div class="session-item px-4 py-3 hover:bg-gray-900 transition-colors">
            <div class="flex items-center justify-between mb-1">
                <span class="font-medium text-sm cursor-pointer flex-1 truncate mr-2" onclick="selectSession('${s.id}')">${s.name || 'Unnamed'}</span>
                <div class="flex items-center gap-1 flex-shrink-0">
                    <button onclick="event.stopPropagation(); renameSession('${s.id}', '${s.name.replace(/'/g, "\\'")}');"
                            class="text-xs px-1.5 py-1 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 flex-shrink-0 whitespace-nowrap"
                            title="Rename session">
                        ✏️
                    </button>
                    <button onclick="event.stopPropagation(); deleteSession('${s.id}', '${s.name.replace(/'/g, "\\'")}');"
                            class="text-xs px-1.5 py-1 bg-red-900 hover:bg-red-800 rounded text-red-300 flex-shrink-0 whitespace-nowrap"
                            title="Delete session">
                        🗑️
                    </button>
                    <span class="text-xs px-2 py-1 rounded flex-shrink-0 ${s.status === 'recording' ? 'bg-red-900 text-red-300' : 'bg-gray-700 text-gray-400'}">
                        ${s.status}
                    </span>
                </div>
            </div>
            <div class="flex items-center gap-2 text-xs text-gray-500 cursor-pointer" onclick="selectSession('${s.id}')">
                ${s.activity_type ? `<span class="bg-blue-900 text-blue-300 px-1.5 py-0.5 rounded">${s.activity_type}</span>` : ''}
                <span>${new Date(s.created_at).toLocaleTimeString()}</span>
            </div>
        </div>
    `).join('');
}

/**
 * Rename a session
 * @param {string} sessionId - Session ID to rename
 * @param {string} currentName - Current session name
 * @returns {Promise<void>}
 */
async function renameSession(sessionId, currentName) {
    const newName = prompt('Enter new name for session:', currentName);
    if (!newName || newName === currentName) return;

    try {
        const response = await fetch(`${SERVER_URL}/api/sessions/${sessionId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName })
        });

        if (!response.ok) {
            throw new Error('Failed to rename session');
        }

        // Refresh session list
        await loadSessions();

        // Update replay state if this is the current session
        if (replaySessionId === sessionId) {
            document.getElementById('replaySession').textContent = newName;
        }

        console.log('Session renamed successfully');
    } catch (error) {
        console.error('Failed to rename session:', error);
        alert('Failed to rename session');
    }
}

/**
 * Delete a session and all its data
 * @param {string} sessionId - Session ID to delete
 * @param {string} sessionName - Session name for confirmation dialog
 * @returns {Promise<void>}
 */
async function deleteSession(sessionId, sessionName) {
    if (!confirm(`Are you sure you want to delete "${sessionName}"?\n\nThis will permanently delete all recorded data.`)) {
        return;
    }

    try {
        const response = await fetch(`${SERVER_URL}/api/sessions/${sessionId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete session');
        }

        const result = await response.json();
        console.log(`Session deleted: ${result.windows_deleted} windows removed`);

        // Stop replay if this session is being replayed
        if (replaySessionId === sessionId) {
            pauseReplay();
            replaySessionId = null;
            replayWindows = [];
            document.getElementById('replayState').classList.add('hidden');
            document.getElementById('idleState').classList.remove('hidden');
        }

        // Refresh session list
        await loadSessions();

        alert(`Session deleted successfully (${result.windows_deleted} windows removed)`);
    } catch (error) {
        console.error('Failed to delete session:', error);
        alert('Failed to delete session');
    }
}

/**
 * Select a session for replay
 * @param {string} sessionId - Session ID to select
 * @returns {Promise<void>}
 */
async function selectSession(sessionId) {
    if (isRecording) {
        alert('Stop recording before selecting a session');
        return;
    }

    // Stop any active replay before switching sessions
    if (isReplaying) {
        pauseReplay();
    }

    try {
        // Load first batch of windows with raw data for replay
        const replayResponse = await fetch(`${SERVER_URL}/api/sessions/${sessionId}/replay?offset=0&limit=${replayBatchSize}`);
        const replayData = await replayResponse.json();

        // Load ALL windows metadata (without raw_data) for timeline rendering
        const metadataResponse = await fetch(`${SERVER_URL}/api/sessions/${sessionId}/windows`);
        const allWindowsMetadata = await metadataResponse.json();

        // Initialize replay state
        replaySessionId = sessionId;
        replayWindows = replayData.windows || [];
        replayTotalWindows = replayData.total_windows || 0;
        replayCurrentWindowIndex = 0;
        replayReadingIndex = 0;
        replayStartTime = null;
        replayPausedElapsedTime = 0;

        // Reset activity detector and display for new session
        if (activityDetector) {
            activityDetector.reset();
        }

        // Reset activity display to "Waiting..." for replay
        const replayState = document.getElementById('replayState');
        if (replayState) {
            const activityLabelEl = replayState.querySelector('#activityLabel');
            const confidenceEl = replayState.querySelector('#activityConfidence');
            if (activityLabelEl && confidenceEl) {
                activityLabelEl.textContent = 'Waiting...';
                activityLabelEl.className = 'text-gray-400';
                confidenceEl.textContent = '';
            }
        }

        // Calculate actual recording duration
        let totalSeconds = 0;

        // Try using session timestamps first (recording start to stop)
        if (replayData.session.created_at && replayData.session.stopped_at) {
            const startTime = new Date(replayData.session.created_at);
            const stopTime = new Date(replayData.session.stopped_at);
            const sessionDuration = Math.floor((stopTime - startTime) / 1000);

            console.log('[Duration Calculation] Session timestamps:', {
                created_at: replayData.session.created_at,
                stopped_at: replayData.session.stopped_at,
                startTime: startTime.toISOString(),
                stopTime: stopTime.toISOString(),
                calculatedDuration: sessionDuration + 's'
            });

            // Sanity check: if session was left open for more than 2 hours, use window span instead
            const MAX_REASONABLE_DURATION = 2 * 60 * 60; // 2 hours in seconds

            if (sessionDuration <= MAX_REASONABLE_DURATION) {
                totalSeconds = sessionDuration;
                console.log('[Duration Calculation] Using session timestamp duration:', totalSeconds + 's');
            } else {
                console.warn('[Replay] Session duration exceeds 2 hours, using window span instead');
                if (allWindowsMetadata.length > 0) {
                    const firstWindow = allWindowsMetadata[0];
                    const lastWindow = allWindowsMetadata[allWindowsMetadata.length - 1];
                    if (firstWindow.start_time && lastWindow.end_time) {
                        const duration_ms = lastWindow.end_time - firstWindow.start_time;
                        totalSeconds = Math.ceil(duration_ms / 1000);
                        console.log('[Duration Calculation] Using window span duration:', totalSeconds + 's');
                    }
                }
            }
        } else if (allWindowsMetadata.length > 0) {
            const firstWindow = allWindowsMetadata[0];
            const lastWindow = allWindowsMetadata[allWindowsMetadata.length - 1];
            if (firstWindow.start_time && lastWindow.end_time) {
                const duration_ms = lastWindow.end_time - firstWindow.start_time;
                totalSeconds = Math.ceil(duration_ms / 1000);
                console.log('[Duration Calculation] Using window span (no session timestamps):', totalSeconds + 's');
            } else {
                totalSeconds = Math.floor(replayTotalWindows * 0.5);
                console.log('[Duration Calculation] Fallback to window count estimate:', totalSeconds + 's');
            }
        } else {
            totalSeconds = Math.floor(replayTotalWindows * 0.5);
            console.log('[Duration Calculation] Fallback to window count estimate (no windows):', totalSeconds + 's');
        }

        // Store for use in playback
        replaySessionDuration = totalSeconds;

        // Store session start time for timestamp-based playback
        if (replayData.session.created_at) {
            replaySessionStartTime = new Date(replayData.session.created_at).getTime();
            console.log('[Duration Calculation] Session start time:', replaySessionStartTime, '(' + new Date(replaySessionStartTime).toISOString() + ')');
        }

        console.log('[Session Load] FINAL VALUES:');
        console.log('  - replaySessionDuration:', replaySessionDuration, 'seconds');
        console.log('  - replaySessionStartTime:', replaySessionStartTime, '(' + new Date(replaySessionStartTime).toISOString() + ')');
        console.log('  - Total windows:', replayTotalWindows);
        console.log('  - Metadata windows:', allWindowsMetadata.length);

        const totalMinutes = Math.floor(totalSeconds / 60);
        const totalSecs = totalSeconds % 60;
        document.getElementById('replayTotalTime').textContent =
            `${String(totalMinutes).padStart(2, '0')}:${String(totalSecs).padStart(2, '0')}`;
        document.getElementById('replayCurrentTime').textContent = '00:00';

        // Update UI - remove active class from all sessions
        document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));

        // Show replay state
        document.getElementById('idleState').classList.add('hidden');
        document.getElementById('recordingState').classList.add('hidden');
        document.getElementById('replayState').classList.remove('hidden');
        document.getElementById('selectedActivity').textContent = replayData.session.activity_type || '-';

        // Load video if available
        const replayVideoContainer = document.getElementById('replay-video-container');
        const replayNoVideo = document.getElementById('replay-no-video');
        const replayVideo = document.getElementById('replay-video');

        // Populate session name
        const sessionDisplayName = replayData.session.activity_type ?
            `${replayData.session.name} - ${replayData.session.activity_type}` :
            replayData.session.name;
        document.getElementById('replaySessionName').textContent = sessionDisplayName;

        if (replayData.session.video_file_path) {
            replayVideo.src = `${SERVER_URL}/api/sessions/${sessionId}/video`;
            replayVideoContainer.classList.remove('hidden');
            replayNoVideo.classList.add('hidden');
            console.log('[Video] Loaded video for replay:', replayData.session.video_file_path);
        } else {
            replayVideo.src = '';
            replayVideoContainer.classList.add('hidden');
            replayNoVideo.classList.remove('hidden');
            console.log('[Video] No video available for this session');
        }

        // Update timeline with session data and ALL windows metadata
        updateTimeline({
            ...replayData.session,
            windows: allWindowsMetadata
        });

        console.log(`Loaded session: ${replayWindows.length} windows for replay (${replayTotalWindows} total), ${allWindowsMetadata.length} windows for timeline`);
    } catch (error) {
        console.error('Failed to load session:', error);
        alert('Failed to load session for replay');
    }
}
