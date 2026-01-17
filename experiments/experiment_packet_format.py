#!/usr/bin/env python3
"""
Experiment: Try different packet formats for IMAGE_UPLOAD.
The working 1-2 byte raw uploads suggest there might be MTU or format requirements.
"""
import asyncio
import sys

sys.path.insert(0, '.')
from badge_controller.commands import Command, ScrollMode, ImageUpload
from badge_controller.protocol import Characteristics, AES_KEY
from bleak import BleakClient
from Crypto.Cipher import AES

ADDRESS = sys.argv[1] if len(sys.argv) > 1 else "FE5DCE05-1120-2974-BCBF-7AE2F6A509DF"


async def send_encrypted(client: BleakClient, packet: bytes):
    await client.write_gatt_char(Characteristics.COMMAND, packet, response=True)


async def send_image_data(client: BleakClient, data: bytes):
    await client.write_gatt_char(Characteristics.IMAGE_UPLOAD, data, response=False)


async def try_upload(client: BleakClient, name: str, raw_data: bytes, use_packet_format: bool = False):
    """Try uploading with optional packet framing."""
    print(f"\n--- {name} ---")

    if use_packet_format:
        # Use ImageUpload packet format: [payload_len+1, counter, data...]
        packets = ImageUpload.build_packets(raw_data)
        total_wire_bytes = sum(len(p) for p in packets)
        print(f"  Raw data: {raw_data.hex()} ({len(raw_data)} bytes)")
        print(f"  Packets: {[p.hex() for p in packets]}")
        print(f"  Total on wire: {total_wire_bytes} bytes")

        # DATS with raw data length (what badge will reconstruct)
        print("  DATS...")
        await send_encrypted(client, Command.data_start(len(raw_data)))
        await asyncio.sleep(0.2)

        # Send packets
        for i, packet in enumerate(packets):
            print(f"  Packet {i}: {packet.hex()}")
            await send_image_data(client, packet)
            await asyncio.sleep(0.02)
    else:
        print(f"  Raw data: {raw_data.hex()} ({len(raw_data)} bytes)")

        # DATS
        print("  DATS...")
        await send_encrypted(client, Command.data_start(len(raw_data)))
        await asyncio.sleep(0.2)

        # Send raw
        print(f"  Sending raw...")
        await send_image_data(client, raw_data)

    await asyncio.sleep(0.2)
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

        # Test 1: Raw "HELLO" (failed before)
        await try_upload(client, "Raw HELLO (expect ERROR)", b'HELLO', use_packet_format=False)
        await asyncio.sleep(2)

        # Test 2: "HELLO" with packet format
        await try_upload(client, "HELLO with packet format", b'HELLO', use_packet_format=True)
        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(3)

        # Test 3: Simple "AB" with packet format (raw worked before)
        await try_upload(client, "AB with packet format", b'AB', use_packet_format=True)
        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(3)

        # Test 4: Raw "AB" for comparison
        await try_upload(client, "Raw AB (should work)", b'AB', use_packet_format=False)
        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(3)

        await client.stop_notify(Characteristics.NOTIFY)
        print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
