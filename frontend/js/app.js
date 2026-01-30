/**
 * @file app.js
 * @description Main application entry point and initialization
 */

/**
 * Initialize the application when DOM is ready
 * Uses InitLoader for step-by-step initialization with loading screen
 */
document.addEventListener('DOMContentLoaded', () => {
    InitLoader.run();
});

// Expose functions to window for HTML onclick handlers
window.toggleRecording = toggleRecording;
window.selectSession = selectSession;
window.deleteSession = deleteSession;
window.renameSession = renameSession;
window.replayControl = replayControl;
window.zoomTimeline = zoomTimeline;
