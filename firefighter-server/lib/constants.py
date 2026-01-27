"""Server constants and configuration values.

This module centralizes all magic numbers and configuration constants,
making them easier to find, understand, and modify.
"""

# =============================================================================
# Activity Types (Stage 1)
# =============================================================================

ACTIVITY_TYPES = [
    "Walking",
    "Running",
    "Crawling",
    "Climbing",
    "Standing",
    "Kneeling",
    "Sitting",
    "Carrying",
    "Hose_Operation",
    "Idle",
]
"""Valid activity types for Stage 1 data collection."""


# =============================================================================
# Sensor Data Dimensions
# =============================================================================

FOOT_SENSOR_VALUES = 18
"""Number of pressure values per foot sensor reading."""

ACCEL_SENSOR_VALUES = 9
"""Number of values per accelerometer reading (acc_xyz + gyro_xyz + angles)."""

MAX_READINGS_PER_WINDOW = 10
"""Maximum number of readings to include in each sensor window."""


# =============================================================================
# Vector Dimensions
# =============================================================================

FOOT_VECTOR_DIM = FOOT_SENSOR_VALUES * MAX_READINGS_PER_WINDOW  # 180
"""Dimension of foot segment in vector (18 values × 10 readings)."""

ACCEL_VECTOR_DIM = ACCEL_SENSOR_VALUES * MAX_READINGS_PER_WINDOW  # 90
"""Dimension of accelerometer segment in vector (9 values × 10 readings)."""

TOTAL_VECTOR_DIM = FOOT_VECTOR_DIM + ACCEL_VECTOR_DIM  # 270
"""Total vector dimension for Qdrant storage."""


# =============================================================================
# Window Configuration
# =============================================================================

DEFAULT_WINDOW_SIZE_MS = 500
"""Default time window duration in milliseconds."""


# =============================================================================
# Query Limits
# =============================================================================

QDRANT_SCROLL_LIMIT = 100
"""Maximum records to fetch per Qdrant scroll operation."""

DEFAULT_REPLAY_LIMIT = 20
"""Default number of windows to return in replay API."""

MAX_REPLAY_LIMIT = 100
"""Maximum number of windows allowed in replay API."""


# =============================================================================
# Video Configuration
# =============================================================================

DEFAULT_VIDEO_MAX_SIZE_MB = 500
"""Default maximum video file size in megabytes."""

ALLOWED_VIDEO_EXTENSIONS = {'webm', 'mp4', 'avi', 'mov'}
"""Allowed video file extensions for upload."""


# =============================================================================
# Timeouts
# =============================================================================

QDRANT_TIMEOUT_SECONDS = 10
"""Timeout for Qdrant operations to prevent hanging."""
