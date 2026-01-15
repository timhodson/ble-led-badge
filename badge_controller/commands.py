"""
Command builders for BLE LED Badge.

Each command is built as an encrypted packet ready to send to the badge.
"""

from enum import IntEnum
from typing import List, Sequence

from .encryption import build_encrypted_packet


class Animation(IntEnum):
    """Available built-in animations on the badge."""
    NONE = 0
    # Add more as discovered through experimentation
    ANIM_1 = 1
    ANIM_2 = 2
    ANIM_3 = 3
    ANIM_4 = 4
    ANIM_5 = 5


class ScrollMode(IntEnum):
    """Scroll modes for text display."""
    STATIC = 1      # No scrolling
    LEFT = 3        # Scroll left
    RIGHT = 4       # Scroll right


class Command:
    """Factory for building badge command packets."""

    @staticmethod
    def led_on() -> bytes:
        """
        Turn the badge display on.

        Returns:
            Encrypted command packet
        """
        return build_encrypted_packet("LEDON")

    @staticmethod
    def led_off() -> bytes:
        """
        Turn the badge display off.

        Returns:
            Encrypted command packet
        """
        return build_encrypted_packet("LEDOFF")

    @staticmethod
    def light(brightness: int) -> bytes:
        """
        Set badge brightness level.

        Args:
            brightness: Brightness level (0-255)

        Returns:
            Encrypted command packet
        """
        return build_encrypted_packet("LIGHT", brightness)

    @staticmethod
    def mode(scroll_mode: int) -> bytes:
        """
        Set scroll mode.

        Args:
            scroll_mode: Scroll mode (1=static, 3=left, 4=right)
                        Use ScrollMode enum for convenience.

        Returns:
            Encrypted command packet
        """
        return build_encrypted_packet("MODE", scroll_mode)

    @staticmethod
    def image(image_id: int) -> bytes:
        """
        Display a static image by ID.

        Args:
            image_id: ID of previously uploaded image

        Returns:
            Encrypted command packet
        """
        return build_encrypted_packet("IMAG", image_id)

    @staticmethod
    def animation(anim_id: int) -> bytes:
        """
        Play a built-in animation.

        Args:
            anim_id: Animation ID (see Animation enum)

        Returns:
            Encrypted command packet
        """
        return build_encrypted_packet("ANIM", anim_id)

    @staticmethod
    def speed(speed_level: int) -> bytes:
        """
        Set transition speed between images.

        Args:
            speed_level: Speed level (0-255, exact range TBD)

        Returns:
            Encrypted command packet
        """
        return build_encrypted_packet("SPEED", speed_level)

    @staticmethod
    def play(image_ids: Sequence[int]) -> bytes:
        """
        Play a sequence of custom images.

        Args:
            image_ids: List of image IDs to play in order

        Returns:
            Encrypted command packet
        """
        count = len(image_ids)
        return build_encrypted_packet("PLAY", count, *image_ids)

    @staticmethod
    def delete(image_ids: Sequence[int]) -> bytes:
        """
        Delete uploaded images.

        Args:
            image_ids: List of image IDs to delete

        Returns:
            Encrypted command packet
        """
        count = len(image_ids)
        return build_encrypted_packet("DELE", count, *image_ids)

    @staticmethod
    def check() -> bytes:
        """
        Check uploaded images on the badge.

        Response will come via the NOTIFY characteristic.

        Returns:
            Encrypted command packet
        """
        return build_encrypted_packet("CHEC")

    @staticmethod
    def data_start(length: int, unknown1: int = 0, unknown2: int = 0, unknown3: int = 0) -> bytes:
        """
        Initiate an image upload.

        After sending this command, send image data to the IMAGE_UPLOAD characteristic.
        Badge will respond with DATSOK via NOTIFY characteristic.

        Args:
            length: Total length of image data in bytes
            unknown1, unknown2, unknown3: Unknown parameters (defaults to 0)

        Returns:
            Encrypted command packet
        """
        length_high = (length >> 8) & 0xFF
        length_low = length & 0xFF
        return build_encrypted_packet("DATS", length_high, length_low, unknown1, unknown2, unknown3)


class ImageUpload:
    """Helper for building image upload packets (sent unencrypted to IMAGE_UPLOAD characteristic)."""

    @staticmethod
    def build_packets(image_data: bytes) -> List[bytes]:
        """
        Split image data into upload packets.

        Packet format: [length][counter][data...]
        Max 100 bytes per packet (98 bytes of payload + 2 header bytes)

        Args:
            image_data: Raw RGB image data

        Returns:
            List of packets ready to send
        """
        from .protocol import MAX_IMAGE_PAYLOAD

        packets = []
        offset = 0
        counter = 0

        while offset < len(image_data):
            chunk = image_data[offset:offset + MAX_IMAGE_PAYLOAD]
            packet_len = len(chunk) + 1  # +1 for counter byte
            packet = bytes([packet_len, counter]) + chunk
            packets.append(packet)

            offset += MAX_IMAGE_PAYLOAD
            counter += 1

        return packets
