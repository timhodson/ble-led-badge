"""
OSC Server for BLE LED Badge control.

Provides an OSC interface for controlling LED badges over Bluetooth,
enabling integration with various creative tools like TouchDesigner,
Max/MSP, Processing, and more.
"""

from .server import BadgeOSCServer

__all__ = ["BadgeOSCServer"]
