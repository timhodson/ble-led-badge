#!/usr/bin/env python3
"""
Experiment: Try different DATS command parameters.
The original trace showed DATS 0,9,0,0 - maybe these aren't just length bytes.
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


async def try_dats_params(client: BleakClient, params: tuple, data: bytes, description: str):
    """Try DATS with specific parameters."""
    print(f"\n{description}")
    print(f"  DATS params: {params}")
    print(f"  Data: {data.hex()} ({len(data)} bytes)")

    # Build DATS command manually
    dats_cmd = build_encrypted_packet("DATS", *params)
    print(f"  DATS encrypted: {dats_cmd.hex()}")

    await send_encrypted(client, dats_cmd)
    await asyncio.sleep(0.15)
    await send_image_data(client, data)
    await asyncio.sleep(0.15)
    await send_encrypted(client, Command.data_complete())
    await asyncio.sleep(0.4)


async def main():
    print(f"Connecting to {ADDRESS}...")

    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")

        def on_notify(sender, data):
            cipher = AES.new(AES_KEY, AES.MODE_ECB)
            decrypted = cipher.decrypt(data)
            text = ''.join(chr(b) if 0x20 <= b <= 0x7E else f'[{b:02x}]' for b in decrypted)
            if 'STYPE' not in text:  # Skip badge type notification
                print(f"  >> {text}")

        await client.start_notify(Characteristics.NOTIFY, on_notify)

        test_data = b'HELLO'

        # Original trace showed: DATS 0,9,0,0
        # Current code interprets as: length_high=0, length_low=9, unknown1=0, unknown2=0
        # But maybe it's: param1=0, param2=9, param3=0, param4=0

        tests = [
            # (params tuple, data, description)
            ((0, 9, 0, 0), b'A' * 9, "Original trace params (0,9,0,0) with 9 bytes"),
            ((0, 5, 0, 0), test_data, "Params (0,5,0,0) with 5 bytes"),
            ((0, 2, 0, 0), b'AB', "Params (0,2,0,0) with 2 bytes"),
            ((0, 0, 0, 5), test_data, "Try length in 4th param"),
            ((5, 0, 0, 0), test_data, "Try length in 1st param"),
            ((0, 0, 5, 0), test_data, "Try length in 3rd param"),
            ((1, 5, 0, 0), test_data, "Params (1,5,0,0) - maybe param1 is slot?"),
            ((0, 5, 1, 0), test_data, "Params (0,5,1,0)"),
            ((0, 5, 0, 1), test_data, "Params (0,5,0,1)"),
        ]

        for params, data, desc in tests:
            await try_dats_params(client, params, data, desc)
            await asyncio.sleep(1)

        await client.stop_notify(Characteristics.NOTIFY)
        print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
