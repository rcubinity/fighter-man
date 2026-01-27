/**
 * VideoRecorder - Browser-based video recording for sensor sessions
 *
 * Features:
 * - MediaRecorder API integration with WebM format
 * - Real-time preview during recording
 * - Timestamp synchronization with sensor data
 * - Upload to server after recording completes
 * - Error handling and browser compatibility checks
 */

class VideoRecorder {
    constructor(options = {}) {
        // Configuration with defaults
        this.config = {
            resolution: {
                width: options.width || 1280,
                height: options.height || 720
            },
            frameRate: options.frameRate || 30,
            videoBitsPerSecond: options.bitrate || 2500000, // 2.5 Mbps
            mimeType: this.getSupportedMimeType()
        };

        // State management
        this.state = 'idle'; // idle, recording, stopped, uploading
        this.stream = null;
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.videoBlob = null;
        this.recordingStartTime = null;
        this.previewElement = null;
    }

    /**
     * Detect best supported video codec
     */
    getSupportedMimeType() {
        const types = [
            'video/webm;codecs=vp9',
            'video/webm;codecs=vp8',
            'video/webm'
        ];

        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                console.log(`[VideoRecorder] Using MIME type: ${type}`);
                return type;
            }
        }

        console.warn('[VideoRecorder] No preferred MIME type supported, using default');
        return 'video/webm';
    }

    /**
     * Initialize camera and check permissions
     */
    async init(previewElementId = 'video-preview') {
        try {
            // Check MediaRecorder API support
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('MediaDevices API not supported in this browser');
            }

            if (typeof MediaRecorder === 'undefined') {
                throw new Error('MediaRecorder API not supported in this browser');
            }

            // Request camera access
            console.log('[VideoRecorder] Requesting camera access...');
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: this.config.resolution.width },
                    height: { ideal: this.config.resolution.height },
                    frameRate: { ideal: this.config.frameRate }
                },
                audio: false // No audio for now
            });

            console.log('[VideoRecorder] Camera access granted');

            // Get video preview element
            this.previewElement = document.getElementById(previewElementId);
            if (this.previewElement) {
                this.previewElement.srcObject = this.stream;
                console.log('[VideoRecorder] Preview connected');
            }

            return true;

        } catch (error) {
            console.error('[VideoRecorder] Initialization failed:', error);
            if (error.name === 'NotAllowedError') {
                throw new Error('Camera permission denied. Please allow camera access and try again.');
            } else if (error.name === 'NotFoundError') {
                throw new Error('No camera found. Please connect a camera and try again.');
            } else {
                throw error;
            }
        }
    }

    /**
     * Start recording video
     */
    async startRecording(sessionId) {
        if (this.state !== 'idle') {
            throw new Error(`Cannot start recording in state: ${this.state}`);
        }

        if (!this.stream) {
            throw new Error('Camera not initialized. Call init() first.');
        }

        try {
            // Create MediaRecorder
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: this.config.mimeType,
                videoBitsPerSecond: this.config.videoBitsPerSecond
            });

            // Reset recorded chunks
            this.recordedChunks = [];
            this.videoBlob = null;

            // Handle data available event
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                    console.log(`[VideoRecorder] Chunk received: ${event.data.size} bytes`);
                }
            };

            // Handle recording stop
            this.mediaRecorder.onstop = () => {
                console.log('[VideoRecorder] Recording stopped');
                this.createVideoBlob();
            };

            // Handle errors
            this.mediaRecorder.onerror = (event) => {
                console.error('[VideoRecorder] Recording error:', event.error);
                this.state = 'idle';
            };

            // Start recording
            this.mediaRecorder.start(1000); // Collect data every 1 second
            this.recordingStartTime = new Date();
            this.state = 'recording';

            console.log(`[VideoRecorder] Started recording for session: ${sessionId}`);
            console.log(`[VideoRecorder] Start time: ${this.recordingStartTime.toISOString()}`);

            return this.recordingStartTime;

        } catch (error) {
            console.error('[VideoRecorder] Failed to start recording:', error);
            this.state = 'idle';
            throw error;
        }
    }

    /**
     * Stop recording
     */
    async stopRecording() {
        if (this.state !== 'recording') {
            console.warn(`[VideoRecorder] Not recording (state: ${this.state})`);
            return null;
        }

        return new Promise((resolve, reject) => {
            // Set up one-time listener for stop event
            const handleStop = () => {
                this.state = 'stopped';
                this.mediaRecorder.removeEventListener('stop', handleStop);
                resolve(this.videoBlob);
            };

            this.mediaRecorder.addEventListener('stop', handleStop);

            // Stop the recorder
            this.mediaRecorder.stop();
            console.log('[VideoRecorder] Stopping recording...');
        });
    }

    /**
     * Create video blob from recorded chunks
     */
    createVideoBlob() {
        if (this.recordedChunks.length === 0) {
            console.warn('[VideoRecorder] No chunks recorded');
            return null;
        }

        this.videoBlob = new Blob(this.recordedChunks, {
            type: this.config.mimeType
        });

        const sizeMB = (this.videoBlob.size / (1024 * 1024)).toFixed(2);
        console.log(`[VideoRecorder] Video blob created: ${sizeMB} MB`);

        return this.videoBlob;
    }

    /**
     * Get recording duration in seconds
     */
    getRecordingDuration() {
        if (!this.recordingStartTime) {
            return 0;
        }

        const now = this.state === 'recording' ? new Date() : new Date();
        return (now - this.recordingStartTime) / 1000;
    }

    /**
     * Get recorded video blob
     */
    getVideoBlob() {
        return this.videoBlob;
    }

    /**
     * Upload video to server
     */
    async uploadVideo(sessionId, videoBlob = null) {
        const blob = videoBlob || this.videoBlob;

        if (!blob) {
            throw new Error('No video to upload. Record a video first.');
        }

        if (!sessionId) {
            throw new Error('Session ID is required for upload');
        }

        // Check file size limit (default 500 MB)
        const maxSizeMB = 500;
        const blobSizeMB = blob.size / (1024 * 1024);
        if (blobSizeMB > maxSizeMB) {
            throw new Error(`Video file too large (${blobSizeMB.toFixed(2)} MB). Maximum size is ${maxSizeMB} MB.`);
        }

        this.state = 'uploading';

        try {
            console.log(`[VideoRecorder] Uploading video for session ${sessionId}...`);
            console.log(`[VideoRecorder] Size: ${blobSizeMB.toFixed(2)} MB`);

            // Create form data
            const formData = new FormData();
            formData.append('video', blob, `${sessionId}.webm`);

            // Upload to server
            const response = await fetch(`${SERVER_URL}/api/sessions/${sessionId}/upload-video`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || `Upload failed: ${response.status}`);
            }

            const result = await response.json();
            console.log('[VideoRecorder] Upload successful:', result);

            this.state = 'idle';
            return result;

        } catch (error) {
            console.error('[VideoRecorder] Upload failed:', error);
            this.state = 'stopped';
            throw error;
        }
    }

    /**
     * Upload with progress callback
     */
    async uploadVideoWithProgress(sessionId, onProgress) {
        const blob = this.videoBlob;

        if (!blob) {
            throw new Error('No video to upload');
        }

        this.state = 'uploading';

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // Track upload progress
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    if (onProgress) {
                        onProgress(percentComplete, event.loaded, event.total);
                    }
                    console.log(`[VideoRecorder] Upload progress: ${percentComplete.toFixed(1)}%`);
                }
            });

            // Handle completion
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    const result = JSON.parse(xhr.responseText);
                    console.log('[VideoRecorder] Upload successful:', result);
                    this.state = 'idle';
                    resolve(result);
                } else {
                    const error = JSON.parse(xhr.responseText);
                    console.error('[VideoRecorder] Upload failed:', error);
                    this.state = 'stopped';
                    reject(new Error(error.error || `Upload failed: ${xhr.status}`));
                }
            });

            // Handle errors
            xhr.addEventListener('error', () => {
                console.error('[VideoRecorder] Network error during upload');
                this.state = 'stopped';
                reject(new Error('Network error during upload'));
            });

            xhr.addEventListener('abort', () => {
                console.error('[VideoRecorder] Upload aborted');
                this.state = 'stopped';
                reject(new Error('Upload aborted'));
            });

            // Create form data
            const formData = new FormData();
            formData.append('video', blob, `${sessionId}.webm`);

            // Send request
            xhr.open('POST', `${SERVER_URL}/api/sessions/${sessionId}/upload-video`);
            xhr.send(formData);
        });
    }

    /**
     * Clean up resources
     */
    destroy() {
        console.log('[VideoRecorder] Cleaning up...');

        // Stop recording if active
        if (this.mediaRecorder && this.state === 'recording') {
            this.mediaRecorder.stop();
        }

        // Stop camera stream
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        // Clear preview
        if (this.previewElement) {
            this.previewElement.srcObject = null;
        }

        // Clear state
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.videoBlob = null;
        this.recordingStartTime = null;
        this.state = 'idle';

        console.log('[VideoRecorder] Cleanup complete');
    }

    /**
     * Get current state
     */
    getState() {
        return this.state;
    }

    /**
     * Check if browser supports video recording
     */
    static isSupported() {
        return !!(
            navigator.mediaDevices &&
            navigator.mediaDevices.getUserMedia &&
            typeof MediaRecorder !== 'undefined'
        );
    }
}
