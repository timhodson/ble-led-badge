"""
High-level Badge controller class.

Provides an easy-to-use async API for controlling BLE LED badges.
"""

import asyncio
from typing import Callable, List, Optional, Sequence

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from .commands import Command, ImageUpload, ScrollMode
from .encryption import decrypt_response
from .protocol import Characteristics, SERVICE_UUID
from .text_renderer import TextRenderer


class Badge:
    """
    BLE LED Badge controller.

    Usage:
        async with Badge("AA:BB:CC:DD:EE:FF") as badge:
            await badge.set_brightness(128)
            await badge.play_animation(1)
    """

    def __init__(self, address: str):
        """
        Initialize badge controller.

        Args:
            address: BLE MAC address or UUID of the badge
        """
        self.address = address
        self._client: Optional[BleakClient] = None
        self._notification_callback: Optional[Callable[[bytes], None]] = None
        self._notification_queue: asyncio.Queue[bytes] = asyncio.Queue()

    async def __aenter__(self) -> "Badge":
        """Async context manager entry - connects to badge."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - disconnects from badge."""
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if currently connected to the badge."""
        return self._client is not None and self._client.is_connected

    async def connect(self) -> None:
        """Establish BLE connection to the badge."""
        self._client = BleakClient(self.address)
        await self._client.connect()

        # Subscribe to notifications
        await self._client.start_notify(
            Characteristics.NOTIFY,
            self._handle_notification
        )

    async def disconnect(self) -> None:
        """Disconnect from the badge."""
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(Characteristics.NOTIFY)
            except Exception:
                pass  # Ignore errors during cleanup
            await self._client.disconnect()
        self._client = None

    def _handle_notification(self, sender, data: bytes) -> None:
        """Handle incoming notifications from the badge."""
        decrypted = decrypt_response(data)

        # Call user callback if set
        if self._notification_callback:
            self._notification_callback(decrypted)

        # Also queue for await-style access
        try:
            self._notification_queue.put_nowait(decrypted)
        except asyncio.QueueFull:
            pass  # Drop if queue is full

    def on_notification(self, callback: Optional[Callable[[bytes], None]]) -> None:
        """
        Set callback for badge notifications.

        Args:
            callback: Function to call with decrypted notification data, or None to clear
        """
        self._notification_callback = callback

    async def wait_notification(self, timeout: float = 5.0) -> Optional[bytes]:
        """
        Wait for the next notification from the badge.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            Decrypted notification data, or None if timeout
        """
        try:
            return await asyncio.wait_for(self._notification_queue.get(), timeout)
        except asyncio.TimeoutError:
            return None

    async def _send_command(self, packet: bytes) -> None:
        """Send an encrypted command packet to the badge."""
        if not self._client:
            raise RuntimeError("Not connected to badge")
        await self._client.write_gatt_char(
            Characteristics.COMMAND,
            packet,
            response=True
        )

    async def _send_image_data(self, packet: bytes) -> None:
        """Send an image data packet (unencrypted) to the badge."""
        if not self._client:
            raise RuntimeError("Not connected to badge")
        await self._client.write_gatt_char(
            Characteristics.IMAGE_UPLOAD,
            packet,
            response=False  # write-without-response for speed
        )

    # High-level commands

    async def turn_on(self) -> None:
        """Turn the badge display on."""
        await self._send_command(Command.led_on())

    async def turn_off(self) -> None:
        """Turn the badge display off."""
        await self._send_command(Command.led_off())

    async def set_brightness(self, level: int) -> None:
        """
        Set the badge brightness.

        Args:
            level: Brightness level (0-255)
        """
        await self._send_command(Command.light(level))

    async def set_scroll_mode(self, mode: int) -> None:
        """
        Set the scroll mode.

        Args:
            mode: Scroll mode (use ScrollMode enum: STATIC=1, LEFT=3, RIGHT=4)
        """
        await self._send_command(Command.mode(mode))

    async def show_image(self, image_id: int) -> None:
        """
        Display a stored image.

        Args:
            image_id: ID of the image to display
        """
        await self._send_command(Command.image(image_id))

    async def play_animation(self, animation_id: int) -> None:
        """
        Play a built-in animation.

        Args:
            animation_id: Animation ID
        """
        await self._send_command(Command.animation(animation_id))

    async def set_speed(self, speed: int) -> None:
        """
        Set transition speed.

        Args:
            speed: Speed level (0-255)
        """
        await self._send_command(Command.speed(speed))

    async def play_sequence(self, image_ids: Sequence[int]) -> None:
        """
        Play a sequence of images.

        Args:
            image_ids: List of image IDs to play in order
        """
        await self._send_command(Command.play(image_ids))

    async def delete_images(self, image_ids: Sequence[int]) -> None:
        """
        Delete images from the badge.

        Args:
            image_ids: List of image IDs to delete
        """
        await self._send_command(Command.delete(image_ids))

    async def check_images(self) -> Optional[bytes]:
        """
        Query what images are stored on the badge.

        Returns:
            Response data from badge, or None if no response
        """
        await self._send_command(Command.check())
        return await self.wait_notification()

    async def upload_image(self, image_data: bytes) -> bool:
        """
        Upload an image to the badge.

        Args:
            image_data: Raw RGB image data

        Returns:
            True if upload was acknowledged (DATSOK received)
        """
        # Send upload start command
        await self._send_command(Command.data_start(len(image_data)))

        # Wait for acknowledgment
        response = await self.wait_notification(timeout=2.0)
        # TODO: Check for DATSOK in response

        # Send image data packets
        packets = ImageUpload.build_packets(image_data)
        for packet in packets:
            await self._send_image_data(packet)
            await asyncio.sleep(0.01)  # Small delay between packets

        # Signal upload complete
        await self._send_command(Command.data_complete())
        await asyncio.sleep(0.1)  # Brief pause for badge to process

        return response is not None

    async def send_text(
        self,
        text: str,
        scroll_mode: int = ScrollMode.LEFT,
        brightness: int = 128,
        speed: int = 50,
        image_slot: int = 0
    ) -> bool:
        """
        Send text to the badge display.

        This is a convenience method that renders text to a bitmap and uploads it.

        Args:
            text: Text string to display
            scroll_mode: Scroll mode (use ScrollMode enum: STATIC=1, LEFT=3, RIGHT=4)
            brightness: Brightness level (0-255, default 128)
            speed: Scroll speed (0-255, default 50)
            image_slot: Image slot number to use (0-7, default 0)

        Returns:
            True if upload was successful
        """
        # Render text to bitmap
        bitmap_data = TextRenderer.render_text(text)

        # Upload bitmap using the proper protocol:
        # 1. DATS (data start) -> COMMAND characteristic
        # 2. Image data packets -> IMAGE_UPLOAD characteristic
        # 3. DATCP (data complete) -> COMMAND characteristic
        success = await self.upload_image(bitmap_data)

        if success:
            # Set display parameters after upload
            await self.set_scroll_mode(scroll_mode)
            await self.set_brightness(brightness)
            await self.set_speed(speed)

        return success

    async def send_raw_command(self, packet: bytes) -> None:
        """
        Send a raw pre-encrypted command packet.

        Useful for experimentation or commands not yet implemented.

        Args:
            packet: Raw 16-byte encrypted packet
        """
        await self._send_command(packet)


# Utility functions

async def scan_for_badges(timeout: float = 10.0) -> List[BLEDevice]:
    """
    Scan for nearby BLE LED badges.

    Args:
        timeout: Scan duration in seconds

    Returns:
        List of discovered devices (filter by name/service as needed)
    """
    devices = await BleakScanner.discover(timeout=timeout)
    # Could filter by SERVICE_UUID if devices advertise it
    return devices


async def find_badge_by_name(name_pattern: str, timeout: float = 10.0) -> Optional[BLEDevice]:
    """
    Find a badge by name pattern.

    Args:
        name_pattern: Substring to match in device name
        timeout: Scan duration in seconds

    Returns:
        First matching device, or None if not found
    """
    devices = await scan_for_badges(timeout)
    for device in devices:
        if device.name and name_pattern.lower() in device.name.lower():
            return device
    return None
