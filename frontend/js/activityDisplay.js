/**
 * @file activityDisplay.js
 * @description Activity detection display including SVG icons and color mappings
 */

/**
 * Activity to SVG content mapping (embedded to avoid CORS issues)
 * @type {Object.<string, string>}
 */
const activitySvgMap = {
    'Sitting': `<svg width="220" height="200" viewBox="0 0 220 200" xmlns="http://www.w3.org/2000/svg">
        <!-- Head -->
        <circle cx="80" cy="30" r="16" fill="white" />
        <!-- Torso -->
        <rect x="70" y="46" width="30" height="65" rx="14" fill="white" />
        <!-- Arm resting -->
        <rect x="82" y="65" width="12" height="45" rx="6" fill="white" />
        <!-- Thigh (folded under body) -->
        <rect x="95" y="105" width="55" height="18" rx="9" fill="white" />
        <!-- Lower leg (bent backward) -->
        <rect x="130" y="115" width="18" height="50" rx="9" fill="white" />
        <!-- Foot -->
        <rect x="120" y="160" width="35" height="12" rx="6" fill="white" />
    </svg>`,
    'Standing': `<svg width="120" height="240" viewBox="0 0 120 240" xmlns="http://www.w3.org/2000/svg">
        <!-- Head -->
        <circle cx="60" cy="30" r="20" fill="white" />
        <!-- Body -->
        <rect x="40" y="55" width="40" height="90" rx="20" fill="white" />
        <!-- Left Arm -->
        <rect x="20" y="60" width="20" height="80" rx="10" fill="white" />
        <!-- Right Arm -->
        <rect x="80" y="60" width="20" height="80" rx="10" fill="white" />
        <!-- Left Leg -->
        <rect x="42" y="140" width="16" height="90" rx="8" fill="white" />
        <!-- Right Leg -->
        <rect x="62" y="140" width="16" height="90" rx="8" fill="white" />
    </svg>`
};

/**
 * Activity to color mapping for timeline segments
 * @type {Object.<string, string>}
 */
const activityColors = {
    'Sitting': '#22c55e',      // green-500
    'Standing': '#3b82f6',     // blue-500
    'Lying_Down': '#f59e0b',   // amber-500
    'Bent_Forward': '#8b5cf6', // violet-500
    'Jumping': '#ef4444'       // red-500
};

/**
 * Update the detected activity display
 * @param {string} activity - Detected activity name
 * @param {number} confidence - Confidence percentage (0-100)
 */
function updateActivityDisplay(activity, confidence) {
    if (!isRecording && !isReplaying) return;

    // Debug logging during replay (throttled to avoid spam)
    if (isReplaying) {
        if (!window.lastActivityLog || window.lastActivityLog !== activity) {
            // Get current replay time for context
            const elapsedMs = replayStartTime ? Date.now() - replayStartTime : 0;
            const elapsedSec = Math.floor(elapsedMs / 1000);
            console.log('[Activity Detection] At', elapsedSec + 's:', activity, '(' + confidence + '%)');
            window.lastActivityLog = activity;
        }
    }

    // Determine which state is active and get elements from correct container
    let activityLabelEl, confidenceEl, activityIconEl;

    if (isReplaying) {
        // Get elements from replay state (visible during replay)
        const replayState = document.getElementById('replayState');
        activityLabelEl = replayState?.querySelector('#activityLabel');
        confidenceEl = replayState?.querySelector('#activityConfidence');
        activityIconEl = replayState?.querySelector('#activityIcon');
    } else {
        // Get elements from recording state (visible during recording)
        const recordingState = document.getElementById('recordingState');
        activityLabelEl = recordingState?.querySelector('#activityLabel');
        confidenceEl = recordingState?.querySelector('#activityConfidence');
        activityIconEl = recordingState?.querySelector('#activityIcon');
    }

    if (activityLabelEl && confidenceEl) {
        activityLabelEl.textContent = activity;
        confidenceEl.textContent = `(${confidence}%)`;

        // Color coding based on confidence
        if (confidence >= 80) {
            activityLabelEl.className = 'text-green-400 font-semibold';
        } else if (confidence >= 60) {
            activityLabelEl.className = 'text-yellow-400 font-semibold';
        } else {
            activityLabelEl.className = 'text-orange-400 font-semibold';
        }
    }

    // Display SVG icon if available for this activity
    if (activityIconEl) {
        const svgContent = activitySvgMap[activity];
        if (svgContent) {
            // Display the embedded SVG
            activityIconEl.innerHTML = svgContent;
            activityIconEl.style.display = 'block';
            // Scale down the SVG
            const svgElement = activityIconEl.querySelector('svg');
            if (svgElement) {
                svgElement.style.width = '80px';
                svgElement.style.height = 'auto';
            }
        } else {
            // No SVG for this activity, hide the icon
            activityIconEl.style.display = 'none';
            activityIconEl.innerHTML = '';
        }
    }
}
