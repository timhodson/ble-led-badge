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
    ANIM_6 = 6
    ANIM_7 = 7
    ANIM_8 = 8


class ScrollMode(IntEnum):
    """Scroll modes for text display."""
    STATIC = 1      # No scrolling
    LEFT = 3        # Scroll left
    RIGHT = 4       # Scroll right
    UP = 5          # Scroll up
    DOWN = 6        # Scroll down
    SNOW = 7       # SNOW effect (line by line drop down)
    # The INVERT and BLINK modes are seen in the app, but not reverse engineered yet


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
    def data_complete() -> bytes:
        """
        Signal completion of data/image upload.

        Send this after all image data packets have been transmitted.

        Returns:
            Encrypted command packet
        """
        return build_encrypted_packet("DATCP")

    @staticmethod
    def data_start(length: int) -> bytes:
        """
        Initiate an image upload.

        After sending this command, send image data to the IMAGE_UPLOAD characteristic.
        Badge will respond with DATSOK via NOTIFY characteristic.

        Args:
            length: Total length of image data in bytes (max 65535)

        Returns:
            Encrypted command packet
        """
        # Format from trace analysis: DATS[length_high][length_low][0x00][0x00]
        # Length is 16-bit big-endian (e.g., 576 bytes = 0x0240 -> params 0x02, 0x40)
        length_high = (length >> 8) & 0xFF
        length_low = length & 0xFF
        return build_encrypted_packet("DATS", length_high, length_low, 0x00, 0x00)


class ImageUpload:
    """Helper for building image upload packets (encrypted, sent to IMAGE_UPLOAD characteristic)."""

    @staticmethod
    def build_packets(image_data: bytes) -> List[bytes]:
        """
        Split image data into encrypted upload packets.

        Packet format (before encryption): [data_length][data...][zero padding to 16 bytes]
        Each packet is then AES-ECB encrypted before sending.

        Args:
            image_data: Raw bitmap data (9 bytes per character for text)

        Returns:
            List of encrypted 16-byte packets ready to send
        """
        from .encryption import encrypt_command

        packets = []
        offset = 0

        while offset < len(image_data):
            # Each packet can hold up to 15 bytes of data (1 byte for length prefix)
            chunk = image_data[offset:offset + 15]
            chunk_len = len(chunk)

            # Build packet: [length][data][zero padding to 16 bytes]
            packet = bytes([chunk_len]) + chunk
            if len(packet) < 16:
                packet = packet + bytes(16 - len(packet))

            # Encrypt the packet
            encrypted = encrypt_command(packet)
            packets.append(encrypted)

            offset += 15

        return packets
