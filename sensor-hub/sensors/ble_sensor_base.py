"""Abstract base class for BLE sensor interfaces."""

import asyncio
from abc import ABC, abstractmethod
from bleak import BleakClient, BleakScanner
from .constants import (
    BLE_SCAN_TIMEOUT,
    BLE_CONNECT_TIMEOUT,
    BLE_RETRY_DELAY,
    BLE_STABILIZATION_DELAY,
    BLE_CONNECTION_CHECK_DELAY,
    BLE_MONITOR_LOOP_INTERVAL,
)


class BLESensorBase(ABC):
    """Abstract base class for BLE sensors with common connection and monitoring logic."""

    def __init__(self, mac_address, device_name, data_callback=None, throttle=1, max_retries=3):
        """
        Initialize BLE sensor.

        Args:
            mac_address: BLE MAC address
            device_name: Identifier for logging
            data_callback: Optional async function to call with parsed data
            throttle: Process every Nth packet (default: 1 = no throttling)
            max_retries: Maximum connection retry attempts (default: 3)
        """
        self.mac = mac_address
        self.name = device_name
        self.data_callback = data_callback
        self.client = None
        self.running = False
        self.throttle = throttle
        self.packet_count = 0
        self.max_retries = max_retries

    @abstractmethod
    def _notification_handler(self, sender, raw_data):
        """Handle incoming BLE notifications. Subclasses implement protocol-specific parsing."""
        pass

    async def _on_connected(self):
        """Hook called after successful connection. Override for post-connection setup."""
        pass

    @abstractmethod
    async def _start_notifications(self):
        """Start sensor-specific notifications. Subclasses implement setup logic."""
        pass

    async def _stop_notifications(self):
        """Stop notifications. Override for sensor-specific cleanup."""
        pass

    async def connect(self):
        """
        Establish BLE connection with device scanning and retries.

        Returns:
            bool: True if connected successfully, False otherwise
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"[{self.name}] Scanning for device {self.mac} (attempt {attempt}/{self.max_retries})...")

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

                self.client = BleakClient(device, timeout=BLE_CONNECT_TIMEOUT)
                await self.client.connect()

                await asyncio.sleep(BLE_STABILIZATION_DELAY)

                if not self.client.is_connected:
                    print(f"[{self.name}] Connection lost immediately after connect")
                    if attempt < self.max_retries:
                        continue
                    else:
                        return False

                print(f"[{self.name}] Connected to {self.mac}")

                await self._on_connected()
                return True

            except Exception as e:
                print(f"[{self.name}] Connection attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    print(f"[{self.name}] Retrying in {BLE_RETRY_DELAY} seconds...")
                    await asyncio.sleep(BLE_RETRY_DELAY)
                else:
                    print(f"[{self.name}] All connection attempts failed")
                    return False

        return False

    async def start_monitoring(self):
        """Start receiving sensor data."""
        if not self.client:
            print(f"[{self.name}] Error: No client object")
            return False

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
            await self._start_notifications()
            print(f"[{self.name}] Monitoring started")
            self.running = True
            return True

        except Exception as e:
            print(f"[{self.name}] Start monitoring failed: {e}")
            return False

    async def stop_monitoring(self):
        """Stop receiving data and disconnect."""
        if not self.client or not self.client.is_connected:
            return

        try:
            self.running = False
            await self._stop_notifications()
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
