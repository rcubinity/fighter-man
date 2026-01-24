/**
 * P5.js-based Pose Detection Sketch
 * Uses p5.js instance mode to avoid global conflicts
 *
 * Based on the working ml5-simple implementation
 */

// Global reference to the sketch instance
let poseSketchInstance = null;
let poseSketchReady = false;

/**
 * Create and start the pose detection sketch
 * @param {string} containerId - ID of the container element
 * @param {object} options - Configuration options
 * @returns {object} - Object with stream and control methods
 */
function createPoseSketch(containerId, options = {}) {
    const config = {
        width: options.width || 640,
        height: options.height || 480,
        mirror: options.mirror !== false,
        showSkeleton: options.showSkeleton !== false,
        showKeypoints: options.showKeypoints !== false,
        confidenceThreshold: options.confidenceThreshold || 0.3,
        onPoseDetected: options.onPoseDetected || null
    };

    let video = null;
    let bodyPose = null;
    let poses = [];
    let isRunning = false;
    let modelLoaded = false;
    let canvasElement = null;

    // Reset ready state
    poseSketchReady = false;

    // p5.js instance mode sketch
    const sketch = (p) => {
        let videoFailed = false;
        let setupComplete = false;
        let fallbackTimeout = null;

        // Fallback function to mark sketch ready without video
        function markReadyWithoutVideo(reason) {
            if (poseSketchReady) return; // Already ready

            console.warn('[PoseSketch] ' + reason);
            videoFailed = true;

            p.background(0);
            p.fill(255, 100, 100);
            p.textAlign(p.CENTER, p.CENTER);
            p.textSize(18);
            p.text('Camera unavailable', p.width/2, p.height/2 - 20);
            p.textSize(14);
            p.fill(180);
            p.text('Recording will continue without video', p.width/2, p.height/2 + 20);

            isRunning = true;
            poseSketchReady = true;
            console.log('[PoseSketch] Marked ready without video/pose detection');
        }

        // Setup - create canvas and video, then load model
        p.setup = function() {
            console.log('[PoseSketch] Setup starting...');

            // Create canvas
            let canvas = p.createCanvas(config.width, config.height);
            canvas.parent(containerId);
            canvasElement = canvas.elt;

            console.log('[PoseSketch] Canvas created:', config.width, 'x', config.height);

            // Show loading message
            p.background(0);
            p.fill(255);
            p.textAlign(p.CENTER, p.CENTER);
            p.textSize(20);
            p.text('Starting camera...', p.width/2, p.height/2);

            // Set a fallback timeout - if video doesn't initialize within 5 seconds,
            // mark as ready without video so recording can proceed
            fallbackTimeout = setTimeout(() => {
                if (!poseSketchReady) {
                    markReadyWithoutVideo('Camera timeout - proceeding without video');
                }
            }, 5000);

            // Create video capture
            try {
                video = p.createCapture(p.VIDEO, function() {
                    // Clear fallback timeout since video is ready
                    if (fallbackTimeout) {
                        clearTimeout(fallbackTimeout);
                        fallbackTimeout = null;
                    }

                    console.log('[PoseSketch] Video capture ready, now loading ml5...');

                    // Update loading message
                    p.background(0);
                    p.fill(255);
                    p.textAlign(p.CENTER, p.CENTER);
                    p.textSize(20);
                    p.text('Loading ML5 model...', p.width/2, p.height/2);

                    // Load ml5 bodyPose model using callback pattern
                    console.log('[PoseSketch] Loading ml5.bodyPose...');

                    // Set another timeout for ML5 model loading
                    const ml5Timeout = setTimeout(() => {
                        if (!poseSketchReady) {
                            markReadyWithoutVideo('ML5 model timeout - proceeding with video only');
                            // Still try to draw video even without pose detection
                            isRunning = true;
                        }
                    }, 10000);

                    bodyPose = ml5.bodyPose('MoveNet', function() {
                        clearTimeout(ml5Timeout);

                        if (poseSketchReady) return; // Already marked ready by timeout

                        console.log('[PoseSketch] ml5.bodyPose model loaded via callback');

                        // Check video state
                        console.log('[PoseSketch] Video element:', video.elt);
                        console.log('[PoseSketch] Video readyState:', video.elt.readyState);
                        console.log('[PoseSketch] Video dimensions:', video.elt.videoWidth, 'x', video.elt.videoHeight);

                        // Start pose detection
                        bodyPose.detectStart(video, gotPoses);
                        modelLoaded = true;
                        isRunning = true;
                        poseSketchReady = true;

                        console.log('[PoseSketch] Pose detection started');
                    });
                });

                video.size(config.width, config.height);
                video.hide();
            } catch (err) {
                console.error('[PoseSketch] Failed to create video capture:', err);
                if (fallbackTimeout) {
                    clearTimeout(fallbackTimeout);
                }
                markReadyWithoutVideo('Camera creation failed: ' + err.message);
            }

            setupComplete = true;
        };

        // Pose detection callback
        function gotPoses(results) {
            poses = results;
            if (config.onPoseDetected && poses.length > 0) {
                config.onPoseDetected(poses[0]);
            }
        }

        // Draw loop
        p.draw = function() {
            if (!isRunning || !video) {
                return;
            }

            // Draw the video
            if (config.mirror) {
                p.push();
                p.translate(p.width, 0);
                p.scale(-1, 1);
                p.image(video, 0, 0, p.width, p.height);
                p.pop();
            } else {
                p.image(video, 0, 0, p.width, p.height);
            }

            // Draw all detected poses
            for (let i = 0; i < poses.length; i++) {
                let pose = poses[i];

                if (config.showSkeleton) {
                    drawSkeleton(pose);
                }
                if (config.showKeypoints) {
                    drawKeypoints(pose);
                }
            }

            // Draw info overlay
            drawInfoOverlay();
        };

        // Draw skeleton connections
        function drawSkeleton(pose) {
            if (!bodyPose) return;

            let connections = bodyPose.getSkeleton();

            for (let i = 0; i < connections.length; i++) {
                let connection = connections[i];
                let pointA = pose.keypoints[connection[0]];
                let pointB = pose.keypoints[connection[1]];

                if (pointA.confidence > config.confidenceThreshold &&
                    pointB.confidence > config.confidenceThreshold) {

                    let ax = config.mirror ? p.width - pointA.x : pointA.x;
                    let ay = pointA.y;
                    let bx = config.mirror ? p.width - pointB.x : pointB.x;
                    let by = pointB.y;

                    p.stroke(0, 255, 255);  // Cyan
                    p.strokeWeight(4);
                    p.line(ax, ay, bx, by);
                }
            }
        }

        // Draw keypoints
        function drawKeypoints(pose) {
            for (let i = 0; i < pose.keypoints.length; i++) {
                let keypoint = pose.keypoints[i];

                if (keypoint.confidence > config.confidenceThreshold) {
                    let kx = config.mirror ? p.width - keypoint.x : keypoint.x;
                    let ky = keypoint.y;

                    p.fill(255, 0, 255);  // Magenta
                    p.noStroke();
                    p.circle(kx, ky, 12);
                }
            }
        }

        // Draw info overlay
        function drawInfoOverlay() {
            // Background box
            p.fill(0, 0, 0, 180);
            p.noStroke();
            p.rect(10, p.height - 35, 160, 25, 8);

            // Text
            p.fill(255);
            p.textSize(12);
            p.textAlign(p.LEFT, p.CENTER);
            p.text(`Poses: ${poses.length} | FPS: ${Math.round(p.frameRate())}`, 18, p.height - 22);
        }
    };

    // Create the p5 instance
    console.log('[PoseSketch] Creating p5 instance in container:', containerId);

    // Make sure container exists
    const container = document.getElementById(containerId);
    if (!container) {
        console.error('[PoseSketch] Container not found:', containerId);
        return null;
    }

    poseSketchInstance = new p5(sketch);

    // Return control object
    return {
        /**
         * Get the canvas stream (includes skeleton overlay)
         * Returns a promise that resolves when canvas is ready
         */
        getCanvasStream: function() {
            return new Promise((resolve, reject) => {
                let attempts = 0;
                const maxAttempts = 100;  // 10 seconds max

                const checkCanvas = () => {
                    const canvas = document.querySelector(`#${containerId} canvas`);
                    console.log('[PoseSketch] Checking canvas, attempt', attempts, 'canvas:', canvas, 'ready:', poseSketchReady);

                    if (canvas && poseSketchReady) {
                        console.log('[PoseSketch] Canvas ready, creating stream...');
                        try {
                            const stream = canvas.captureStream(30);
                            resolve(stream);
                        } catch (e) {
                            reject(new Error('Failed to capture stream: ' + e.message));
                        }
                    } else if (attempts < maxAttempts) {
                        attempts++;
                        setTimeout(checkCanvas, 100);
                    } else {
                        reject(new Error('Canvas not ready after timeout'));
                    }
                };
                checkCanvas();
            });
        },

        /**
         * Stop the sketch
         */
        stop: function() {
            console.log('[PoseSketch] Stopping...');
            isRunning = false;
            poseSketchReady = false;

            if (bodyPose && typeof bodyPose.detectStop === 'function') {
                try {
                    bodyPose.detectStop();
                } catch (e) {
                    console.warn('[PoseSketch] Error stopping detection:', e);
                }
            }

            if (poseSketchInstance) {
                poseSketchInstance.remove();
                poseSketchInstance = null;
            }

            console.log('[PoseSketch] Stopped');
        },

        /**
         * Check if model is loaded and running
         */
        isReady: function() {
            return poseSketchReady;
        },

        /**
         * Get current poses
         */
        getPoses: function() {
            return poses;
        }
    };
}

/**
 * Stop the current pose sketch if running
 */
function stopPoseSketch() {
    if (poseSketchInstance) {
        poseSketchInstance.remove();
        poseSketchInstance = null;
    }
    poseSketchReady = false;
}
