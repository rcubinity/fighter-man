/**
 * @file app.js
 * @description Main application entry point and initialization
 */

/**
 * Initialize the application when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    initFootBars();
    loadSessions();

    // Initialize activity detector
    activityDetector = new ActivityDetector();

    // Initialize video recorder if supported
    if (VideoRecorder.isSupported()) {
        videoRecorder = new VideoRecorder();
        console.log('[Video] VideoRecorder initialized');
    } else {
        console.warn('[Video] Video recording not supported in this browser');
    }

    connectSocket();
    checkActiveSession();
});

// Expose functions to window for HTML onclick handlers
window.toggleRecording = toggleRecording;
window.selectSession = selectSession;
window.deleteSession = deleteSession;
window.renameSession = renameSession;
window.replayControl = replayControl;
window.zoomTimeline = zoomTimeline;
