# Video Recording Technical Reference

This document provides technical details about the browser-based video recording system implemented in `videoRecorder.js`.

## Table of Contents

1. [Browser APIs Used](#browser-apis-used)
2. [Video Configuration](#video-configuration)
3. [Recording Process](#recording-process)
4. [Upload Mechanism](#upload-mechanism)
5. [Error Handling](#error-handling)
6. [Browser Compatibility](#browser-compatibility)

---

## Browser APIs Used

### MediaDevices API

Used for accessing camera hardware:

```javascript
navigator.mediaDevices.getUserMedia(constraints)
```

**Requires:**
- HTTPS connection OR localhost
- User permission grant
- Camera hardware available

**Returns:** `MediaStream` object containing video track

### MediaRecorder API

Used for encoding video from MediaStream:

```javascript
const recorder = new MediaRecorder(stream, options);
recorder.start(timeslice);  // Collect chunks every N ms
recorder.stop();             // Finalize recording
```

**Supported Formats:**
- WebM container (primary)
- VP9 codec (preferred)
- VP8 codec (fallback)

---

## Video Configuration

### Default Settings

```javascript
{
  resolution: {
    width: 1280,
    height: 720
  },
  frameRate: 30,
  videoBitsPerSecond: 2500000,  // 2.5 Mbps
  mimeType: 'video/webm;codecs=vp9'
}
```

### Resolution: 1280x720 (HD)

**Why HD Quality?**
- Good balance of quality vs. file size
- Clear enough to see body movements
- Not excessive for network/storage

**Estimated File Sizes:**
- 1 minute: ~2-3 MB
- 10 minutes: ~20-30 MB
- 30 minutes: ~60-90 MB

**Server Limit:** 500 MB (roughly 30-40 minutes of HD video)

### Frame Rate: 30 FPS

**Why 30 FPS?**
- Smooth playback for human movement
- Standard video frame rate
- Lower than 60 FPS saves bandwidth/storage

**Trade-offs:**
- Higher FPS = smoother but larger files
- Lower FPS = smaller but choppy playback

### Bitrate: 2.5 Mbps

**What is Bitrate?**
- Amount of data per second of video
- Higher = better quality but larger files

**Why 2.5 Mbps?**
- Good quality for 720p video
- Reasonable file sizes
- Standard for HD streaming

### Codec: VP9 (VP8 fallback)

**VP9:**
- Modern, efficient codec
- Good compression (smaller files)
- Supported in Chrome, Firefox, Edge

**VP8 Fallback:**
- Older codec (larger files)
- Used if VP9 not available
- Wider browser support

---

## Recording Process

### Step 1: Initialization

```javascript
async init(previewElementId = 'video-preview') {
  // 1. Check API support
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error('MediaDevices API not supported');
  }

  if (typeof MediaRecorder === 'undefined') {
    throw new Error('MediaRecorder API not supported');
  }

  // 2. Request camera access
  this.stream = await navigator.mediaDevices.getUserMedia({
    video: {
      width: { ideal: 1280 },
      height: { ideal: 720 },
      frameRate: { ideal: 30 }
    },
    audio: false  // No microphone recording
  });

  // 3. Connect to preview element
  this.previewElement = document.getElementById(previewElementId);
  if (this.previewElement) {
    this.previewElement.srcObject = this.stream;
  }

  return true;
}
```

**What Happens:**
1. Check browser supports required APIs
2. Request camera permission from user
3. Get video stream from camera
4. Display live preview (mirrored for user comfort)

### Step 2: Start Recording

```javascript
async startRecording(sessionId) {
  // 1. Create MediaRecorder
  this.mediaRecorder = new MediaRecorder(this.stream, {
    mimeType: this.config.mimeType,
    videoBitsPerSecond: this.config.videoBitsPerSecond
  });

  // 2. Reset state
  this.recordedChunks = [];
  this.videoBlob = null;
  this.recordingStartTime = new Date();
  this.state = 'recording';

  // 3. Handle data chunks
  this.mediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      this.recordedChunks.push(event.data);
    }
  };

  // 4. Start recording (collect chunks every 1 second)
  this.mediaRecorder.start(1000);

  return this.recordingStartTime;
}
```

**Chunk Collection:**
- Every 1 second, MediaRecorder fires `ondataavailable` event
- Each chunk is a Blob of encoded video data
- Chunks are stored in memory array

**Why 1-second chunks?**
- Balance between memory usage and overhead
- Allows progress tracking during long recordings
- Easy to recover partial recordings if crash occurs

### Step 3: Stop Recording

```javascript
async stopRecording() {
  if (this.state !== 'recording') {
    return null;
  }

  return new Promise((resolve, reject) => {
    // Set up listener for stop event
    const handleStop = () => {
      this.state = 'stopped';
      this.mediaRecorder.removeEventListener('stop', handleStop);
      resolve(this.videoBlob);
    };

    this.mediaRecorder.addEventListener('stop', handleStop);

    // Stop the recorder
    this.mediaRecorder.stop();
  });
}
```

**What Happens:**
1. `stop()` called → MediaRecorder finalizes last chunk
2. `onstop` event fires → Creates video blob from chunks
3. Promise resolves with completed video blob

### Step 4: Create Video Blob

```javascript
createVideoBlob() {
  if (this.recordedChunks.length === 0) {
    return null;
  }

  this.videoBlob = new Blob(this.recordedChunks, {
    type: this.config.mimeType
  });

  const sizeMB = (this.videoBlob.size / (1024 * 1024)).toFixed(2);
  console.log(`Video blob created: ${sizeMB} MB`);

  return this.videoBlob;
}
```

**Blob Creation:**
- Combine all chunks into single Blob
- Set MIME type for proper playback
- Blob is in-memory (not saved to disk yet)

---

## Upload Mechanism

### Simple Upload (No Progress)

```javascript
async uploadVideo(sessionId, videoBlob = null) {
  const blob = videoBlob || this.videoBlob;

  // 1. Validate
  if (!blob) {
    throw new Error('No video to upload');
  }

  const maxSizeMB = 500;
  const blobSizeMB = blob.size / (1024 * 1024);
  if (blobSizeMB > maxSizeMB) {
    throw new Error(`Video file too large (${blobSizeMB.toFixed(2)} MB)`);
  }

  // 2. Create form data
  const formData = new FormData();
  formData.append('video', blob, `${sessionId}.webm`);

  // 3. Upload
  const response = await fetch(
    `http://localhost:4100/api/sessions/${sessionId}/upload-video`,
    {
      method: 'POST',
      body: formData
    }
  );

  // 4. Handle response
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || `Upload failed: ${response.status}`);
  }

  return await response.json();
}
```

### Upload with Progress Tracking

```javascript
async uploadVideoWithProgress(sessionId, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // Track upload progress
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        const percentComplete = (event.loaded / event.total) * 100;
        if (onProgress) {
          onProgress(percentComplete, event.loaded, event.total);
        }
      }
    });

    // Handle completion
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const result = JSON.parse(xhr.responseText);
        resolve(result);
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`));
      }
    });

    // Create form data
    const formData = new FormData();
    formData.append('video', this.videoBlob, `${sessionId}.webm`);

    // Send request
    xhr.open('POST', `http://localhost:4100/api/sessions/${sessionId}/upload-video`);
    xhr.send(formData);
  });
}
```

**Why XMLHttpRequest instead of fetch?**
- `fetch` API doesn't support upload progress tracking
- `xhr.upload.onprogress` provides real-time upload status
- Allows UI to show progress bar

**Upload Flow:**
1. Create FormData with video blob
2. Send POST request to server
3. Track progress via XHR events
4. Update UI progress bar (0-100%)
5. Resolve promise when complete

---

## Error Handling

### Camera Permission Errors

```javascript
try {
  this.stream = await navigator.mediaDevices.getUserMedia(constraints);
} catch (error) {
  if (error.name === 'NotAllowedError') {
    throw new Error('Camera permission denied. Please allow camera access and try again.');
  } else if (error.name === 'NotFoundError') {
    throw new Error('No camera found. Please connect a camera and try again.');
  } else {
    throw error;
  }
}
```

**Error Types:**
- `NotAllowedError`: User clicked "Block" or permissions denied by browser
- `NotFoundError`: No camera hardware detected
- `NotReadableError`: Camera in use by another application
- `OverconstrainedError`: Requested resolution not supported

### Recording Errors

```javascript
this.mediaRecorder.onerror = (event) => {
  console.error('Recording error:', event.error);
  this.state = 'idle';
  // Notify user, clean up resources
};
```

**Common Recording Errors:**
- Out of memory (very long recordings)
- Codec not supported
- Hardware encoder failure

### Upload Errors

```javascript
// Network error
xhr.addEventListener('error', () => {
  reject(new Error('Network error during upload'));
});

// Upload aborted
xhr.addEventListener('abort', () => {
  reject(new Error('Upload aborted'));
});

// Server error
if (xhr.status >= 400) {
  reject(new Error(`Server error: ${xhr.status}`));
}
```

**Upload Error Scenarios:**
- Network disconnected
- Server not responding
- Server disk full (507 Insufficient Storage)
- File too large (400 Bad Request)

---

## Browser Compatibility

### Feature Support Matrix

| Browser | MediaDevices | MediaRecorder | VP9 | VP8 | Notes |
|---------|-------------|---------------|-----|-----|-------|
| **Chrome 90+** | ✅ | ✅ | ✅ | ✅ | Best support |
| **Firefox 88+** | ✅ | ✅ | ❌ | ✅ | Uses VP8 |
| **Safari 14.1+** | ✅ | ✅ | ❌ | ⚠️ | Limited WebM support |
| **Edge 90+** | ✅ | ✅ | ✅ | ✅ | Same as Chrome |
| **IE 11** | ❌ | ❌ | ❌ | ❌ | Not supported |

### Checking Support

```javascript
static isSupported() {
  return !!(
    navigator.mediaDevices &&
    navigator.mediaDevices.getUserMedia &&
    typeof MediaRecorder !== 'undefined'
  );
}
```

**Usage:**
```javascript
if (!VideoRecorder.isSupported()) {
  alert('Your browser does not support video recording. Please use Chrome 90+ or Firefox 88+.');
}
```

### MIME Type Fallback

```javascript
getSupportedMimeType() {
  const types = [
    'video/webm;codecs=vp9',  // Preferred
    'video/webm;codecs=vp8',  // Fallback
    'video/webm'              // Generic
  ];

  for (const type of types) {
    if (MediaRecorder.isTypeSupported(type)) {
      console.log(`Using MIME type: ${type}`);
      return type;
    }
  }

  console.warn('No preferred MIME type supported, using default');
  return 'video/webm';
}
```

**Codec Selection:**
1. Try VP9 (best compression)
2. Fall back to VP8 (wider support)
3. Fall back to generic WebM (browser chooses codec)

---

## Performance Considerations

### Memory Usage

**During Recording:**
- Video chunks accumulate in JavaScript memory
- 1 minute ≈ 2-3 MB in memory
- 30 minutes ≈ 60-90 MB in memory

**Peak Usage:**
- Recording: Chunks in memory
- Upload: Blob + FormData (2x file size temporarily)

**Mitigation:**
- Chunks released after upload completes
- Clear `recordedChunks` array immediately after blob creation

### CPU Usage

**Encoding:**
- MediaRecorder uses hardware encoder (GPU) when available
- Falls back to software encoding if no GPU
- Minimal CPU impact with hardware acceleration

**UI Updates:**
- Video preview: Handled by browser (hardware accelerated)
- Progress bar: Updates every 100ms (throttled)

### Network Bandwidth

**Upload Speed:**
- Depends on connection speed
- Example: 25 MB video on 10 Mbps connection ≈ 20 seconds
- Progress tracking allows user to see upload status

---

## Security Considerations

### HTTPS Requirement

MediaDevices API requires secure context:
- ✅ `https://` URLs
- ✅ `localhost` (exception for development)
- ❌ `http://` on remote servers

### Permission Persistence

Browser remembers camera permission:
- **Allow:** Stored per-origin, persists across sessions
- **Block:** Stored per-origin, persists until manually changed
- **Reset:** User can change in browser settings

### Privacy

- Video never leaves user's device until user clicks "Stop Recording"
- User can review video before upload (if feature added)
- Server has no access to camera until user grants permission

---

**Document Version:** 1.0
**Last Updated:** December 24, 2025
