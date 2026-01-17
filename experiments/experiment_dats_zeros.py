#!/usr/bin/env python3
"""
Experiment: DATS with (0,0,x,x) params - this seems to work!
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


async def send_encrypted(client: BleakClient, packet: bytes):
    await client.write_gatt_char(Characteristics.COMMAND, packet, response=True)


async def send_image_data(client: BleakClient, data: bytes):
    await client.write_gatt_char(Characteristics.IMAGE_UPLOAD, data, response=False)


async def upload_text(client: BleakClient, text: str):
    """Upload text using DATS(0,0,0,0) params."""
    data = text.encode('ascii')
    print(f"\nUploading: '{text}' ({len(data)} bytes)")

    # DATS with all zeros
    dats_cmd = build_encrypted_packet("DATS", 0, 0, 0, 0)
    await send_encrypted(client, dats_cmd)
    await asyncio.sleep(0.15)

    # Send data
    await send_image_data(client, data)
    await asyncio.sleep(0.15)

    # DATCP
    await send_encrypted(client, Command.data_complete())
    await asyncio.sleep(0.5)

    # Set mode to display
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

        # Test progressively longer strings
        test_strings = [
            "HI",
            "HELLO",
            "TESTING",
            "Hello World",
            "This is a longer test message!",
        ]

        for text in test_strings:
            await upload_text(client, text)
            print(f"  >>> Check badge for: {text} <<<")
            await asyncio.sleep(3)

        await client.stop_notify(Characteristics.NOTIFY)
        print("\n=== Done! Did any text appear on the badge? ===")


if __name__ == "__main__":
    asyncio.run(main())
