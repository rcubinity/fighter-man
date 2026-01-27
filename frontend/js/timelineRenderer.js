/**
 * @file timelineRenderer.js
 * @description Timeline UI rendering including segments, markers, and playhead
 */

/**
 * Group consecutive windows with same label into activity segments
 *
 * CRITICAL FIXES (2025-12-20):
 * 1. Timeline segments now use replaySessionStartTime as reference point
 * 2. Timeline duration now uses replaySessionDuration
 * 3. This ensures timeline segments align perfectly with playhead position
 *
 * @param {Array} windows - Array of window objects with label, start_time, end_time
 * @returns {Array} Array of segments: [{label, start_time, end_time}, ...]
 */
function groupActivitySegments(windows) {
    if (!windows || windows.length === 0) return [];

    console.log('[Segment Grouping] Processing', windows.length, 'windows');

    // Count labels for debugging
    const labelCounts = {};
    windows.forEach(w => {
        const label = w.label || 'unlabeled';
        labelCounts[label] = (labelCounts[label] || 0) + 1;
    });
    console.log('[Segment Grouping] Label distribution:', labelCounts);

    const segments = [];
    let currentSegment = null;

    windows.forEach((window, idx) => {
        const label = window.label;

        // Debug: Log first few and last few windows
        if (idx < 5 || idx >= windows.length - 5) {
            console.log(`[Segment] Window ${idx}/${windows.length}:`, {
                label: label,
                start_time: window.start_time,
                end_time: window.end_time,
                window_id: window.window_id
            });
        }

        // Skip unlabeled windows (gaps)
        if (!label) {
            if (currentSegment) {
                segments.push(currentSegment);
                currentSegment = null;
            }
            return;
        }

        // Start new segment or extend current one
        if (!currentSegment || currentSegment.label !== label) {
            if (currentSegment) {
                segments.push(currentSegment);
            }
            currentSegment = {
                label: label,
                start_time: window.start_time,
                end_time: window.end_time
            };
        } else {
            currentSegment.end_time = window.end_time;
        }
    });

    // Don't forget the last segment
    if (currentSegment) {
        segments.push(currentSegment);
    }

    return segments;
}

/**
 * Update timeline with session data
 * @param {Object} session - Session object with windows metadata
 */
function updateTimeline(session) {
    const windows = session.windows || [];
    if (windows.length === 0) {
        document.getElementById('timelineRange').textContent = '00:00 — 00:00';
        return;
    }

    // CRITICAL: Use the same duration value as playhead for consistency
    const duration = replaySessionDuration;

    // For reference calculations only
    const startTime = new Date(session.created_at);
    const endTime = new Date(session.stopped_at || session.created_at);
    const sessionTimestampDuration = (endTime - startTime) / 1000;

    console.log('[Timeline] Using duration:', duration, 'seconds (same as playhead)');
    console.log('[Timeline] Verification - session timestamp duration:', sessionTimestampDuration, 'seconds');
    if (Math.abs(duration - sessionTimestampDuration) > 1) {
        console.warn('[Timeline] WARNING: Duration mismatch! Timeline duration:', duration, 'vs session timestamps:', sessionTimestampDuration);
    }

    // Update time range display
    document.getElementById('timelineRange').textContent = `${formatTime(1)} — ${formatTime(duration)}`;

    // Generate timeline markers
    const ruler = document.getElementById('timelineRuler');
    const activityTrack = document.getElementById('activityTrack');

    // Clear existing content
    ruler.innerHTML = '';
    if (activityTrack) {
        activityTrack.innerHTML = '';
    }

    // Generate time markers every second
    const markerInterval = 1;
    const markerCount = Math.ceil(duration) + 1;

    // Generate markers at 1-second intervals (starting from 00:01)
    for (let i = 1; i < markerCount; i++) {
        const displayTime = i;
        const actualTime = i - 1;

        if (displayTime > duration) break;

        const marker = document.createElement('div');
        marker.className = 'absolute flex items-center justify-center border-r border-gray-600 h-full';

        const position = (actualTime / duration) * 100;
        marker.style.left = `${position}%`;

        const nextActualTime = Math.min(i, duration);
        const widthInSeconds = nextActualTime - actualTime;
        const width = (widthInSeconds / duration) * 100;
        marker.style.width = `${width}%`;

        marker.innerHTML = `<span class="text-[10px] text-gray-400">${formatTime(displayTime)}</span>`;

        ruler.appendChild(marker);
    }

    // Group windows into activity segments
    const activitySegments = groupActivitySegments(windows);
    console.log('[Timeline] Total windows:', windows.length);
    console.log('[Timeline] Windows with labels:', windows.filter(w => w.label).length);
    console.log('[Timeline] Activity segments:', activitySegments.length, activitySegments);

    // Debug: Show segment details
    activitySegments.forEach((seg, idx) => {
        const segStart = (new Date(seg.start_time) - startTime) / 1000;
        const segEnd = (new Date(seg.end_time) - startTime) / 1000;
        console.log(`[Timeline] Segment ${idx}: ${seg.label} from ${segStart.toFixed(1)}s to ${segEnd.toFixed(1)}s`);
    });

    // Render activity segments on the activity track
    if (activityTrack) {
        activitySegments.forEach((segment, idx) => {
            // Calculate segment position relative to SESSION START TIME
            const segmentStart = (segment.start_time - replaySessionStartTime) / 1000;
            const segmentEnd = (segment.end_time - replaySessionStartTime) / 1000;
            const segmentDuration = segmentEnd - segmentStart;

            const left = (segmentStart / duration) * 100;
            const width = (segmentDuration / duration) * 100;

            // Debug logging for segment positioning
            console.log(`[Timeline Segment ${idx}] "${segment.label}":`, {
                startTime: segmentStart.toFixed(2) + 's',
                endTime: segmentEnd.toFixed(2) + 's',
                duration: segmentDuration.toFixed(2) + 's',
                position: left.toFixed(2) + '%',
                width: width.toFixed(2) + '%',
                totalDuration: duration + 's',
                rawStartTime: segment.start_time,
                rawEndTime: segment.end_time,
                sessionStartTime: replaySessionStartTime
            });

            // Get color for this activity
            const color = activityColors[segment.label] || '#6b7280';

            // Create segment bar
            const segmentBar = document.createElement('div');
            segmentBar.className = 'absolute top-0 h-full flex items-center justify-center text-xs font-medium text-white overflow-hidden';
            segmentBar.style.left = `${left}%`;
            segmentBar.style.width = `${width}%`;
            segmentBar.style.backgroundColor = color;
            segmentBar.style.opacity = '0.8';

            // Add label text inside the bar (only if segment is wide enough)
            const minWidthForLabel = 5;
            if (width > minWidthForLabel) {
                segmentBar.innerHTML = `<span class="px-1 truncate">${segment.label}</span>`;
            }

            // Add tooltip
            segmentBar.title = `${segment.label}: ${formatTime(segmentStart)} - ${formatTime(segmentEnd)}`;

            activityTrack.appendChild(segmentBar);
        });
    }
}

/**
 * Timeline zoom control
 * @param {number} direction - Zoom direction: positive for in, negative for out
 */
function zoomTimeline(direction) {
    // Implement zoom functionality
    console.log('Zoom:', direction > 0 ? 'in' : 'out');
}
