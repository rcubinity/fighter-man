# Testing Guide

## Test Files Overview

| File                  | Purpose                                                              |
| --------------------- | -------------------------------------------------------------------- |
| `test_api.py`         | Tests REST API endpoints only (no data)                              |
| `test_client.py`      | Simulates Pi sending sensor data via Socket.IO                       |
| `test_integration.py` | Full end-to-end test (create session → send data → verify → cleanup) |

---

## Prerequisites

Before running tests, ensure both services are running:

```bash
# Check Qdrant
curl http://localhost:6333/health

# Check Server
curl http://localhost:4100/health
```

If not running:

```bash
# Start Qdrant
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Start Server
./start.sh
```

---

## Quick Start

```bash
cd /Users/gorki/Herd/neuronso-connection/firefighter-server
source venv/bin/activate
```

---

## Run All Tests

```bash
./run_tests.sh
```

This runs API tests + integration tests automatically.

---

## Individual Tests

### 1. API Tests (REST endpoints)

Tests all API endpoints without sending sensor data.

```bash
python tests/test_api.py
```

### 2. Test Client (Simulate Pi sending data)

Simulates a Raspberry Pi sending sensor data via Socket.IO.

```bash
# Send data for 10 seconds
python tests/test_client.py --duration 10

# Send data for 30 seconds
python tests/test_client.py --duration 30

# Custom server
python tests/test_client.py --server http://192.168.1.100:4100 --duration 10
```

### 3. Integration Test (Full flow)

Creates session, sends data, verifies storage, exports, and cleans up.

```bash
python tests/test_integration.py --duration 5
```

---

## Manual Testing with curl

### Health Check

```bash
curl http://localhost:4100/health
```

### Create Session

```bash
curl -X POST http://localhost:4100/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "my_test_session"}'
```

### List Sessions

```bash
curl http://localhost:4100/api/sessions
```

### Get Session Details

```bash
curl http://localhost:4100/api/sessions/{SESSION_ID}
```

### Stop Session

```bash
curl -X POST http://localhost:4100/api/sessions/{SESSION_ID}/stop
```

### Export Session

```bash
curl "http://localhost:4100/api/sessions/{SESSION_ID}/export?format=json"
```

### Delete Session

```bash
curl -X DELETE http://localhost:4100/api/sessions/{SESSION_ID}
```

---

## Complete Test Workflow

```bash
# 1. Start server (Terminal 1)
./start.sh

# 2. Run test client (Terminal 2)
source venv/bin/activate
python tests/test_client.py --duration 10

# 3. Verify data
curl http://localhost:4100/health
# Check points_count > 0

curl http://localhost:4100/api/sessions
# See your session listed
```

---

## Video Recording Tests

### Test Video Upload

**Purpose:** Verify video file upload and storage

```bash
# 1. Create a test session
SESSION_ID=$(curl -s -X POST http://localhost:4100/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "test_video_session"}' | jq -r '.id')

echo "Created session: $SESSION_ID"

# 2. Create a test video file (10 seconds blank video)
ffmpeg -f lavfi -i color=c=black:s=1280x720:d=10 -c:v vp9 test_video.webm

# 3. Upload video
curl -X POST http://localhost:4100/api/sessions/$SESSION_ID/upload-video \
  -F "video=@test_video.webm"

# Expected response:
# {
#   "success": true,
#   "video_file_path": "{session_id}.webm",
#   "size_bytes": <file_size>
# }

# 4. Verify file exists on disk
ls -lh data/videos/$SESSION_ID.webm

# 5. Verify database record
curl http://localhost:4100/api/sessions/$SESSION_ID | jq '.video_file_path'
# Should return: "{session_id}.webm"

# 6. Cleanup
rm test_video.webm
curl -X DELETE http://localhost:4100/api/sessions/$SESSION_ID
```

### Test Video Streaming

**Purpose:** Verify video playback with Range requests

```bash
# 1. Use the session from previous test (or create new one with video)

# 2. Request full video
curl http://localhost:4100/api/sessions/$SESSION_ID/video \
  --output downloaded_video.webm

# 3. Verify file is playable
ffplay downloaded_video.webm  # (or open in browser)

# 4. Test Range request (for seeking)
curl -H "Range: bytes=0-1024" \
  http://localhost:4100/api/sessions/$SESSION_ID/video \
  --output video_chunk.webm

# Expected: 206 Partial Content response
# Expected headers:
#   Content-Range: bytes 0-1024/<total_size>
#   Accept-Ranges: bytes

# 5. Cleanup
rm downloaded_video.webm video_chunk.webm
```

### Test Error Cases

**Purpose:** Verify proper error handling

```bash
# Test 1: Upload without video file
curl -X POST http://localhost:4100/api/sessions/$SESSION_ID/upload-video
# Expected: 400 Bad Request - "No video file provided"

# Test 2: Upload to non-existent session
curl -X POST http://localhost:4100/api/sessions/invalid-id/upload-video \
  -F "video=@test_video.webm"
# Expected: 404 Not Found - "Session not found"

# Test 3: Request video for session without video
curl http://localhost:4100/api/sessions/$SESSION_WITHOUT_VIDEO/video
# Expected: 404 Not Found - "Video not found"

# Test 4: Upload oversized video (>500 MB)
# Create large file: dd if=/dev/zero of=large_video.webm bs=1M count=600
# curl -X POST http://localhost:4100/api/sessions/$SESSION_ID/upload-video \
#   -F "video=@large_video.webm"
# Expected: 400 or 507 error (depending on server configuration)
```

### Integration Test: Full Recording Flow with Video

**Purpose:** Test complete video recording workflow

```bash
# 1. Create session
SESSION_ID=$(curl -s -X POST http://localhost:4100/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "integration_test_video"}' | jq -r '.id')

echo "Created session: $SESSION_ID"

# 2. Simulate recording (wait a few seconds)
sleep 5

# 3. Stop session
curl -X POST http://localhost:4100/api/sessions/$SESSION_ID/stop

# 4. Create and upload test video
ffmpeg -f lavfi -i color=c=black:s=1280x720:d=5 -c:v vp9 test_video.webm
curl -X POST http://localhost:4100/api/sessions/$SESSION_ID/upload-video \
  -F "video=@test_video.webm"

# 5. Verify session has video metadata
curl -s http://localhost:4100/api/sessions/$SESSION_ID | jq '{
  id, name, video_file_path, video_size_bytes
}'

# 6. Stream video and verify playback
curl http://localhost:4100/api/sessions/$SESSION_ID/video \
  --output test_playback.webm

# 7. Clean up
rm test_video.webm test_playback.webm
curl -X DELETE http://localhost:4100/api/sessions/$SESSION_ID

echo "Integration test complete!"
```

---

## Troubleshooting

| Issue                                        | Solution                                                                     |
| -------------------------------------------- | ---------------------------------------------------------------------------- |
| Connection refused                           | Check server is running: `./start.sh`                                        |
| Auth failed                                  | Check `.env` has `ALLOWED_DEVICE_KEYS=firefighter_pi_001` or leave empty     |
| No windows created                           | Send data for at least 1 second (500ms window size)                          |
| Qdrant not running                           | `docker start qdrant`                                                        |
| "OSError: Read-only file system" (video)     | Update `.env` with `VIDEO_STORAGE_PATH=./data/videos` and restart server    |
| Video playback not working in browser        | Verify Flask CORS configuration includes video endpoints                     |
| "Video file not found on disk"               | Check `data/videos/` directory and `session.video_file_path` match           |
| Video upload returns 400                     | Check video file size < 500 MB (see `VIDEO_MAX_SIZE_MB` in `.env`)          |
| Video streaming shows 404                    | Verify session has `video_file_path` field and file exists in `data/videos/` |
