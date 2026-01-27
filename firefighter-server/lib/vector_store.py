"""Qdrant vector database wrapper for sensor data storage.

Handles windowing of sensor readings into vectors for similarity search.
"""

import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    Range,
)

from .config import QdrantConfig
from .constants import (
    FOOT_SENSOR_VALUES,
    ACCEL_SENSOR_VALUES,
    MAX_READINGS_PER_WINDOW,
    FOOT_VECTOR_DIM,
    ACCEL_VECTOR_DIM,
    QDRANT_SCROLL_LIMIT,
    QDRANT_TIMEOUT_SECONDS,
)


@dataclass
class SensorWindow:
    """A time window of sensor readings."""
    session_id: str
    device: str
    start_time: float
    end_time: float
    foot_readings: List[Dict] = field(default_factory=list)
    accel_readings: List[Dict] = field(default_factory=list)
    label: Optional[str] = None


class VectorStore:
    """Qdrant wrapper for sensor data with windowing."""

    def __init__(self, config: QdrantConfig):
        """
        Initialize Qdrant connection.

        Args:
            config: Qdrant configuration
        """
        self.config = config
        self.client = QdrantClient(
            host=config.host,
            port=config.port,
            timeout=QDRANT_TIMEOUT_SECONDS
        )

        # Active windows being accumulated (keyed by session_id)
        self._active_windows: Dict[str, SensorWindow] = {}

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.config.collection not in collection_names:
            self.client.create_collection(
                collection_name=self.config.collection,
                vectors_config=VectorParams(
                    size=self.config.vector_dimension,
                    distance=Distance.COSINE,
                ),
            )
            print(f"[Qdrant] Created collection: {self.config.collection}")
        else:
            print(f"[Qdrant] Using existing collection: {self.config.collection}")

    def _normalize_vector(self, values: List[float]) -> List[float]:
        """
        Normalize a vector to unit length.

        Args:
            values: Raw vector values

        Returns:
            Normalized vector
        """
        import numpy as np
        arr = np.array(values, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    def _foot_reading_to_vector(self, reading: Dict) -> List[float]:
        """
        Convert foot reading to vector segment.

        Args:
            reading: Foot sensor reading

        Returns:
            List of FOOT_SENSOR_VALUES floats
        """
        data = reading.get("data", {})
        values = data.get("values", [])

        # Pad or truncate to FOOT_SENSOR_VALUES values
        if len(values) < FOOT_SENSOR_VALUES:
            values = values + [0.0] * (FOOT_SENSOR_VALUES - len(values))
        return values[:FOOT_SENSOR_VALUES]

    def _accel_reading_to_vector(self, reading: Dict) -> List[float]:
        """
        Convert accelerometer reading to vector segment (9 values).

        Args:
            reading: Accelerometer reading

        Returns:
            List of 9 floats (acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, roll, pitch, yaw)
        """
        data = reading.get("data", {})
        acc = data.get("acc", {})
        gyro = data.get("gyro", {})
        angle = data.get("angle", {})

        return [
            acc.get("x", 0.0),
            acc.get("y", 0.0),
            acc.get("z", 0.0),
            gyro.get("x", 0.0),
            gyro.get("y", 0.0),
            gyro.get("z", 0.0),
            angle.get("roll", 0.0),
            angle.get("pitch", 0.0),
            angle.get("yaw", 0.0),
        ]

    def _window_to_vector(self, window: SensorWindow) -> List[float]:
        """
        Convert a sensor window to a fixed-size vector.

        Vector composition (270 dimensions):
        - 10 foot readings × 18 values = 180 dims
        - 10 accel readings × 9 values = 90 dims

        Args:
            window: Sensor window with accumulated readings

        Returns:
            Normalized vector of 270 floats
        """
        # Get up to MAX_READINGS_PER_WINDOW most recent readings of each type
        foot_readings = window.foot_readings[-MAX_READINGS_PER_WINDOW:]
        accel_readings = window.accel_readings[-MAX_READINGS_PER_WINDOW:]

        # Build foot segment (FOOT_VECTOR_DIM values)
        foot_vector = []
        for reading in foot_readings:
            foot_vector.extend(self._foot_reading_to_vector(reading))
        # Pad if less than MAX_READINGS_PER_WINDOW readings
        while len(foot_vector) < FOOT_VECTOR_DIM:
            foot_vector.extend([0.0] * FOOT_SENSOR_VALUES)

        # Build accel segment (ACCEL_VECTOR_DIM values)
        accel_vector = []
        for reading in accel_readings:
            accel_vector.extend(self._accel_reading_to_vector(reading))
        # Pad if less than MAX_READINGS_PER_WINDOW readings
        while len(accel_vector) < ACCEL_VECTOR_DIM:
            accel_vector.extend([0.0] * ACCEL_SENSOR_VALUES)

        # Combine and normalize
        full_vector = foot_vector[:FOOT_VECTOR_DIM] + accel_vector[:ACCEL_VECTOR_DIM]
        return self._normalize_vector(full_vector)

    def add_reading(
        self,
        session_id: str,
        sensor_type: str,
        reading: Dict,
        label: Optional[str] = None,
    ) -> Optional[str]:
        """
        Add a sensor reading, accumulating into windows.

        Args:
            session_id: Current recording session ID
            sensor_type: "foot" or "accel"
            reading: Sensor reading data
            label: Optional activity label for this window

        Returns:
            Point ID if a window was stored, None otherwise
        """
        if not session_id:
            return None

        # Parse timestamp
        timestamp_str = reading.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp_str)
            timestamp_ms = dt.timestamp() * 1000
        except (ValueError, TypeError):
            timestamp_ms = time.time() * 1000

        # Get or create active window
        if session_id not in self._active_windows:
            print(f"[VectorStore DEBUG] Creating new window for session {session_id} with label: {label}")
            self._active_windows[session_id] = SensorWindow(
                session_id=session_id,
                device=reading.get("device", "unknown"),
                start_time=timestamp_ms,
                end_time=timestamp_ms,
                label=label,
            )

        window = self._active_windows[session_id]

        # Update label if provided (allows changing activity during recording)
        if label is not None:
            print(f"[VectorStore DEBUG] Updating window label to: {label}")
            window.label = label

        print(f"[VectorStore DEBUG] Window label is now: {window.label}")

        # Add reading to appropriate list
        if sensor_type == "foot":
            window.foot_readings.append(reading)
        elif sensor_type == "accel":
            window.accel_readings.append(reading)

        window.end_time = timestamp_ms

        # Check if window is complete (500ms elapsed)
        window_duration = window.end_time - window.start_time
        if window_duration >= self.config.window_size_ms:
            # Store the window and start a new one
            point_id = self._store_window(window)

            # Reset for next window
            del self._active_windows[session_id]

            return point_id

        return None

    def _store_window(self, window: SensorWindow) -> str:
        """
        Store a completed window in Qdrant.

        Args:
            window: Completed sensor window

        Returns:
            Point ID
        """
        point_id = str(uuid.uuid4())
        vector = self._window_to_vector(window)

        # Prepare payload
        payload = {
            "session_id": window.session_id,
            "device": window.device,
            "start_time": window.start_time,
            "end_time": window.end_time,
            "foot_count": len(window.foot_readings),
            "accel_count": len(window.accel_readings),
            "label": window.label,
            "raw_data": json.dumps({
                "foot": window.foot_readings,
                "accel": window.accel_readings,
            }),
        }

        # Upsert point
        self.client.upsert(
            collection_name=self.config.collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )

        return point_id

    def flush_session(self, session_id: str) -> Optional[str]:
        """
        Flush any remaining data in the active window for a session.

        Args:
            session_id: Session to flush

        Returns:
            Point ID if data was stored, None otherwise
        """
        if session_id in self._active_windows:
            window = self._active_windows[session_id]
            if window.foot_readings or window.accel_readings:
                point_id = self._store_window(window)
                del self._active_windows[session_id]
                return point_id
            del self._active_windows[session_id]
        return None

    def query_similar(
        self,
        vector: List[float],
        limit: int = 10,
        session_id: Optional[str] = None,
        label: Optional[str] = None,
    ) -> List[Dict]:
        """
        Find similar sensor patterns.

        Args:
            vector: Query vector (270 dims)
            limit: Maximum results
            session_id: Optional filter by session
            label: Optional filter by label

        Returns:
            List of similar windows with scores
        """
        # Build filter
        filter_conditions = []
        if session_id:
            filter_conditions.append(
                FieldCondition(key="session_id", match=MatchValue(value=session_id))
            )
        if label:
            filter_conditions.append(
                FieldCondition(key="label", match=MatchValue(value=label))
            )

        query_filter = Filter(must=filter_conditions) if filter_conditions else None

        # Search
        results = self.client.search(
            collection_name=self.config.collection,
            query_vector=vector,
            limit=limit,
            query_filter=query_filter,
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "session_id": hit.payload.get("session_id"),
                "start_time": hit.payload.get("start_time"),
                "end_time": hit.payload.get("end_time"),
                "label": hit.payload.get("label"),
            }
            for hit in results
        ]

    def get_session_data(
        self,
        session_id: str,
        include_raw: bool = False,
    ) -> List[Dict]:
        """
        Get all windows for a session.

        Args:
            session_id: Session ID
            include_raw: Include raw sensor data

        Returns:
            List of windows
        """
        # Scroll through all points with session filter
        results = []
        offset = None

        while True:
            response = self.client.scroll(
                collection_name=self.config.collection,
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
                window_data = {
                    "id": point.id,
                    "start_time": point.payload.get("start_time"),
                    "end_time": point.payload.get("end_time"),
                    "foot_count": point.payload.get("foot_count"),
                    "accel_count": point.payload.get("accel_count"),
                    "label": point.payload.get("label"),
                }
                if include_raw:
                    raw_json = point.payload.get("raw_data", "{}")
                    window_data["raw_data"] = json.loads(raw_json)
                results.append(window_data)

            if next_offset is None:
                break
            offset = next_offset

        # Sort by start time
        results.sort(key=lambda x: x.get("start_time", 0))
        return results

    def update_labels(
        self,
        session_id: str,
        labels: Dict[str, str],
    ) -> int:
        """
        Update labels for windows in a session.

        Args:
            session_id: Session ID
            labels: Dict mapping window_id -> label

        Returns:
            Number of windows updated
        """
        updated = 0
        for window_id, label in labels.items():
            try:
                self.client.set_payload(
                    collection_name=self.config.collection,
                    payload={"label": label},
                    points=[window_id],
                )
                updated += 1
            except Exception as e:
                print(f"[Qdrant] Error updating label for {window_id}: {e}")

        return updated

    def delete_session(self, session_id: str) -> int:
        """
        Delete all windows for a session.

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
                collection_name=self.config.collection,
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
                collection_name=self.config.collection,
                points_selector=points_to_delete,
            )

        return len(points_to_delete)

    def health_check(self) -> Dict[str, Any]:
        """
        Check Qdrant connection health.

        Returns:
            Health status dict
        """
        try:
            info = self.client.get_collection(self.config.collection)
            return {
                "status": "healthy",
                "collection": self.config.collection,
                "points_count": info.points_count,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
