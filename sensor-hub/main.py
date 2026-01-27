#!/usr/bin/env python3
"""Central BLE sensor monitoring system - monitors foot sensors and accelerometer concurrently.

Data Flow:
1. Sensors emit data via BLE
2. Data is stored in SQLite (backup buffer)
3. Data is broadcast via Socket.IO (if connected)
4. Background senders retry failed transmissions
"""

import asyncio
import json
import sys
from dotenv import load_dotenv
from sensors import FootSensor, AccelSensor
from lib.config import Config, SocketConfig, DatabaseConfig
from lib.database.foot_db import FootDatabase
from lib.database.accel_db import AccelDatabase
from lib.socket_client import SocketIOClient


# Global instances
foot_db: FootDatabase = None
accel_db: AccelDatabase = None
socket_client: SocketIOClient = None


def create_data_handler(database_getter, socket_event_name: str):
    """
    Factory function to create sensor data handlers.

    This eliminates duplicate handler code by parameterizing the database
    and Socket.IO event name.

    Args:
        database_getter: Function that returns the database instance
        socket_event_name: Socket.IO event name to emit

    Returns:
        Async handler function
    """
    async def handler(data: dict):
        global socket_client

        # Always store in SQLite (backup)
        database = database_getter()
        if database:
            database.save_record(data)

        # Broadcast via Socket.IO if connected
        if socket_client and socket_client.connected:
            socket_client.emit(socket_event_name, data)

        # Print to stdout (for debugging/logging)
        print(json.dumps(data))

    return handler


# Create handlers using factory (eliminates duplicate code)
handle_foot_data = create_data_handler(lambda: foot_db, "foot_pressure_data")
handle_accel_data = create_data_handler(lambda: accel_db, "accelerometer_data")


def init_databases(config: DatabaseConfig):
    """Initialize SQLite databases for sensor data storage."""
    global foot_db, accel_db

    print("[Database] Initializing SQLite storage...")
    foot_db = FootDatabase(config.foot_db_file)
    accel_db = AccelDatabase(config.accel_db_file)
    print(f"[Database] Foot DB: {config.foot_db_file}")
    print(f"[Database] Accel DB: {config.accel_db_file}")


def init_socket(config: SocketConfig) -> bool:
    """Initialize Socket.IO client for real-time data transmission."""
    global socket_client

    if not config.enabled:
        print("[Socket.IO] Disabled in configuration")
        return False

    print(f"[Socket.IO] Connecting to {config.server_url}...")
    socket_client = SocketIOClient(
        server_url=config.server_url,
        device_key=config.device_key,
        namespace=config.namespace,
    )

    if socket_client.connect():
        print("[Socket.IO] Connected successfully")
        return True
    else:
        print("[Socket.IO] Connection failed - data will be buffered in SQLite")
        return False


async def cleanup_tasks(tasks: list, socket_client):
    """
    Cancel all running tasks and disconnect socket client.

    This function handles graceful shutdown by:
    1. Cancelling all async tasks
    2. Waiting for them to complete cleanup
    3. Disconnecting the Socket.IO client

    Args:
        tasks: List of asyncio tasks to cancel
        socket_client: Socket.IO client instance (or None)
    """
    # Cancel all tasks
    for task in tasks:
        if not task.done():
            task.cancel()

    # Wait for all tasks to finish cleanup
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    # Disconnect Socket.IO
    if socket_client:
        socket_client.disconnect()


async def main():
    """Main entry point - monitor all sensors concurrently."""
    global socket_client

    # Load environment variables
    load_dotenv()

    # Load configuration
    config = Config.from_env()

    # Validate MAC addresses
    if not config.ble.left_foot_mac:
        print("Error: LEFT_FOOT_MAC not configured in .env")
        sys.exit(1)

    print("=" * 60)
    print("Sensor Hub - BLE Monitor with Data Pipeline")
    print("=" * 60)
    print(f"Left Foot:      {config.ble.left_foot_mac}")
    print(f"Right Foot:     {config.ble.right_foot_mac or 'Not configured'}")
    print(f"Accelerometer:  {config.ble.accelerometer_mac or 'Not configured'}")
    print("=" * 60)
    print(f"Throttle:       Foot={config.ble.foot_throttle}, Accel={config.ble.accel_throttle}")
    print(f"Retries:        {config.ble.connection_retries} attempts per device")
    print("=" * 60)

    # Initialize databases
    init_databases(config.database)

    # Initialize Socket.IO
    init_socket(config.socket)

    print("=" * 60)
    print("\nConnecting to devices with 3s delays...\n")

    # Create sensor instances and tasks with delays
    tasks = []

    # Connect to left foot first (critical sensor)
    print(f"[PRIORITY] Connecting to left foot sensor (throttle={config.ble.foot_throttle})...")
    left_foot = FootSensor(
        config.ble.left_foot_mac,
        "LEFT_FOOT",
        data_callback=handle_foot_data,
        throttle=config.ble.foot_throttle,
        max_retries=config.ble.connection_retries,
    )
    tasks.append(asyncio.create_task(left_foot.monitor_loop()))
    await asyncio.sleep(3)  # Delay to avoid BLE stack overload

    # Connect to right foot
    if config.ble.right_foot_mac:
        print(f"[PRIORITY] Connecting to right foot sensor (throttle={config.ble.foot_throttle})...")
        right_foot = FootSensor(
            config.ble.right_foot_mac,
            "RIGHT_FOOT",
            data_callback=handle_foot_data,
            throttle=config.ble.foot_throttle,
            max_retries=config.ble.connection_retries,
        )
        tasks.append(asyncio.create_task(right_foot.monitor_loop()))
        await asyncio.sleep(3)  # Delay to avoid BLE stack overload

    # Connect to accelerometer (with throttling, lower priority)
    if config.ble.accelerometer_mac:
        print(f"[SECONDARY] Connecting to accelerometer (throttle={config.ble.accel_throttle})...")
        accelerometer = AccelSensor(
            config.ble.accelerometer_mac,
            "ACCELEROMETER",
            data_callback=handle_accel_data,
            throttle=config.ble.accel_throttle,
            max_retries=config.ble.connection_retries,
        )
        tasks.append(asyncio.create_task(accelerometer.monitor_loop()))

    print("\n" + "=" * 60)
    print("All configured devices connected. Monitoring... (Ctrl+C to stop)")
    print("Data is being stored in SQLite and broadcast via Socket.IO")
    print("=" * 60 + "\n")

    # Monitor all sensors concurrently
    try:
        await asyncio.gather(*tasks)
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\n\nShutting down... Cleaning up connections.")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        await cleanup_tasks(tasks, socket_client)

    print("\n" + "=" * 60)
    print("All sensors disconnected. Goodbye!")
    print("=" * 60)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted during startup.")
