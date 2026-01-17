#!/usr/bin/env python3
"""
Experiment: Send "wang" formatted data through the encrypted DATS/DATCP flow.
"""
import asyncio
import sys

sys.path.insert(0, '.')
from badge_controller.commands import Command, ScrollMode
from badge_controller.protocol import Characteristics, AES_KEY
from bleak import BleakClient
from Crypto.Cipher import AES

ADDRESS = sys.argv[1] if len(sys.argv) > 1 else "FE5DCE05-1120-2974-BCBF-7AE2F6A509DF"

# Character bitmaps (12 rows to match STYPE12X48N)
FONT_12ROW = {
    'A': bytes([0x00, 0x00, 0x38, 0x6C, 0xC6, 0xC6, 0xFE, 0xC6, 0xC6, 0xC6, 0x00, 0x00]),
    'B': bytes([0x00, 0x00, 0xFC, 0x66, 0x66, 0x7C, 0x66, 0x66, 0x66, 0xFC, 0x00, 0x00]),
    'H': bytes([0x00, 0x00, 0xC6, 0xC6, 0xC6, 0xFE, 0xC6, 0xC6, 0xC6, 0xC6, 0x00, 0x00]),
    'I': bytes([0x00, 0x00, 0x3C, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x3C, 0x00, 0x00]),
    ' ': bytes([0x00] * 12),
}


def build_wang_data(text: str) -> bytes:
    """Build complete wang-format data for a text string."""
    result = bytearray()

    # Packet 1: Header "wang" + message length
    header = bytearray(16)
    header[0:4] = b'wang'
    header[4] = 0x00
    header[5] = len(text)  # Number of characters
    result.extend(header)

    # Packet 2: Timestamp (zeros)
    result.extend(bytes(16))

    # Packet 3: Separator (zeros)
    result.extend(bytes(16))

    # Bitmap data - 12 bytes per character
    for char in text.upper():
        if char in FONT_12ROW:
            result.extend(FONT_12ROW[char])
        else:
            result.extend(FONT_12ROW[' '])

    return bytes(result)


async def send_encrypted(client: BleakClient, packet: bytes):
    await client.write_gatt_char(Characteristics.COMMAND, packet, response=True)


async def send_image_data(client: BleakClient, data: bytes):
    await client.write_gatt_char(Characteristics.IMAGE_UPLOAD, data, response=False)


async def upload_wang_data(client: BleakClient, text: str):
    """Upload wang-formatted data through DATS/DATCP."""
    data = build_wang_data(text)
    print(f"\nUploading '{text}' as wang format ({len(data)} bytes)")
    print(f"  First 48 bytes: {data[:48].hex()}")

    # 1. DATS with total length
    print("  DATS...")
    await send_encrypted(client, Command.data_start(len(data)))
    await asyncio.sleep(0.2)

    # 2. Send all data (might need chunking for large data)
    print("  Sending data...")
    # Try sending in chunks
    chunk_size = 20  # BLE typical MTU
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        await send_image_data(client, chunk)
        await asyncio.sleep(0.02)

    await asyncio.sleep(0.2)

    # 3. DATCP
    print("  DATCP...")
    await send_encrypted(client, Command.data_complete())
    await asyncio.sleep(0.5)


async def main():
    print(f"Connecting to {ADDRESS}...")

    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")

        def on_notify(sender, data):
            cipher = AES.new(AES_KEY, AES.MODE_ECB)
            decrypted = cipher.decrypt(data)
            ascii_str = ''.join(chr(b) if 0x20 <= b <= 0x7E else f'[{b:02x}]' for b in decrypted)
            print(f"  >> {ascii_str}")

        await client.start_notify(Characteristics.NOTIFY, on_notify)

        # Test with "HI"
        await upload_wang_data(client, "HI")
        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        # Test with "A"
        await upload_wang_data(client, "A")
        await send_encrypted(client, Command.mode(ScrollMode.STATIC))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        await client.stop_notify(Characteristics.NOTIFY)
        print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
