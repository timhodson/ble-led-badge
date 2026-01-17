#!/usr/bin/env python3
"""
Experiment: Send ASCII text - the badge might have an internal font!
"""
import asyncio
import sys

sys.path.insert(0, '.')
from badge_controller.commands import Command, ScrollMode
from badge_controller.protocol import Characteristics, AES_KEY
from bleak import BleakClient
from Crypto.Cipher import AES

ADDRESS = sys.argv[1] if len(sys.argv) > 1 else "FE5DCE05-1120-2974-BCBF-7AE2F6A509DF"


async def send_encrypted(client: BleakClient, packet: bytes):
    await client.write_gatt_char(Characteristics.COMMAND, packet, response=True)


async def send_image_data(client: BleakClient, data: bytes):
    await client.write_gatt_char(Characteristics.IMAGE_UPLOAD, data, response=False)


async def upload_text(client: BleakClient, text: str):
    """Upload ASCII text to badge."""
    data = text.encode('ascii')
    print(f"\nUploading: '{text}' ({len(data)} bytes)")
    print(f"  Data: {data.hex()}")

    # 1. DATS
    print("  Sending DATS...")
    await send_encrypted(client, Command.data_start(len(data)))
    await asyncio.sleep(0.2)

    # 2. Send text data
    print("  Sending text data...")
    await send_image_data(client, data)
    await asyncio.sleep(0.2)

    # 3. DATCP
    print("  Sending DATCP...")
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

        # Test different ASCII strings
        test_strings = [
            "A",
            "AB",
            "HELLO",
            "Test",
            "Hi!",
        ]

        for text in test_strings:
            await upload_text(client, text)

            # Set mode to trigger display
            print("  Setting MODE LEFT...")
            await send_encrypted(client, Command.mode(ScrollMode.LEFT))
            await asyncio.sleep(2)
            print("  >>> Check badge display! <<<")
            await asyncio.sleep(2)

        await client.stop_notify(Characteristics.NOTIFY)
        print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
