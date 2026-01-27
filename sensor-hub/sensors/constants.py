"""BLE protocol constants and timeouts for sensor communication.

This module centralizes all magic numbers used in BLE sensor communication,
making them easier to find, understand, and tune.
"""

# =============================================================================
# BLE Connection Timeouts (seconds)
# =============================================================================

BLE_SCAN_TIMEOUT = 10.0
"""Time to scan for a BLE device before giving up."""

BLE_CONNECT_TIMEOUT = 15.0
"""Time to wait for BLE connection to establish."""

BLE_RETRY_DELAY = 3.0
"""Delay between connection retry attempts."""

BLE_STABILIZATION_DELAY = 0.2
"""Wait after connection for link to stabilize."""

BLE_NOTIFICATION_SETUP_DELAY = 0.3
"""Wait after enabling notifications before sending commands."""

BLE_CONNECTION_CHECK_DELAY = 0.5
"""Delay between connection status checks."""

BLE_MONITOR_LOOP_INTERVAL = 0.1
"""Sleep interval in main monitoring loop."""


# =============================================================================
# Accelerometer (WT901BLE67) Constants
# =============================================================================

ACCEL_PACKET_SIZE = 20
"""Size of accelerometer data packet in bytes."""

ACCEL_KEEPALIVE_INTERVAL = 1.0
"""Interval between keep-alive commands (seconds)."""

ACCEL_KEEPALIVE_COMMAND = bytes([0xff, 0xaa, 0x27, 0x3A, 0x00])
"""Keep-alive command bytes for WT901BLE67."""


# =============================================================================
# Foot Sensor BLE UUIDs
# =============================================================================

FOOT_SERVICE_UUID = "0000FFF0-0000-1000-8000-00805F9B34FB"
FOOT_NOTIFY_UUID = "0000FFF1-0000-1000-8000-00805F9B34FB"
FOOT_WRITE_UUID = "0000FFF2-0000-1000-8000-00805F9B34FB"


# =============================================================================
# Accelerometer BLE UUIDs (two possible patterns depending on device variant)
# =============================================================================

ACCEL_NOTIFY_UUID_VARIANT1 = "0000ffe4-0000-1000-8000-00805f9b34fb"
ACCEL_NOTIFY_UUID_VARIANT2 = "0000fff1-0000-1000-8000-00805f9b34fb"
ACCEL_WRITE_UUID_VARIANT1 = "0000ffe9-0000-1000-8000-00805f9b34fb"
ACCEL_WRITE_UUID_VARIANT2 = "0000fff2-0000-1000-8000-00805f9b34fb"


# =============================================================================
# Startup Configuration
# =============================================================================

SENSOR_STARTUP_STAGGER = 3.0
"""Delay between starting each sensor to avoid BLE contention."""
