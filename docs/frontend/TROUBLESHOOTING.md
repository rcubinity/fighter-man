# Troubleshooting Guide

This guide helps you resolve common issues with the frontend recording and replay application.

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Camera Issues](#camera-issues)
3. [Recording Issues](#recording-issues)
4. [Upload Issues](#upload-issues)
5. [Replay Issues](#replay-issues)
6. [Browser Console Errors](#browser-console-errors)

---

## Connection Issues

### "Disconnected" Status in Header

**Problem:** Top-right corner shows "Disconnected" in red

**Possible Causes:**
- Server not running
- Wrong server URL
- Network connectivity issues
- Firewall blocking Socket.IO

**Solutions:**

**1. Check Server is Running:**
```bash
# Visit health endpoint
curl http://localhost:4100/health

# Should return: {"status": "ok", ...}
```

**2. Verify Server URL:**
- Check `SERVER_URL` in code matches actual server
- Default: `http://localhost:4100`
- Production: Update to production server address

**3. Check Network:**
```bash
# Ping server
ping localhost

# Check port is open
netstat -an | grep 4100
```

**4. Check Browser Console:**
- Press `F12` to open Developer Tools
- Check "Console" tab for connection errors
- Look for "Socket.IO" or "WebSocket" errors

**5. Try Different Browser:**
- Some browsers block WebSocket connections
- Try Chrome (most reliable)

---

## Camera Issues

### "Camera Permission Denied"

**Problem:** Browser blocks camera access

**Solutions:**

**1. Grant Permission:**
- Click the **lock icon** (🔒) in address bar
- Find "Camera" permission
- Change to "Allow"
- Refresh the page

**2. Browser Settings:**

**Chrome:**
1. Settings → Privacy and Security → Site Settings
2. Camera → Check permissions
3. Ensure site is not in "Blocked" list

**Firefox:**
1. Settings → Privacy & Security → Permissions
2. Camera → Settings
3. Remove site from blocked list if present

**Safari:**
1. Safari → Settings for This Website
2. Camera → Allow

**3. System Permissions (macOS):**
1. System Preferences → Security & Privacy
2. Privacy tab → Camera
3. Ensure browser has camera access checked

### "No Camera Found"

**Problem:** Browser can't detect camera

**Solutions:**

**1. Check Camera is Connected:**
- For external webcam: Verify USB cable is plugged in
- For integrated camera: May be disabled in BIOS

**2. Close Other Applications:**
Camera can only be used by one app at a time:
- Close Zoom, Teams, Skype, FaceTime
- Close other browser tabs using camera
- Restart browser if needed

**3. Try Different Camera:**
```javascript
// Check available cameras
navigator.mediaDevices.enumerateDevices()
  .then(devices => {
    const cameras = devices.filter(d => d.kind === 'videoinput');
    console.log('Available cameras:', cameras);
  });
```

**4. Restart Computer:**
- Sometimes camera driver gets stuck
- Restart resolves most hardware issues

### "MediaRecorder Not Supported"

**Problem:** Browser doesn't support video recording

**Solutions:**

**1. Update Browser:**
- Chrome: Update to version 90+
- Firefox: Update to version 88+
- Safari: Update to version 14.1+
- Edge: Update to version 90+

**2. Use Supported Browser:**
- Chrome 90+ (Recommended)
- Firefox 88+
- Safari 14.1+ (Limited WebM support)
- **NOT** Internet Explorer (never supported)

**3. Enable Experimental Features (if needed):**
- Chrome: `chrome://flags` → Search "MediaRecorder"
- Enable any experimental MediaRecorder flags

### Camera Preview Frozen or Black

**Problem:** Video preview shows black screen or is frozen

**Solutions:**

**1. Check Camera LED:**
- Most cameras have an LED when active
- If LED is off, camera may not be receiving power

**2. Refresh Page:**
- Simple refresh often fixes frozen preview
- Hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)

**3. Disconnect and Reconnect:**
- For external webcams: Unplug USB, wait 5 seconds, plug back in
- Refresh browser page after reconnecting

**4. Check Camera Settings:**
- Some cameras have physical privacy shutters
- Check camera isn't covered or blocked

---

## Recording Issues

### "No Sensor Data Appearing"

**Problem:** Foot/Accel reading counters stay at 0

**Solutions:**

**1. Check Raspberry Pi:**
```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Check sensor-hub is running
ps aux | grep sensor-hub
```

**2. Verify Socket.IO Connection:**
- Check status in top-right: Should say "Connected" in green
- If red "Disconnected", see [Connection Issues](#connection-issues)

**3. Check Server Logs:**
```bash
# In firefighter-server directory
tail -f server.log

# Look for:
# - "foot_pressure_data" events
# - "accelerometer_data" events
```

**4. Restart Sensor Hub:**
```bash
# On Raspberry Pi
sudo systemctl restart sensor-hub
# OR
cd sensor-hub
python3 main.py
```

### Activity Detection Shows "Waiting..."

**Problem:** Activity never detected, always shows "Waiting..."

**Solutions:**

**1. Ensure Both Data Types Streaming:**
- Activity detector needs BOTH foot pressure AND accelerometer data
- Check both counters are incrementing

**2. Move to Trigger Detection:**
- Standing perfectly still may not trigger detection
- Try moving, bending, or sitting to trigger classification

**3. Check Confidence Threshold:**
- Low confidence (<60%) shows as "Waiting..."
- May indicate transitional movement or unusual posture

**4. Verify Sensor Pairing:**
- Sensors must be paired via Bluetooth
- Check sensor-hub logs for pairing status

---

## Upload Issues

### "Upload Failed" Error

**Problem:** Video doesn't upload after stopping recording

**Solutions:**

**1. Check Network Connection:**
```bash
# Ping server
ping localhost

# Check server is responding
curl http://localhost:4100/health
```

**2. Verify Server Has Disk Space:**
```bash
# On server
df -h /app/data/videos

# Should show available space
```

**3. Try Uploading Again:**
- Video is kept in browser memory
- Click upload button again (if available)
- Or restart recording (video will be lost)

**4. Check Video Size:**
```javascript
// In browser console
console.log('Video size:', (videoRecorder.videoBlob.size / (1024 * 1024)).toFixed(2), 'MB');

// Must be < 500 MB
```

**5. Check Server Logs:**
```bash
# Server may show specific error
tail -f server.log
```

### Upload Progress Stuck at X%

**Problem:** Upload progress bar freezes

**Solutions:**

**1. Wait Longer:**
- Large files take time (500 MB ≈ 2-5 minutes on slow connection)
- Check network speed: `speedtest.net`

**2. Check Network Stability:**
- WiFi may be dropping packets
- Try wired connection if possible
- Move closer to WiFi router

**3. Check Server Load:**
- Server may be processing other requests
- Check server CPU/memory usage

**4. Last Resort - Refresh:**
- If truly stuck (>10 minutes), refresh page
- ⚠️ **Warning:** Video will be lost, must record again

### "Video File Too Large"

**Problem:** Video exceeds server upload limit

**Solutions:**

**1. Reduce Recording Duration:**
- Server limit: 500 MB (roughly 30-40 minutes at HD quality)
- Split longer sessions into multiple recordings

**2. Contact Administrator:**
- Admin can increase `VIDEO_MAX_SIZE_MB` in server .env
- Requires server restart

**3. Reduce Quality (Future):**
- Currently not configurable from UI
- Developer can modify `videoRecorder.js` bitrate setting

---

## Replay Issues

### "Failed to Load Session for Replay"

**Problem:** Error message when clicking session name

**Solutions:**

**1. Check Browser Console:**
```
Press F12 → Console tab
Look for specific error message
```

**2. Verify Session Exists:**
```bash
# Check session in database
curl http://localhost:4100/api/sessions/{session_id}
```

**3. Check Session Data Integrity:**
- Session may be corrupted
- Try deleting and re-recording

**4. Refresh Page:**
- Clear browser cache: `Ctrl+Shift+Delete`
- Hard refresh: `Ctrl+Shift+R`

### Video Not Playing

**Problem:** Video element shows but doesn't play

**Solutions:**

**1. Check Video File Exists:**
```bash
# On server
ls -lh /app/data/videos/{session_id}.webm

# Should show file with size
```

**2. Verify Browser Supports WebM:**
```javascript
// In browser console
document.createElement('video').canPlayType('video/webm')

// Should return: "probably" or "maybe"
```

**3. Check Network Streaming:**
```bash
# Try downloading video
curl http://localhost:4100/api/sessions/{session_id}/video -o test.webm

# Check file size
ls -lh test.webm
```

**4. Try Different Browser:**
- Safari has limited WebM support
- Use Chrome or Firefox

### Video Out of Sync with Sensors

**Problem:** Video ahead or behind sensor data by several seconds

**Solutions:**

**1. Small Drift (<2s) is Normal:**
- System auto-corrects drift >2 seconds
- Small drift is allowed for smoother playback

**2. Check Timestamp Alignment:**
```javascript
// In browser console during replay
console.log('Session start:', session.created_at);
console.log('Video time:', replayVideo.currentTime);
console.log('Expected time:', (Date.now() - replayStartTime) / 1000);
```

**3. Verify Session Timestamps:**
- `session.created_at` should match video recording start
- If mismatched, re-record session

**4. Report Persistent Issues:**
- Large persistent drift (>5s) may indicate bug
- Report to developer with session ID

### Timeline Not Showing Activities

**Problem:** Timeline shows time markers but no colored activity segments

**Solutions:**

**1. Check Activity Detection During Recording:**
- Activities may not have been detected
- Verify sensor data was streaming during recording

**2. Verify Sensor Windows Exist:**
```bash
# Check session has data
curl http://localhost:4100/api/sessions/{session_id}/windows

# Should return array of windows with activities
```

**3. Check Window Metadata:**
- Each window should have `activity` and `confidence` fields
- If missing, activity detection failed during recording

**4. Re-record Session:**
- If no activities detected, re-record with verified sensors

---

## Browser Console Errors

### How to Access Console

**Chrome/Edge:**
1. Press `F12` or `Ctrl+Shift+I`
2. Click "Console" tab

**Firefox:**
1. Press `F12` or `Ctrl+Shift+K`
2. Console appears at bottom

**Safari:**
1. Enable Developer menu: Preferences → Advanced → Show Develop menu
2. Develop → Show JavaScript Console

### Common Error Messages

#### CORS Error

```
Access to fetch at 'http://localhost:4100/api/sessions' from origin 'null'
has been blocked by CORS policy
```

**Cause:** Server CORS configuration issue
**Solution:** Contact administrator to enable CORS for frontend origin

#### 404 Not Found

```
GET http://localhost:4100/api/sessions/abc-123 404 (Not Found)
```

**Cause:** Session or resource doesn't exist
**Solution:** Check session ID is correct, or session may have been deleted

#### TypeError: Cannot read property 'X' of null

```
TypeError: Cannot read property 'video_file_path' of null
```

**Cause:** JavaScript error, expected data missing
**Solution:** Report to developer with full error stack trace

#### Network Error

```
Failed to fetch
net::ERR_CONNECTION_REFUSED
```

**Cause:** Server not reachable
**Solution:** Check server is running and URL is correct

---

## Getting Further Help

If issues persist after trying these solutions:

**1. Gather Information:**
- Browser name and version
- Operating system
- Error messages from console (screenshot or copy-paste)
- Steps to reproduce the issue

**2. Check Server Logs:**
```bash
# In firefighter-server directory
tail -100 server.log
```

**3. Check Network Logs:**
- F12 → Network tab
- Filter by "XHR" or "WS" (WebSocket)
- Look for failed requests (red text)

**4. Report Issue:**
- Contact project administrator
- Provide gathered information
- Include session ID if issue is session-specific

---

**Document Version:** 1.0
**Last Updated:** December 24, 2025
