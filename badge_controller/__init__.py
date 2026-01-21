"""
BLE LED Badge Controller

A Python library for controlling Bluetooth Low Energy LED name badges.
Uses AES-ECB encryption with the idealLED key.

Usage:
    from badge_controller import Badge, ScrollMode

    async with Badge("AA:BB:CC:DD:EE:FF") as badge:
        await badge.turn_on()
        await badge.set_brightness(128)
        await badge.set_scroll_mode(ScrollMode.LEFT)
        await badge.set_speed(50)
        await badge.turn_off()

Or use the CLI:
    badge-controller scan
    badge-controller brightness <address> <level>
"""

from .badge import Badge, scan_for_badges, find_badge_by_name
from .commands import Command, Animation, ImageUpload, ScrollMode
from .protocol import Characteristics, SERVICE_UUID
from .text_renderer import TextRenderer

__version__ = "0.1.0"

__all__ = [
    # Main class
    "Badge",

    # Utility functions
    "scan_for_badges",
    "find_badge_by_name",

    # Text rendering
    "TextRenderer",

    # Low-level access
    "Command",
    "Animation",
    "ScrollMode",
    "ImageUpload",
    "Characteristics",
    "SERVICE_UUID",
]
