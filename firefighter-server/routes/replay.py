"""Session replay endpoints."""

from flask import Blueprint, request, jsonify

from app_state import AppState

replay_bp = Blueprint('replay', __name__)


@replay_bp.route("/sessions/<session_id>/replay", methods=["GET"])
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
    repo = AppState.get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    try:
        offset = int(request.args.get("offset", 0))
        limit = min(int(request.args.get("limit", 20)), 100)
    except ValueError:
        return jsonify({"error": "Invalid offset or limit parameter"}), 400

    store = AppState.get_vector_store()
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


@replay_bp.route("/sessions/<session_id>/windows", methods=["GET"])
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
    repo = AppState.get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    store = AppState.get_vector_store()
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


@replay_bp.route("/sessions/<session_id>/poses", methods=["GET"])
def get_session_poses(session_id):
    """
    Get all pose windows for a session.

    Query params:
        include_raw: Include raw keypoint data (default: false)

    Returns:
        [
            {
                "id": str,
                "start_time": timestamp,
                "end_time": timestamp,
                "pose_count": int,
                "detected_activity": str or null,
                "raw_poses": [...] (if include_raw=true)
            },
            ...
        ]
    """
    repo = AppState.get_session_repo()
    session = repo.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    include_raw = request.args.get("include_raw", "false").lower() == "true"

    pose_store = AppState.get_pose_store()
    poses = pose_store.get_session_poses(session_id, include_raw=include_raw)

    return jsonify(poses)
