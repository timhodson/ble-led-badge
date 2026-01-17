#!/usr/bin/env python3
"""
Experiment: Try the encrypted DATS/DATCP protocol with different data formats.
"""
import asyncio
import sys
from bleak import BleakClient

# Add parent to path for imports
sys.path.insert(0, '.')
from badge_controller.commands import Command, ScrollMode
from badge_controller.protocol import Characteristics

ADDRESS = sys.argv[1] if len(sys.argv) > 1 else "FE5DCE05-1120-2974-BCBF-7AE2F6A509DF"

# Character 'A' bitmap - 11 rows (from Nilhcem)
CHAR_A = bytes([0x00, 0x38, 0x6C, 0xC6, 0xC6, 0xFE, 0xC6, 0xC6, 0xC6, 0xC6, 0x00])

# Try different data formats
TEST_DATA = {
    "raw_bitmap_11": CHAR_A,
    "raw_bitmap_12": CHAR_A + b'\x00',  # 12 rows
    "ascii_A": b'A',
    "ascii_A_padded": b'A' + b'\x00' * 10,
    "length_prefixed": bytes([11]) + CHAR_A,  # Length + bitmap
    "counter_prefixed": bytes([12, 0]) + CHAR_A + b'\x00',  # Like ImageUpload format
}


async def send_encrypted(client: BleakClient, packet: bytes):
    """Send encrypted packet to COMMAND characteristic."""
    await client.write_gatt_char(Characteristics.COMMAND, packet, response=True)


async def send_image_data(client: BleakClient, data: bytes):
    """Send data to IMAGE_UPLOAD characteristic."""
    await client.write_gatt_char(Characteristics.IMAGE_UPLOAD, data, response=False)


async def try_upload(client: BleakClient, name: str, data: bytes):
    """Try uploading data using DATS/DATCP protocol."""
    print(f"\n--- Trying: {name} ({len(data)} bytes) ---")
    print(f"  Data: {data.hex()}")

    try:
        # 1. Send DATS (data start) with length
        dats_cmd = Command.data_start(len(data))
        print(f"  DATS command: {dats_cmd.hex()}")
        await send_encrypted(client, dats_cmd)
        await asyncio.sleep(0.1)

        # 2. Send image data (unencrypted)
        print(f"  Sending {len(data)} bytes to IMAGE_UPLOAD...")
        await send_image_data(client, data)
        await asyncio.sleep(0.1)

        # 3. Send DATCP (data complete)
        datcp_cmd = Command.data_complete()
        print(f"  DATCP command: {datcp_cmd.hex()}")
        await send_encrypted(client, datcp_cmd)
        await asyncio.sleep(0.1)

        # 4. Set mode to static to trigger display
        mode_cmd = Command.mode(ScrollMode.STATIC)
        print(f"  MODE command: {mode_cmd.hex()}")
        await send_encrypted(client, mode_cmd)
        await asyncio.sleep(0.5)

        print(f"  SUCCESS")
        return True

    except Exception as e:
        print(f"  FAILED: {e}")
        return False


async def main():
    print(f"Connecting to {ADDRESS}...")

    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")

        # Subscribe to notifications to see responses
        responses = []
        def on_notify(sender, data):
            print(f"  >> Notification: {data.hex()}")
            responses.append(data)

        await client.start_notify(Characteristics.NOTIFY, on_notify)

        for name, data in TEST_DATA.items():
            await try_upload(client, name, data)
            await asyncio.sleep(1)
            print(f"  (Check badge now)")
            await asyncio.sleep(2)

        await client.stop_notify(Characteristics.NOTIFY)

        print("\n=== All tests complete ===")
        print("Did the badge display change for any of the formats?")


if __name__ == "__main__":
    asyncio.run(main())
