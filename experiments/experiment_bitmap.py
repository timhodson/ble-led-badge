#!/usr/bin/env python3
"""
Experiment: Send bitmap data through the working DATS(0,0,0,0) flow.
Badge is 12 rows x 48 columns (STYPE12X48N).
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

# 12-row font (to match STYPE12X48N)
# Each character is 8 pixels wide, 12 pixels tall
# Each byte is one row (8 bits = 8 horizontal pixels)
FONT_12ROW = {
    'A': [0x00, 0x00, 0x3C, 0x42, 0x42, 0x42, 0x7E, 0x42, 0x42, 0x42, 0x00, 0x00],
    'B': [0x00, 0x00, 0x7C, 0x42, 0x42, 0x7C, 0x42, 0x42, 0x42, 0x7C, 0x00, 0x00],
    'C': [0x00, 0x00, 0x3C, 0x42, 0x40, 0x40, 0x40, 0x40, 0x42, 0x3C, 0x00, 0x00],
    'H': [0x00, 0x00, 0x42, 0x42, 0x42, 0x7E, 0x42, 0x42, 0x42, 0x42, 0x00, 0x00],
    'I': [0x00, 0x00, 0x3E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x3E, 0x00, 0x00],
    'E': [0x00, 0x00, 0x7E, 0x40, 0x40, 0x7C, 0x40, 0x40, 0x40, 0x7E, 0x00, 0x00],
    'L': [0x00, 0x00, 0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0x7E, 0x00, 0x00],
    'O': [0x00, 0x00, 0x3C, 0x42, 0x42, 0x42, 0x42, 0x42, 0x42, 0x3C, 0x00, 0x00],
    ' ': [0x00] * 12,
}


def text_to_bitmap_by_char(text: str) -> bytes:
    """Convert text to bitmap, character by character (all rows of char 1, then char 2, etc)."""
    result = bytearray()
    for char in text.upper():
        char_data = FONT_12ROW.get(char, FONT_12ROW[' '])
        result.extend(char_data)
    return bytes(result)


def text_to_bitmap_by_row(text: str) -> bytes:
    """Convert text to bitmap, row by row (row 0 of all chars, then row 1, etc)."""
    result = bytearray()
    chars = [FONT_12ROW.get(c, FONT_12ROW[' ']) for c in text.upper()]
    for row in range(12):
        for char_data in chars:
            result.append(char_data[row])
    return bytes(result)


def solid_pattern(rows: int, cols_bytes: int, pattern: int = 0xFF) -> bytes:
    """Create a solid pattern (for testing)."""
    return bytes([pattern] * (rows * cols_bytes))


def stripe_pattern(rows: int, cols_bytes: int) -> bytes:
    """Create horizontal stripes."""
    result = bytearray()
    for row in range(rows):
        val = 0xFF if row % 2 == 0 else 0x00
        result.extend([val] * cols_bytes)
    return bytes(result)


async def send_encrypted(client: BleakClient, packet: bytes):
    await client.write_gatt_char(Characteristics.COMMAND, packet, response=True)


async def send_image_data(client: BleakClient, data: bytes):
    await client.write_gatt_char(Characteristics.IMAGE_UPLOAD, data, response=False)


async def upload_data(client: BleakClient, data: bytes, description: str):
    """Upload data using DATS(0,0,0,0)."""
    print(f"\n{description}")
    print(f"  Size: {len(data)} bytes")
    print(f"  Data (first 48 bytes): {data[:48].hex()}")

    dats_cmd = build_encrypted_packet("DATS", 0, 0, 0, 0)
    await send_encrypted(client, dats_cmd)
    await asyncio.sleep(0.15)

    await send_image_data(client, data)
    await asyncio.sleep(0.15)

    await send_encrypted(client, Command.data_complete())
    await asyncio.sleep(0.5)

    await send_encrypted(client, Command.mode(ScrollMode.LEFT))
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

        # Test 1: Solid white (all LEDs on) - 12 rows x 6 bytes = 72 bytes for 48 pixels
        await upload_data(client, solid_pattern(12, 6, 0xFF), "Solid ON (all LEDs)")
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        # Test 2: Horizontal stripes
        await upload_data(client, stripe_pattern(12, 6), "Horizontal stripes")
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        # Test 3: "HI" bitmap by character (char1 rows, then char2 rows)
        await upload_data(client, text_to_bitmap_by_char("HI"), "HI - by character")
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        # Test 4: "HI" bitmap by row (row0 of all chars, row1 of all chars, etc)
        await upload_data(client, text_to_bitmap_by_row("HI"), "HI - by row")
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        # Test 5: Single character "A"
        await upload_data(client, bytes(FONT_12ROW['A']), "Single A character (12 bytes)")
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        await client.stop_notify(Characteristics.NOTIFY)
        print("\n=== Done! Did any patterns appear? ===")


if __name__ == "__main__":
    asyncio.run(main())
