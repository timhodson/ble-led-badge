#!/usr/bin/env python3
"""
Experiment: Send "wang" structured data through DATS(0,0,0,0) flow.
Maybe the badge needs the wang header to interpret the bitmap data.
"""
import asyncio
import sys

sys.path.insert(0, '.')
from badge_controller.encryption import build_encrypted_packet
from badge_controller.commands import Command, ScrollMode
from badge_controller.protocol import Characteristics, AES_KEY
from bleak import BleakClient
from Crypto.Cipher import AES

ADDRESS = sys.argv[1] if len(sys.argv) > 1 else "FE5DCE05-1120-2974-BCBF-7AE2F6A509DF"

# 12-row font
FONT = {
    'H': [0x00, 0x00, 0x42, 0x42, 0x42, 0x7E, 0x42, 0x42, 0x42, 0x42, 0x00, 0x00],
    'I': [0x00, 0x00, 0x3E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x3E, 0x00, 0x00],
    'A': [0x00, 0x00, 0x3C, 0x42, 0x42, 0x42, 0x7E, 0x42, 0x42, 0x42, 0x00, 0x00],
    ' ': [0x00] * 12,
}


def build_wang_packet(text: str, use_bitmap: bool = True) -> bytes:
    """
    Build wang-format data.
    Structure from Nilhcem article:
    - Bytes 0-3: "wang"
    - Bytes 4-5: flash mode, marquee mode
    - Bytes 6-7: speed settings
    - Bytes 8+: message lengths (2 bytes each, up to 8 messages)
    Then timestamp, separator, and bitmap/text data.
    """
    result = bytearray()

    # Header packet (16 bytes)
    header = bytearray(16)
    header[0:4] = b'wang'
    # Byte 4: flash (0=no flash)
    # Byte 5: marquee/scroll mode
    header[4] = 0x00  # no flash
    header[5] = 0x00  # mode
    # Bytes 6-7: speeds
    header[6] = 0x00
    header[7] = 0x00
    # Bytes 8-9: length of message 1 (as 2-byte value)
    header[8] = 0x00
    header[9] = len(text)
    # Rest are zeros for other message slots
    result.extend(header)

    # Timestamp packet (6 bytes used, padded to 16)
    timestamp = bytearray(16)
    # Could put actual timestamp but zeros should work
    result.extend(timestamp)

    # Padding/separator (varies by implementation, try different amounts)
    # Some say 20 bytes, let's try 16 (one packet)
    result.extend(bytes(16))

    # Bitmap data (12 bytes per character)
    if use_bitmap:
        for char in text.upper():
            char_data = FONT.get(char, FONT[' '])
            result.extend(char_data)
    else:
        # Or just ASCII
        result.extend(text.encode('ascii'))

    return bytes(result)


async def send_encrypted(client: BleakClient, packet: bytes):
    await client.write_gatt_char(Characteristics.COMMAND, packet, response=True)


async def send_image_data(client: BleakClient, data: bytes):
    await client.write_gatt_char(Characteristics.IMAGE_UPLOAD, data, response=False)


async def upload_data(client: BleakClient, data: bytes, description: str):
    """Upload using DATS(0,0,0,0)."""
    print(f"\n{description}")
    print(f"  Size: {len(data)} bytes")
    print(f"  First 64 bytes: {data[:64].hex()}")

    dats_cmd = build_encrypted_packet("DATS", 0, 0, 0, 0)
    await send_encrypted(client, dats_cmd)
    await asyncio.sleep(0.15)

    # Send in chunks (BLE MTU is typically ~20 bytes)
    chunk_size = 20
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        await send_image_data(client, chunk)
        await asyncio.sleep(0.02)

    await asyncio.sleep(0.15)
    await send_encrypted(client, Command.data_complete())
    await asyncio.sleep(0.5)


async def main():
    print(f"Connecting to {ADDRESS}...")

    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")

        def on_notify(sender, data):
            cipher = AES.new(AES_KEY, AES.MODE_ECB)
            decrypted = cipher.decrypt(data)
            text = ''.join(chr(b) if 0x20 <= b <= 0x7E else f'[{b:02x}]' for b in decrypted)
            if 'STYPE' not in text:
                print(f"  >> {text}")

        await client.start_notify(Characteristics.NOTIFY, on_notify)

        # Test 1: Wang format with bitmap
        wang_data = build_wang_packet("HI", use_bitmap=True)
        await upload_data(client, wang_data, "Wang format + bitmap for 'HI'")
        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        # Test 2: Wang format with ASCII (not bitmap)
        wang_ascii = build_wang_packet("HI", use_bitmap=False)
        await upload_data(client, wang_ascii, "Wang format + ASCII for 'HI'")
        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        # Test 3: Just the wang header (no bitmap)
        header_only = build_wang_packet("")[:48]  # Just header + timestamp + separator
        await upload_data(client, header_only, "Wang header only (no content)")
        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        await client.stop_notify(Characteristics.NOTIFY)
        print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
