"""Foot pressure sensor BLE interface using bleak."""

import asyncio
import json
from datetime import datetime
from bleak import BleakClient, BleakScanner
from .parsers import parse_foot_data
from .constants import (
    BLE_SCAN_TIMEOUT,
    BLE_CONNECT_TIMEOUT,
    BLE_RETRY_DELAY,
    BLE_STABILIZATION_DELAY,
    BLE_NOTIFICATION_SETUP_DELAY,
    BLE_CONNECTION_CHECK_DELAY,
    BLE_MONITOR_LOOP_INTERVAL,
    FOOT_SERVICE_UUID,
    FOOT_NOTIFY_UUID,
    FOOT_WRITE_UUID,
)


# Use constants for BLE UUIDs
SERVICE_UUID = FOOT_SERVICE_UUID
NOTIFY_UUID = FOOT_NOTIFY_UUID
WRITE_UUID = FOOT_WRITE_UUID


class FootSensor:
    """BLE interface for foot pressure sensor."""

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
        self.mac = mac_address
        self.name = device_name
        self.data_callback = data_callback
        self.client = None
        self.running = False
        self.data_buffer = ""
        self.throttle = throttle
        self.packet_count = 0
        self.max_retries = max_retries

    def _notification_handler(self, sender, raw_data):
        """Handle incoming BLE notifications (text protocol with newline delimiters and throttling)."""
        try:
            chunk = raw_data.decode('utf-8')
            self.data_buffer += chunk

            # Process all complete lines
            while '\n' in self.data_buffer:
                line, self.data_buffer = self.data_buffer.split('\n', 1)
                line = line.strip()

                if line:
                    # Throttle: only process every Nth packet
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

                        # Call callback if provided
                        if self.data_callback:
                            asyncio.create_task(self.data_callback(output))
                        else:
                            print(json.dumps(output))

        except Exception as e:
            print(f"[{self.name}] Notification error: {e}")

    async def connect(self):
        """
        Establish BLE connection with device scanning and retries.

        Returns:
            bool: True if connected successfully, False otherwise
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"[{self.name}] Scanning for device {self.mac} (attempt {attempt}/{self.max_retries})...")

                # Scan for device with timeout
                device = await BleakScanner.find_device_by_address(
                    self.mac,
                    timeout=BLE_SCAN_TIMEOUT
                )

                if not device:
                    print(f"[{self.name}] Device not found during scan")
                    if attempt < self.max_retries:
                        print(f"[{self.name}] Retrying in {BLE_RETRY_DELAY} seconds...")
                        await asyncio.sleep(BLE_RETRY_DELAY)
                        continue
                    else:
                        print(f"[{self.name}] Failed after {self.max_retries} attempts")
                        return False

                print(f"[{self.name}] Device found, connecting...")

                # Connect to device
                self.client = BleakClient(device, timeout=BLE_CONNECT_TIMEOUT)
                await self.client.connect()

                # Wait briefly for connection to stabilize
                await asyncio.sleep(BLE_STABILIZATION_DELAY)

                # Verify still connected
                if not self.client.is_connected:
                    print(f"[{self.name}] Connection lost immediately after connect")
                    if attempt < self.max_retries:
                        continue
                    else:
                        return False

                print(f"[{self.name}] Connected to {self.mac}")
                return True

            except Exception as e:
                print(f"[{self.name}] Connection attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    print(f"[{self.name}] Retrying in 3 seconds...")
                    await asyncio.sleep(3)
                else:
                    print(f"[{self.name}] All connection attempts failed")
                    return False

        return False

    async def start_monitoring(self):
        """Start receiving pressure data."""
        if not self.client:
            print(f"[{self.name}] Error: No client object")
            return False

        # Check connection with retry
        max_checks = 3
        for check in range(max_checks):
            if self.client.is_connected:
                break
            print(f"[{self.name}] Waiting for connection (check {check+1}/{max_checks})...")
            await asyncio.sleep(BLE_CONNECTION_CHECK_DELAY)

        if not self.client.is_connected:
            print(f"[{self.name}] Not connected after {max_checks} checks")
            return False

        try:
            # Enable notifications FIRST, before sending begin command
            await self.client.start_notify(NOTIFY_UUID, self._notification_handler)

            # Wait for notification setup to complete
            await asyncio.sleep(BLE_NOTIFICATION_SETUP_DELAY)

            # Now send begin command to start data collection
            await self.client.write_gatt_char(WRITE_UUID, b'begin', response=True)

            print(f"[{self.name}] Monitoring started")
            self.running = True
            return True

        except Exception as e:
            print(f"[{self.name}] Start monitoring failed: {e}")
            # Try to clean up
            try:
                await self.client.stop_notify(NOTIFY_UUID)
            except:
                pass
            return False

    async def stop_monitoring(self):
        """Stop receiving data and disconnect."""
        if not self.client or not self.client.is_connected:
            return

        try:
            self.running = False

            # Send end command
            await self.client.write_gatt_char(WRITE_UUID, b'end', response=True)

            # Stop notifications
            await self.client.stop_notify(NOTIFY_UUID)

            # Disconnect
            await self.client.disconnect()

            print(f"[{self.name}] Stopped and disconnected")

        except Exception as e:
            print(f"[{self.name}] Stop error: {e}")

    async def monitor_loop(self, duration=None):
        """
        Main monitoring loop.

        Args:
            duration: Optional duration in seconds (None = run indefinitely)
        """
        if not await self.connect():
            print(f"[{self.name}] Exiting - connection failed")
            return

        if not await self.start_monitoring():
            print(f"[{self.name}] Exiting - monitoring start failed")
            await self.stop_monitoring()
            return

        try:
            start_time = asyncio.get_event_loop().time()

            while self.running and self.client.is_connected:
                if duration and (asyncio.get_event_loop().time() - start_time) >= duration:
                    break
                await asyncio.sleep(BLE_MONITOR_LOOP_INTERVAL)

        except asyncio.CancelledError:
            pass
        finally:
            await self.stop_monitoring()
