#!/usr/bin/env python3
"""
Experiment: Find the DATS length limit.
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


async def try_length(client: BleakClient, length: int):
    """Try DATS with specific length."""
    data = bytes([0x41 + i for i in range(length)])  # A, B, C, D...
    print(f"Length {length}: ", end="", flush=True)

    await send_encrypted(client, Command.data_start(length))
    await asyncio.sleep(0.1)
    await send_image_data(client, data)
    await asyncio.sleep(0.1)
    await send_encrypted(client, Command.data_complete())
    await asyncio.sleep(0.3)


async def main():
    print(f"Connecting to {ADDRESS}...")

    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}\n")

        results = {}

        def on_notify(sender, data):
            cipher = AES.new(AES_KEY, AES.MODE_ECB)
            decrypted = cipher.decrypt(data)
            # Look for DATCPOK or ERROR
            text = decrypted.decode('ascii', errors='ignore')
            if 'DATCPOK' in text:
                print("OK")
                results[current_len] = 'OK'
            elif 'ERROR' in text:
                print("ERROR")
                results[current_len] = 'ERROR'
            elif 'DATSOK' in text:
                pass  # Expected, ignore
            elif 'STYPE' in text:
                pass  # Badge type, ignore

        await client.start_notify(Characteristics.NOTIFY, on_notify)

        print("Testing DATS length limits...")
        for length in range(1, 20):
            current_len = length
            await try_length(client, length)

        await client.stop_notify(Characteristics.NOTIFY)

        print(f"\n=== Results ===")
        for k, v in sorted(results.items()):
            print(f"  Length {k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
