"""Qdrant storage for ml5 pose keypoint data.

Stores pose keypoints (17 body joints) in a separate collection from sensor data,
enabling ML training to correlate body positions with activity labels.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from .config import QdrantConfig
from .constants import (
    POSE_KEYPOINT_COUNT,
    POSE_VALUES_PER_KEYPOINT,
    POSE_VECTOR_DIM,
    POSE_COLLECTION_NAME,
    POSE_KEYPOINT_NAMES,
    QDRANT_SCROLL_LIMIT,
    QDRANT_TIMEOUT_SECONDS,
)


@dataclass
class PoseWindow:
    """A time window of pose keypoint data."""
    session_id: str
    start_time: float
    end_time: float
    poses: List[Dict] = field(default_factory=list)
    detected_activity: Optional[str] = None


class PoseStore:
    """Qdrant wrapper for pose keypoint data storage."""

    def __init__(self, config: QdrantConfig):
        """
        Initialize Qdrant connection for pose data.

        Args:
            config: Qdrant configuration (shared with VectorStore)
        """
        self.config = config
        self.client = QdrantClient(
            host=config.host,
            port=config.port,
            timeout=QDRANT_TIMEOUT_SECONDS
        )

        # Active windows being accumulated (keyed by session_id)
        self._active_windows: Dict[str, PoseWindow] = {}

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create pose collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if POSE_COLLECTION_NAME not in collection_names:
            self.client.create_collection(
                collection_name=POSE_COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=POSE_VECTOR_DIM,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"[PoseStore] Created collection: {POSE_COLLECTION_NAME}")
        else:
            logger.info(f"[PoseStore] Using existing collection: {POSE_COLLECTION_NAME}")

    def _normalize_vector(self, values: List[float]) -> List[float]:
        """
        Normalize a vector to unit length.

        Args:
            values: Raw vector values

        Returns:
            Normalized vector
        """
        arr = np.array(values, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    def _pose_to_vector(self, pose_data: Dict) -> List[float]:
        """
        Convert pose keypoints to a vector.

        Args:
            pose_data: Pose data with keypoints array

        Returns:
            List of POSE_VECTOR_DIM floats (51 values)
        """
        keypoints = pose_data.get("keypoints", [])
        vector = []

        for i in range(POSE_KEYPOINT_COUNT):
            if i < len(keypoints):
                kp = keypoints[i]
                vector.append(float(kp.get("x", 0.0)))
                vector.append(float(kp.get("y", 0.0)))
                vector.append(float(kp.get("confidence", 0.0)))
            else:
                # Pad missing keypoints with zeros
                vector.extend([0.0, 0.0, 0.0])

        return vector[:POSE_VECTOR_DIM]

    def _window_to_vector(self, window: PoseWindow) -> List[float]:
        """
        Convert a pose window to a vector (uses the last pose in the window).

        Args:
            window: Pose window with accumulated poses

        Returns:
            Normalized vector of POSE_VECTOR_DIM floats
        """
        if not window.poses:
            return [0.0] * POSE_VECTOR_DIM

        # Use the most recent pose in the window
        last_pose = window.poses[-1]
        vector = self._pose_to_vector(last_pose)
        return self._normalize_vector(vector)

    def add_pose(
        self,
        session_id: str,
        pose_data: Dict,
        timestamp_ms: Optional[float] = None,
        detected_activity: Optional[str] = None,
    ) -> Optional[str]:
        """
        Add a pose reading, accumulating into windows.

        Args:
            session_id: Current recording session ID
            pose_data: Pose data with keypoints array
            timestamp_ms: Timestamp in milliseconds (uses current time if not provided)
            detected_activity: Optional activity label

        Returns:
            Point ID if a window was stored, None otherwise
        """
        if not session_id:
            return None

        if timestamp_ms is None:
            timestamp_ms = time.time() * 1000

        # Get or create active window
        if session_id not in self._active_windows:
            self._active_windows[session_id] = PoseWindow(
                session_id=session_id,
                start_time=timestamp_ms,
                end_time=timestamp_ms,
                detected_activity=detected_activity,
            )

        window = self._active_windows[session_id]

        # Update activity if provided
        if detected_activity is not None:
            window.detected_activity = detected_activity

        # Add pose to window
        window.poses.append(pose_data)
        window.end_time = timestamp_ms

        # Check if window is complete (500ms elapsed)
        window_duration = window.end_time - window.start_time
        if window_duration >= self.config.window_size_ms:
            # Store the window and start a new one
            point_id = self._store_window(window)
            del self._active_windows[session_id]
            return point_id

        return None

    def _store_window(self, window: PoseWindow) -> Optional[str]:
        """
        Store a completed pose window in Qdrant.

        Args:
            window: Completed pose window

        Returns:
            Point ID if successful, None on error
        """
        try:
            point_id = str(uuid.uuid4())
            vector = self._window_to_vector(window)

            # Prepare payload
            payload = {
                "session_id": window.session_id,
                "start_time": window.start_time,
                "end_time": window.end_time,
                "pose_count": len(window.poses),
                "detected_activity": window.detected_activity,
                "keypoint_names": POSE_KEYPOINT_NAMES,
                "raw_poses": json.dumps(window.poses),
            }

            # Upsert point
            self.client.upsert(
                collection_name=POSE_COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                ],
            )

            return point_id
        except Exception as e:
            logger.error(f"[PoseStore] Error storing pose window: {e}")
            return None

    def flush_session(self, session_id: str) -> Optional[str]:
        """
        Flush any remaining pose data in the active window for a session.

        Args:
            session_id: Session to flush

        Returns:
            Point ID if data was stored, None otherwise
        """
        if session_id in self._active_windows:
            window = self._active_windows[session_id]
            if window.poses:
                point_id = self._store_window(window)
                del self._active_windows[session_id]
                return point_id
            del self._active_windows[session_id]
        return None

    def get_session_poses(
        self,
        session_id: str,
        include_raw: bool = False,
    ) -> List[Dict]:
        """
        Get all pose windows for a session.

        Args:
            session_id: Session ID
            include_raw: Include raw pose data

        Returns:
            List of pose windows
        """
        results = []
        offset = None

        while True:
            response = self.client.scroll(
                collection_name=POSE_COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="session_id",
                            match=MatchValue(value=session_id),
                        )
                    ]
                ),
                limit=QDRANT_SCROLL_LIMIT,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            points, next_offset = response

            for point in points:
                pose_data = {
                    "id": point.id,
                    "start_time": point.payload.get("start_time"),
                    "end_time": point.payload.get("end_time"),
                    "pose_count": point.payload.get("pose_count"),
                    "detected_activity": point.payload.get("detected_activity"),
                }
                if include_raw:
                    raw_json = point.payload.get("raw_poses", "[]")
                    pose_data["raw_poses"] = json.loads(raw_json)
                results.append(pose_data)

            if next_offset is None:
                break
            offset = next_offset

        # Sort by start time
        results.sort(key=lambda x: x.get("start_time", 0))
        return results

    def delete_session_poses(self, session_id: str) -> int:
        """
        Delete all pose windows for a session.

        Args:
            session_id: Session to delete

        Returns:
            Number of points deleted
        """
        # Get all point IDs for session
        points_to_delete = []
        offset = None

        while True:
            response = self.client.scroll(
                collection_name=POSE_COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="session_id",
                            match=MatchValue(value=session_id),
                        )
                    ]
                ),
                limit=QDRANT_SCROLL_LIMIT,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )

            points, next_offset = response
            points_to_delete.extend([p.id for p in points])

            if next_offset is None:
                break
            offset = next_offset

        if points_to_delete:
            self.client.delete(
                collection_name=POSE_COLLECTION_NAME,
                points_selector=points_to_delete,
            )

        return len(points_to_delete)

    def health_check(self) -> Dict[str, Any]:
        """
        Check Qdrant pose collection health.

        Returns:
            Health status dict
        """
        try:
            info = self.client.get_collection(POSE_COLLECTION_NAME)
            return {
                "status": "healthy",
                "collection": POSE_COLLECTION_NAME,
                "points_count": info.points_count,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
