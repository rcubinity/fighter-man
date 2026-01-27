"""Accelerometer IMU sensor BLE interface using bleak (WT901BLE67)."""

import asyncio
import json
from datetime import datetime
from .ble_sensor_base import BLESensorBase
from .parsers import parse_accel_data
from .constants import (
    ACCEL_PACKET_SIZE,
    ACCEL_KEEPALIVE_INTERVAL,
    ACCEL_KEEPALIVE_COMMAND,
    ACCEL_NOTIFY_UUID_VARIANT1,
    ACCEL_WRITE_UUID_VARIANT1,
)


class AccelSensor(BLESensorBase):
    """BLE interface for WT901BLE67 IMU accelerometer sensor (binary protocol)."""

    def __init__(self, mac_address, device_name="ACCELEROMETER", data_callback=None, throttle=5, max_retries=3):
        """
        Initialize accelerometer sensor.

        Args:
            mac_address: BLE MAC address
            device_name: Identifier (default: 'ACCELEROMETER')
            data_callback: Optional async function to call with parsed data
            throttle: Process every Nth packet (default: 5, reduces 100Hz -> 20Hz)
            max_retries: Maximum connection retry attempts (default: 3)
        """
        super().__init__(mac_address, device_name, data_callback, throttle, max_retries)
        self.packet_buffer = bytearray()
        self.notify_uuid = None
        self.write_uuid = None

    def _notification_handler(self, sender, raw_data):
        """Handle incoming BLE notifications (binary 20-byte packets)."""
        try:
            self.packet_buffer.extend(raw_data)

            while len(self.packet_buffer) >= ACCEL_PACKET_SIZE:
                packet = bytes(self.packet_buffer[:ACCEL_PACKET_SIZE])
                self.packet_buffer = self.packet_buffer[ACCEL_PACKET_SIZE:]

                self.packet_count += 1
                if self.packet_count % self.throttle != 0:
                    continue

                result = parse_accel_data(packet)
                if result:
                    output = {
                        'timestamp': datetime.now().isoformat(),
                        'device': self.name,
                        'data': result
                    }

                    if self.data_callback:
                        asyncio.create_task(self.data_callback(output))
                    else:
                        print(json.dumps(output))

        except Exception as e:
            print(f"[{self.name}] Notification error: {e}")

    async def _on_connected(self):
        """Discover UUIDs after connection."""
        await self._discover_uuids()

    async def _discover_uuids(self):
        """Discover which UUID pattern this device uses."""
        try:
            services = self.client.services

            for service in services:
                for char in service.characteristics:
                    uuid_str = str(char.uuid).lower()

                    if 'ffe4' in uuid_str or 'fff1' in uuid_str:
                        if 'read' in char.properties or 'notify' in char.properties:
                            self.notify_uuid = char.uuid
                            print(f"[{self.name}] Found notify UUID: {char.uuid}")

                    if 'ffe9' in uuid_str or 'fff2' in uuid_str:
                        if 'write' in char.properties:
                            self.write_uuid = char.uuid
                            print(f"[{self.name}] Found write UUID: {char.uuid}")

            if not self.notify_uuid:
                print(f"[{self.name}] Warning: Notify UUID not found, trying default")
                self.notify_uuid = ACCEL_NOTIFY_UUID_VARIANT1

            return bool(self.notify_uuid)

        except Exception as e:
            print(f"[{self.name}] UUID discovery error: {e}")
            self.notify_uuid = ACCEL_NOTIFY_UUID_VARIANT1
            self.write_uuid = ACCEL_WRITE_UUID_VARIANT1
            return True

    async def _start_notifications(self):
        """Enable notifications and start keep-alive task."""
        await self.client.start_notify(self.notify_uuid, self._notification_handler)
        asyncio.create_task(self._keep_alive())

    async def _stop_notifications(self):
        """Stop notifications."""
        if self.notify_uuid:
            await self.client.stop_notify(self.notify_uuid)

    async def _keep_alive(self):
        """Send periodic keep-alive commands (device-specific protocol)."""
        while self.running and self.client and self.client.is_connected:
            try:
                if self.write_uuid:
                    await self.client.write_gatt_char(self.write_uuid, ACCEL_KEEPALIVE_COMMAND, response=False)
                await asyncio.sleep(ACCEL_KEEPALIVE_INTERVAL)
            except Exception:
                break
