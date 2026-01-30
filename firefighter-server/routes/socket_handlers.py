"""Socket.IO event handlers for IoT device communication.

Handles connections, authentication, and sensor data from Raspberry Pi devices.
"""

import logging
from datetime import datetime

from flask import request
from flask_socketio import emit, disconnect

from app_state import AppState
from lib.constants import SOCKETIO_NAMESPACE

logger = logging.getLogger(__name__)


def register_socket_handlers(socketio):
    """Register all Socket.IO event handlers with the SocketIO instance."""

    @socketio.on("connect", namespace=SOCKETIO_NAMESPACE)
    def handle_connect():
        """Handle client connection."""
        logger.info(f"[Socket.IO] Client connected: {request.sid}")

    @socketio.on("disconnect", namespace=SOCKETIO_NAMESPACE)
    def handle_disconnect():
        """Handle client disconnection."""
        logger.info(f"[Socket.IO] Client disconnected: {request.sid}")

    @socketio.on("authenticate", namespace=SOCKETIO_NAMESPACE)
    def handle_authenticate(data):
        """
        Handle device authentication.

        Expected data: {"device_key": "firefighter_pi_001"}
        """
        device_key = data.get("device_key", "")

        if AppState.config.auth.is_valid_device(device_key):
            logger.info(f"[Socket.IO] Device authenticated: {device_key}")
            emit("auth_success", {
                "device_key": device_key,
                "session_id": AppState.current_session_id
            })
        else:
            logger.info(f"[Socket.IO] Authentication failed: {device_key}")
            emit("auth_error", {"message": "Invalid device key"})
            disconnect()

    @socketio.on("foot_pressure_data", namespace=SOCKETIO_NAMESPACE)
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
        logger.debug(f"[Broadcast] foot_data to {SOCKETIO_NAMESPACE}")
        socketio.emit("foot_data", data, namespace=SOCKETIO_NAMESPACE)

        if not AppState.current_session_id:
            return  # No active session

        activity_label = AppState.get_current_activity_label(AppState.current_session_id)

        store = AppState.get_vector_store()
        point_id = store.add_reading(
            AppState.current_session_id, "foot", data, label=activity_label
        )

        if point_id:
            logger.info(f"[Qdrant] Stored foot window: {point_id} (label: {activity_label})")

    @socketio.on("accelerometer_data", namespace=SOCKETIO_NAMESPACE)
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
        logger.debug(f"[Broadcast] accel_data to {SOCKETIO_NAMESPACE}")
        socketio.emit("accel_data", data, namespace=SOCKETIO_NAMESPACE)

        if not AppState.current_session_id:
            return  # No active session

        activity_label = AppState.get_current_activity_label(AppState.current_session_id)

        store = AppState.get_vector_store()
        point_id = store.add_reading(
            AppState.current_session_id, "accel", data, label=activity_label
        )

        if point_id:
            logger.info(f"[Qdrant] Stored accel window: {point_id} (label: {activity_label})")

    @socketio.on("activity_detected", namespace=SOCKETIO_NAMESPACE)
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
        session_id = data.get("session_id")
        activity = data.get("activity")
        confidence = data.get("confidence", 0)

        if not session_id or not activity:
            return

        # Store current detected activity in memory
        AppState.detected_activities[session_id] = {
            "activity": activity,
            "confidence": confidence,
            "timestamp": datetime.utcnow()
        }

        logger.info(
            f"[Activity] Detected: {activity} ({confidence}%) for session {session_id}"
        )

    @socketio.on("pose_data", namespace=SOCKETIO_NAMESPACE)
    def handle_pose_data(data):
        """
        Handle ml5 pose keypoint data from frontend.

        Expected data: {
            "session_id": "uuid",
            "timestamp": float (ms),
            "keypoints": [
                {"name": "nose", "x": 320, "y": 100, "confidence": 0.95},
                {"name": "left_eye", "x": 310, "y": 95, "confidence": 0.92},
                ...  (17 keypoints total)
            ],
            "detected_activity": "Standing" (optional)
        }
        """
        try:
            session_id = data.get("session_id")
            timestamp_ms = data.get("timestamp")
            keypoints = data.get("keypoints", [])
            detected_activity = data.get("detected_activity")

            if not session_id:
                return

            # Check if there's an active session and it matches
            # This prevents race conditions when session is being stopped
            if not AppState.current_session_id:
                return  # No active session

            if session_id != AppState.current_session_id:
                return  # Stale pose data for a stopped session

            # If no activity provided, get from current detected activities
            if not detected_activity:
                detected_activity = AppState.get_current_activity_label(session_id)

            pose_store = AppState.get_pose_store()
            point_id = pose_store.add_pose(
                session_id=session_id,
                pose_data={"keypoints": keypoints},
                timestamp_ms=timestamp_ms,
                detected_activity=detected_activity,
            )

            if point_id:
                logger.info(f"[Pose] Stored pose window: {point_id} (activity: {detected_activity})")

        except Exception as e:
            logger.error(f"[Pose] Error storing pose data: {e}")
            # Don't crash the handler - pose collection is supplementary to sensor data
