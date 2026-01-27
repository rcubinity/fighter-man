"""Foot pressure sensor BLE interface using bleak."""

import asyncio
import json
from datetime import datetime
from .ble_sensor_base import BLESensorBase
from .parsers import parse_foot_data
from .constants import (
    BLE_NOTIFICATION_SETUP_DELAY,
    FOOT_NOTIFY_UUID,
    FOOT_WRITE_UUID,
)


class FootSensor(BLESensorBase):
    """BLE interface for foot pressure sensor (text protocol)."""

    def __init__(self, mac_address, device_name, data_callback=None, throttle=1, max_retries=3):
        """
        Initialize foot sensor.

        Args:
            mac_address: BLE MAC address
            device_name: Identifier (e.g., 'LEFT_FOOT', 'RIGHT_FOOT')
            data_callback: Optional async function to call with parsed data
            throttle: Process every Nth packet (default: 1 = no throttling)
            max_retries: Maximum connection retry attempts (default: 3)
        """
        super().__init__(mac_address, device_name, data_callback, throttle, max_retries)
        self.data_buffer = ""

    def _notification_handler(self, sender, raw_data):
        """Handle incoming BLE notifications (text protocol with newline delimiters)."""
        try:
            chunk = raw_data.decode('utf-8')
            self.data_buffer += chunk

            while '\n' in self.data_buffer:
                line, self.data_buffer = self.data_buffer.split('\n', 1)
                line = line.strip()

                if line:
                    self.packet_count += 1
                    if self.packet_count % self.throttle != 0:
                        continue

                    result = parse_foot_data(line)
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

    async def _start_notifications(self):
        """Enable notifications and send begin command."""
        await self.client.start_notify(FOOT_NOTIFY_UUID, self._notification_handler)
        await asyncio.sleep(BLE_NOTIFICATION_SETUP_DELAY)
        await self.client.write_gatt_char(FOOT_WRITE_UUID, b'begin', response=True)

    async def _stop_notifications(self):
        """Send end command and stop notifications."""
        try:
            await self.client.write_gatt_char(FOOT_WRITE_UUID, b'end', response=True)
            await self.client.stop_notify(FOOT_NOTIFY_UUID)
        except Exception:
            pass
