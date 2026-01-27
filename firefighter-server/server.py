#!/usr/bin/env python3
"""Firefighter Server - Socket.IO + REST API for sensor data collection.

Receives sensor data from Raspberry Pi via Socket.IO and stores in Qdrant.
Provides REST API for session management and data export.
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from flask import Flask, request, jsonify, send_file, Response
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS
from werkzeug.utils import secure_filename

from lib.config import Config
from lib.vector_store import VectorStore
from lib.database import Database, SessionRepository
from lib.constants import ACTIVITY_TYPES

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
config = Config.from_env()
app.config["SECRET_KEY"] = config.server.secret_key

# Enable CORS for all origins including 'null' (file:// protocol)
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]}})

# Initialize Socket.IO
# Using threading mode for development stability
# For production with high concurrency, use gevent or eventlet
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    logger=False,
    engineio_logger=False,
)

# Initialize Qdrant vector store
vector_store: VectorStore = None

# Initialize PostgreSQL database
db: Database = None
session_repo: SessionRepository = None

# Session management
current_session_id: str = None

# Track currently detected activity per session (from frontend detector)
detected_activities: Dict[str, Dict[str, Any]] = {}

# ACTIVITY_TYPES imported from lib/constants.py


def get_vector_store() -> VectorStore:
    """Get or create vector store instance."""
    global vector_store
    if vector_store is None:
        vector_store = VectorStore(config.qdrant)
    return vector_store


def get_database() -> Database:
    """Get or create database instance."""
    global db
    if db is None:
        db = Database(config.postgres)
    return db


def get_session_repo() -> SessionRepository:
    """Get or create session repository instance."""
    global session_repo
    if session_repo is None:
        session_repo = SessionRepository(get_database())
    return session_repo


def get_current_activity_label(session_id: str) -> Optional[str]:
    """
    Get activity label for a session.

    Prioritizes frontend-detected activity over session default.

    Args:
        session_id: Session ID to get activity for

    Returns:
        Activity label string or None
    """
    if session_id in detected_activities:
        return detected_activities[session_id]["activity"]

    repo = get_session_repo()
    session = repo.get(session_id)
    return session.activity_type if session else None


# ============================================================
# Socket.IO Event Handlers
# ============================================================

@socketio.on("connect", namespace="/iot")
def handle_connect():
    """Handle client connection."""
    logger.info(f"[Socket.IO] Client connected: {request.sid}")


@socketio.on("disconnect", namespace="/iot")
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"[Socket.IO] Client disconnected: {request.sid}")


@socketio.on("authenticate", namespace="/iot")
def handle_authenticate(data):
    """
    Handle device authentication.

    Expected data: {"device_key": "firefighter_pi_001"}
    """
    device_key = data.get("device_key", "")

    if config.auth.is_valid_device(device_key):
        logger.info(f"[Socket.IO] Device authenticated: {device_key}")
        emit("auth_success", {"device_key": device_key, "session_id": current_session_id})
    else:
        logger.info(f"[Socket.IO] Authentication failed: {device_key}")
        emit("auth_error", {"message": "Invalid device key"})
        disconnect()


@socketio.on("foot_pressure_data", namespace="/iot")
def handle_foot_data(data):
    """
    Handle foot pressure sensor data.

    Expected data: {
        "timestamp": "ISO datetime",
        "device": "LEFT_FOOT" or "RIGHT_FOOT",
        "data": {
            "foot": "LEFT" or "RIGHT",
            "max": float,
            "avg": float,
            "active_count": int,
            "values": [18 floats]
        }
    }
    """
    # Broadcast to UI clients for live display
    logger.debug(f"[Broadcast] foot_data to /iot")
    socketio.emit("foot_data", data, namespace="/iot")

    if not current_session_id:
        return  # No active session

    activity_label = get_current_activity_label(current_session_id)

    store = get_vector_store()
    point_id = store.add_reading(current_session_id, "foot", data, label=activity_label)

    if point_id:
        logger.info(f"[Qdrant] Stored foot window: {point_id} (label: {activity_label})")


@socketio.on("accelerometer_data", namespace="/iot")
def handle_accel_data(data):
    """
    Handle accelerometer sensor data.

    Expected data: {
        "timestamp": "ISO datetime",
        "device": "ACCELEROMETER",
        "data": {
            "acc": {"x": float, "y": float, "z": float},
            "gyro": {"x": float, "y": float, "z": float},
            "angle": {"roll": float, "pitch": float, "yaw": float}
        }
    }
    """
    # Broadcast to UI clients for live display
    logger.debug(f"[Broadcast] accel_data to /iot")
    socketio.emit("accel_data", data, namespace="/iot")

    if not current_session_id:
        return  # No active session

    activity_label = get_current_activity_label(current_session_id)

    store = get_vector_store()
    point_id = store.add_reading(current_session_id, "accel", data, label=activity_label)

    if point_id:
        logger.info(f"[Qdrant] Stored accel window: {point_id} (label: {activity_label})")


@socketio.on("activity_detected", namespace="/iot")
def handle_activity_detected(data):
    """
    Handle activity detected from frontend activity detector.

    Expected data: {
        "session_id": "uuid",
        "activity": "Standing",
        "confidence": 85,
        "timestamp": "ISO datetime"
    }
    """
    global detected_activities

    session_id = data.get("session_id")
    activity = data.get("activity")
    confidence = data.get("confidence", 0)

    if not session_id or not activity:
        return

    # Store current detected activity in memory
    detected_activities[session_id] = {
        "activity": activity,
        "confidence": confidence,
        "timestamp": datetime.utcnow()
    }

    logger.info(f"[Activity] Detected: {activity} ({confidence}%) for session {session_id}")


# ============================================================
# REST API - Health
# ============================================================

@app.route("/health", methods=["GET"])
def health_check():
    """Server health check."""
    store = get_vector_store()
    qdrant_health = store.health_check()

    database = get_database()
    postgres_health = database.health_check()

    return jsonify({
        "status": "healthy" if all([
            qdrant_health["status"] == "healthy",
            postgres_health["status"] == "healthy"
        ]) else "degraded",
        "server": "running",
        "qdrant": qdrant_health,
        "postgres": postgres_health,
        "active_session": current_session_id,
    })


# ============================================================
# REST API - Activity Types
# ============================================================

@app.route("/api/activity-types", methods=["GET"])
def get_activity_types():
    """Get list of valid activity types for Stage 1."""
    return jsonify(ACTIVITY_TYPES)


# ============================================================
# REST API - Sessions
# ============================================================

@app.route("/api/sessions", methods=["POST"])
def create_session():
    """
    Create a new recording session.

    Request body: {
        "name": "optional session name",
        "activity_type": "Walking"  # Required for Stage 1
    }
    """
    global current_session_id

    data = request.get_json() or {}
    session_name = data.get("name", f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    activity_type = data.get("activity_type")

    # DEBUG: Log received data
    logger.debug(f"[DEBUG] Received session creation request:")
    logger.debug(f"[DEBUG]   Raw data: {data}")
    logger.debug(f"[DEBUG]   session_name: {session_name}")
    logger.debug(f"[DEBUG]   activity_type: {activity_type}")

    # Validate activity_type
    if activity_type and activity_type not in ACTIVITY_TYPES:
        return jsonify({
            "error": f"Invalid activity_type. Must be one of: {ACTIVITY_TYPES}"
        }), 400

    repo = get_session_repo()

    # Auto-stop any existing active session
    active_session = repo.get_active()
    if active_session:
        store = get_vector_store()
        store.flush_session(active_session.id)
        repo.update(active_session.id, status="stopped", stopped_at=datetime.utcnow())
        logger.info(f"[Session] Auto-stopped: {active_session.id}")

    # Create new session
    session = repo.create(name=session_name, activity_type=activity_type)
    current_session_id = session.id

    # DEBUG: Log created session
    logger.debug(f"[DEBUG] Created session object:")
    logger.debug(f"[DEBUG]   session.id: {session.id}")
    logger.debug(f"[DEBUG]   session.activity_type: {session.activity_type}")

    logger.info(f"[Session] Created: {session.id} ({session.name}) - Activity: {activity_type}")

    # Notify connected clients
    socketio.emit(
        "session_started",
        {"session_id": session.id, "name": session.name, "activity_type": activity_type},
        namespace="/iot",
    )

    return jsonify(session.to_dict()), 201


@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    """List all sessions."""
    repo = get_session_repo()
    sessions = repo.list_all()
    return jsonify([s.to_dict() for s in sessions])


@app.route("/api/sessions/active", methods=["GET"])
def get_active_session():
    """Get the currently active recording session."""
    repo = get_session_repo()
    session = repo.get_active()
    return jsonify(session.to_dict() if session else None)


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    """Get session details."""
    repo = get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    store = get_vector_store()
    windows = store.get_session_data(session_id, include_raw=False)

    session_info = session.to_dict()
    session_info["window_count"] = len(windows)
    session_info["windows"] = windows

    return jsonify(session_info)


@app.route("/api/sessions/<session_id>", methods=["PUT"])
def update_session(session_id):
    """
    Update session (labels, name, status).

    Request body: {
        "name": "new name",
        "status": "completed",
        "labels": {"window_id": "Walking", ...}
    }
    """
    repo = get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    data = request.get_json() or {}

    # Update session metadata in database
    updated = repo.update(
        session_id,
        name=data.get("name"),
        status=data.get("status")
    )

    # Update labels in Qdrant
    if "labels" in data:
        store = get_vector_store()
        store.update_labels(session_id, data["labels"])

    return jsonify(updated.to_dict())


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """Delete a session and all its data."""
    global current_session_id

    repo = get_session_repo()
    if not repo.get(session_id):
        return jsonify({"error": "Session not found"}), 404

    store = get_vector_store()
    deleted_count = store.delete_session(session_id)
    repo.delete(session_id)

    if current_session_id == session_id:
        current_session_id = None

    return jsonify({
        "message": "Session deleted",
        "windows_deleted": deleted_count,
    })


@app.route("/api/sessions/<session_id>/stop", methods=["POST"])
def stop_session(session_id):
    """Stop the current recording session."""
    global current_session_id

    repo = get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Flush remaining data
    store = get_vector_store()
    store.flush_session(session_id)

    updated = repo.update(session_id, status="stopped", stopped_at=datetime.utcnow())

    # Clean up detected activities for this session
    if session_id in detected_activities:
        del detected_activities[session_id]

    if current_session_id == session_id:
        current_session_id = None

    # Notify connected clients
    socketio.emit(
        "session_stopped",
        {"session_id": session_id},
        namespace="/iot",
    )

    return jsonify(updated.to_dict())


# ============================================================
# REST API - Export
# ============================================================

@app.route("/api/sessions/<session_id>/export", methods=["GET"])
def export_session(session_id):
    """
    Export session data for annotation tool or ML training.

    Query params:
        format: "json" (default) or "csv"
        include_raw: "true" to include raw sensor data
    """
    repo = get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    include_raw = request.args.get("include_raw", "false").lower() == "true"
    export_format = request.args.get("format", "json")

    store = get_vector_store()
    windows = store.get_session_data(session_id, include_raw=include_raw)

    if export_format == "csv":
        # Simple CSV export
        import csv
        from io import StringIO

        output = StringIO()
        if windows:
            fieldnames = ["id", "start_time", "end_time", "foot_count", "accel_count", "label"]
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(windows)

        response = app.response_class(
            response=output.getvalue(),
            status=200,
            mimetype="text/csv",
        )
        response.headers["Content-Disposition"] = f"attachment; filename={session_id}.csv"
        return response

    # JSON export (default)
    return jsonify({
        "session": session.to_dict(),
        "windows": windows,
        "window_count": len(windows),
    })


# ============================================================
# REST API - Replay
# ============================================================

@app.route("/api/sessions/<session_id>/replay", methods=["GET"])
def get_replay_data(session_id):
    """
    Get windows for replay with pagination.

    Optimized endpoint for session replay that returns windows in batches
    for efficient memory usage and smooth playback.

    Query params:
        offset: Starting window index (default: 0)
        limit: Number of windows to return (default: 20, max: 100)

    Returns:
        {
            "session": {session metadata},
            "windows": [{window with raw_data}, ...],
            "total_windows": int,
            "offset": int,
            "limit": int,
            "has_more": bool
        }
    """
    repo = get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    offset = int(request.args.get("offset", 0))
    limit = min(int(request.args.get("limit", 20)), 100)

    store = get_vector_store()
    all_windows = store.get_session_data(session_id, include_raw=True)

    # Paginate windows
    windows = all_windows[offset:offset + limit]

    return jsonify({
        "session": session.to_dict(),
        "windows": windows,
        "total_windows": len(all_windows),
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < len(all_windows)
    })


@app.route("/api/sessions/<session_id>/windows", methods=["GET"])
def get_session_windows_metadata(session_id):
    """
    Get all windows metadata for a session (without raw_data).

    Lightweight endpoint for timeline rendering that returns window metadata
    including labels, timestamps, but excludes heavy raw_data field.

    Returns:
        [
            {
                "window_id": str,
                "session_id": str,
                "label": str or null,
                "start_time": timestamp,
                "end_time": timestamp,
                "foot_count": int,
                "accel_count": int
            },
            ...
        ]
    """
    repo = get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    store = get_vector_store()
    # Get all windows without raw_data (lightweight)
    all_windows = store.get_session_data(session_id, include_raw=False)

    # Normalize field names to match frontend expectations
    normalized = [
        {
            "window_id": w.get("id"),
            "session_id": session_id,
            "label": w.get("label"),
            "start_time": w.get("start_time"),
            "end_time": w.get("end_time"),
            "foot_count": w.get("foot_count"),
            "accel_count": w.get("accel_count"),
        }
        for w in all_windows
    ]

    return jsonify(normalized)


# ============================================================
# REST API - Query (Similarity Search)
# ============================================================

@app.route("/api/query/similar", methods=["POST"])
def query_similar():
    """
    Find similar sensor patterns.

    Request body: {
        "window_id": "id of reference window",
        "session_id": "optional filter by session",
        "label": "optional filter by label",
        "limit": 10
    }
    """
    data = request.get_json() or {}
    window_id = data.get("window_id")
    session_filter = data.get("session_id")
    label_filter = data.get("label")
    limit = data.get("limit", 10)

    if not window_id:
        return jsonify({"error": "window_id is required"}), 400

    store = get_vector_store()

    # Get the reference window's vector
    try:
        points = store.client.retrieve(
            collection_name=store.config.collection,
            ids=[window_id],
            with_vectors=True,
        )
        if not points:
            return jsonify({"error": "Window not found"}), 404

        reference_vector = points[0].vector
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Search for similar
    results = store.query_similar(
        vector=reference_vector,
        limit=limit + 1,  # +1 because result may include the reference
        session_id=session_filter,
        label=label_filter,
    )

    # Remove the reference window from results
    results = [r for r in results if r["id"] != window_id][:limit]

    return jsonify({
        "reference_id": window_id,
        "similar_windows": results,
    })


@app.route("/api/sessions/<session_id>/upload-video", methods=["POST"])
def upload_session_video(session_id):
    """
    Upload video file for a session.

    Expects multipart/form-data with 'video' file.
    Stores video file on disk and updates session record.
    """
    # Check if video file is in request
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    # Validate session exists
    repo = get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Get video storage path from environment, resolve relative to BASE_DIR
    video_storage_path = os.getenv('VIDEO_STORAGE_PATH', './data/videos')
    if not os.path.isabs(video_storage_path):
        video_storage_path = os.path.join(BASE_DIR, video_storage_path)

    # Create videos directory if it doesn't exist
    os.makedirs(video_storage_path, exist_ok=True)

    # Save with session_id as filename
    filename = f"{session_id}.webm"
    file_path = os.path.join(video_storage_path, filename)

    try:
        video_file.save(file_path)
        file_size = os.path.getsize(file_path)

        # Update session record with video metadata
        repo.update(
            session_id,
            video_file_path=filename,
            video_size_bytes=file_size
        )

        logger.info(f"[Video] Uploaded for session {session_id}: {filename} ({file_size} bytes)")

        return jsonify({
            'success': True,
            'video_file_path': filename,
            'size_bytes': file_size
        }), 200

    except Exception as e:
        logger.info(f"[Video] Upload failed for session {session_id}: {str(e)}")
        return jsonify({'error': f'Failed to save video: {str(e)}'}), 500


@app.route("/api/sessions/<session_id>/video", methods=["GET"])
def get_session_video(session_id):
    """
    Stream video file for a session.

    Supports HTTP Range requests for seeking.
    Returns video/webm with appropriate headers.
    """
    # Get session and check if video exists
    repo = get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    if not session.video_file_path:
        return jsonify({'error': 'No video file for this session'}), 404

    # Get video storage path from environment, resolve relative to BASE_DIR
    video_storage_path = os.getenv('VIDEO_STORAGE_PATH', './data/videos')
    if not os.path.isabs(video_storage_path):
        video_storage_path = os.path.join(BASE_DIR, video_storage_path)
    file_path = os.path.join(video_storage_path, session.video_file_path)

    # Check if file exists on disk
    if not os.path.exists(file_path):
        logger.info(f"[Video] File not found on disk: {file_path}")
        return jsonify({'error': 'Video file not found on disk'}), 404

    # Get file size
    file_size = os.path.getsize(file_path)

    # Handle Range requests for video seeking
    range_header = request.headers.get('Range', None)

    if range_header:
        # Parse range header (format: "bytes=start-end")
        try:
            byte_range = range_header.replace('bytes=', '').split('-')
            start = int(byte_range[0]) if byte_range[0] else 0
            end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1

            # Ensure valid range
            start = max(0, start)
            end = min(end, file_size - 1)

            # Read chunk
            with open(file_path, 'rb') as f:
                f.seek(start)
                data = f.read(end - start + 1)

            # Return partial content (206)
            response = Response(data, 206, mimetype='video/webm')
            response.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
            response.headers.add('Accept-Ranges', 'bytes')
            response.headers.add('Content-Length', len(data))
            return response

        except Exception as e:
            logger.info(f"[Video] Range request failed: {str(e)}")
            # Fall through to full file response on error

    # Return full file (no range request or range parsing failed)
    return send_file(
        file_path,
        mimetype='video/webm',
        as_attachment=False,
        download_name=f"session_{session_id}.webm"
    )


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Firefighter Server")
    logger.info("=" * 60)
    logger.info(f"Host: {config.server.host}")
    logger.info(f"Port: {config.server.port}")
    logger.info(f"Debug: {config.server.debug}")
    logger.info(f"Qdrant: {config.qdrant.host}:{config.qdrant.port}")
    logger.info(f"PostgreSQL: {config.postgres.host}:{config.postgres.port}/{config.postgres.database}")
    logger.info("=" * 60)

    # Initialize vector store on startup
    get_vector_store()
    logger.info("[Qdrant] Vector store initialized")

    # Initialize database
    get_database()
    get_session_repo()
    logger.info("[Database] PostgreSQL initialized")

    # Restore active session if server restarted
    repo = get_session_repo()
    active_session = repo.get_active()
    if active_session:
        current_session_id = active_session.id
        logger.info(f"[Session] Restored active session: {current_session_id}")

    socketio.run(
        app,
        host=config.server.host,
        port=config.server.port,
        debug=config.server.debug,
        allow_unsafe_werkzeug=True,  # Required for threading mode in development
    )
