"""Session CRUD endpoints."""

import logging
from datetime import datetime

from flask import Blueprint, request, jsonify

from app_state import AppState
from lib.constants import ACTIVITY_TYPES, SOCKETIO_NAMESPACE

logger = logging.getLogger(__name__)

sessions_bp = Blueprint('sessions', __name__)

# Reference to socketio instance, set by server.py
_socketio = None


def init_socketio(socketio):
    """Initialize the socketio reference for emitting events."""
    global _socketio
    _socketio = socketio


@sessions_bp.route("/sessions", methods=["POST"])
def create_session():
    """
    Create a new recording session.

    Request body: {
        "name": "optional session name",
        "activity_type": "Walking"  # Required for Stage 1
    }
    """
    data = request.get_json() or {}
    session_name = data.get(
        "name", f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
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

    repo = AppState.get_session_repo()

    # Auto-stop any existing active session
    active_session = repo.get_active()
    if active_session:
        store = AppState.get_vector_store()
        store.flush_session(active_session.id)
        pose_store = AppState.get_pose_store()
        pose_store.flush_session(active_session.id)
        repo.update(active_session.id, status="stopped", stopped_at=datetime.utcnow())
        logger.info(f"[Session] Auto-stopped: {active_session.id}")

    # Create new session
    session = repo.create(name=session_name, activity_type=activity_type)
    AppState.current_session_id = session.id

    # DEBUG: Log created session
    logger.debug(f"[DEBUG] Created session object:")
    logger.debug(f"[DEBUG]   session.id: {session.id}")
    logger.debug(f"[DEBUG]   session.activity_type: {session.activity_type}")

    logger.info(
        f"[Session] Created: {session.id} ({session.name}) - Activity: {activity_type}"
    )

    # Notify connected clients
    if _socketio:
        _socketio.emit(
            "session_started",
            {
                "session_id": session.id,
                "name": session.name,
                "activity_type": activity_type
            },
            namespace=SOCKETIO_NAMESPACE,
        )
    else:
        logger.warning("[Session] Cannot emit session_started - socketio not initialized")

    return jsonify(session.to_dict()), 201


@sessions_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """List all sessions."""
    repo = AppState.get_session_repo()
    sessions = repo.list_all()
    return jsonify([s.to_dict() for s in sessions])


@sessions_bp.route("/sessions/active", methods=["GET"])
def get_active_session():
    """Get the currently active recording session."""
    repo = AppState.get_session_repo()
    session = repo.get_active()
    return jsonify(session.to_dict() if session else None)


@sessions_bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    """Get session details."""
    repo = AppState.get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    store = AppState.get_vector_store()
    windows = store.get_session_data(session_id, include_raw=False)

    session_info = session.to_dict()
    session_info["window_count"] = len(windows)
    session_info["windows"] = windows

    return jsonify(session_info)


@sessions_bp.route("/sessions/<session_id>", methods=["PUT"])
def update_session(session_id):
    """
    Update session (labels, name, status).

    Request body: {
        "name": "new name",
        "status": "completed",
        "labels": {"window_id": "Walking", ...}
    }
    """
    repo = AppState.get_session_repo()
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
        store = AppState.get_vector_store()
        store.update_labels(session_id, data["labels"])

    return jsonify(updated.to_dict())


@sessions_bp.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """Delete a session and all its data."""
    repo = AppState.get_session_repo()
    if not repo.get(session_id):
        return jsonify({"error": "Session not found"}), 404

    # Delete sensor data
    store = AppState.get_vector_store()
    sensor_deleted = store.delete_session(session_id)

    # Delete pose data
    pose_store = AppState.get_pose_store()
    pose_deleted = pose_store.delete_session_poses(session_id)

    repo.delete(session_id)

    if AppState.current_session_id == session_id:
        AppState.current_session_id = None

    return jsonify({
        "message": "Session deleted",
        "sensor_windows_deleted": sensor_deleted,
        "pose_windows_deleted": pose_deleted,
    })


@sessions_bp.route("/sessions/<session_id>/stop", methods=["POST"])
def stop_session(session_id):
    """Stop the current recording session."""
    repo = AppState.get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Flush remaining sensor data
    store = AppState.get_vector_store()
    store.flush_session(session_id)

    # Flush remaining pose data
    pose_store = AppState.get_pose_store()
    pose_store.flush_session(session_id)

    updated = repo.update(session_id, status="stopped", stopped_at=datetime.utcnow())

    # Clean up detected activities for this session
    if session_id in AppState.detected_activities:
        del AppState.detected_activities[session_id]

    if AppState.current_session_id == session_id:
        AppState.current_session_id = None

    # Notify connected clients
    if _socketio:
        _socketio.emit(
            "session_stopped",
            {"session_id": session_id},
            namespace=SOCKETIO_NAMESPACE,
        )
    else:
        logger.warning("[Session] Cannot emit session_stopped - socketio not initialized")

    return jsonify(updated.to_dict())
