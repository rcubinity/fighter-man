"""Health check and activity types endpoints."""

from flask import Blueprint, jsonify

from app_state import AppState
from lib.constants import ACTIVITY_TYPES

health_bp = Blueprint('health', __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Server health check."""
    store = AppState.get_vector_store()
    qdrant_sensor_health = store.health_check()

    pose_store = AppState.get_pose_store()
    qdrant_pose_health = pose_store.health_check()

    database = AppState.get_database()
    postgres_health = database.health_check()

    return jsonify({
        "status": "healthy" if all([
            qdrant_sensor_health["status"] == "healthy",
            qdrant_pose_health["status"] == "healthy",
            postgres_health["status"] == "healthy"
        ]) else "degraded",
        "server": "running",
        "qdrant_sensors": qdrant_sensor_health,
        "qdrant_poses": qdrant_pose_health,
        "postgres": postgres_health,
        "active_session": AppState.current_session_id,
    })


@health_bp.route("/api/activity-types", methods=["GET"])
def get_activity_types():
    """Get list of valid activity types for Stage 1."""
    return jsonify(ACTIVITY_TYPES)
