"""
Protocol constants for BLE LED Badge communication.

Based on reverse-engineered "Shining Masks" protocol.
Reference: https://gist.github.com/Staars/71e63e4bdefc7e3fd22377bf9c50ac12
"""

# BLE Service UUID
SERVICE_UUID = "0000fee9-0000-1000-8000-00805f9b34fb"

# BLE Characteristic UUIDs
class Characteristics:
    """BLE GATT characteristic UUIDs for badge communication."""

    # Main command channel (AES-ECB encrypted)
    COMMAND = "d44bc439-abfd-45a2-b575-925416129600"

    # Image upload channel (unencrypted)
    IMAGE_UPLOAD = "d44bc439-abfd-45a2-b575-92541612960a"

    # Third write channel (purpose TBD)
    WRITE_3 = "d44bc439-abfd-45a2-b575-92541612960b"

    # Notification channel for responses
    NOTIFY = "d44bc439-abfd-45a2-b575-925416129601"


# AES Encryption key for command channel
# This is the "idealLED" key, found through reverse engineering BTSnoop traces
# Reference: https://github.com/8none1/idealLED
AES_KEY = bytes([
    0x34, 0x52, 0x2A, 0x5B, 0x7A, 0x6E, 0x49, 0x2C,
    0x08, 0x09, 0x0A, 0x9D, 0x8D, 0x2A, 0x23, 0xF8
])

# Alternative key used by "Shining Masks" devices (for reference)
SHINING_MASKS_KEY = bytes([
    0x32, 0x67, 0x2f, 0x79, 0x74, 0xad, 0x43, 0x45,
    0x1d, 0x9c, 0x6c, 0x89, 0x4a, 0x0e, 0x87, 0x64
])

# Packet size for AES-ECB (must be multiple of 16)
BLOCK_SIZE = 16

# Maximum image upload payload per packet
MAX_IMAGE_PAYLOAD = 98
