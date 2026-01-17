#!/usr/bin/env python3
"""
Experiment: Write wang-formatted data directly to ae01 characteristic.
This is the alternate service we discovered - maybe it's for text upload.
"""
import asyncio
import sys

sys.path.insert(0, '.')
from badge_controller.commands import Command, ScrollMode
from badge_controller.protocol import Characteristics, AES_KEY
from bleak import BleakClient
from Crypto.Cipher import AES

ADDRESS = sys.argv[1] if len(sys.argv) > 1 else "FE5DCE05-1120-2974-BCBF-7AE2F6A509DF"

CHAR_AE01 = "0000ae01-0000-1000-8000-00805f9b34fb"
CHAR_AE02 = "0000ae02-0000-1000-8000-00805f9b34fb"  # notify

# 12-row font
FONT = {
    'H': [0x00, 0x00, 0x42, 0x42, 0x42, 0x7E, 0x42, 0x42, 0x42, 0x42, 0x00, 0x00],
    'I': [0x00, 0x00, 0x3E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x3E, 0x00, 0x00],
    ' ': [0x00] * 12,
}


def build_wang_packets(text: str) -> list[bytes]:
    """Build 16-byte packets in wang format."""
    packets = []

    # Packet 1: Header
    header = bytearray(16)
    header[0:4] = b'wang'
    header[4] = 0x00  # flash mode
    header[5] = 0x00  # marquee mode
    header[6] = 0x00  # speed 1
    header[7] = 0x00  # speed 2
    header[8] = 0x00  # msg1 len high
    header[9] = len(text)  # msg1 len low
    packets.append(bytes(header))

    # Packet 2: Timestamp (zeros)
    packets.append(bytes(16))

    # Packet 3: Padding/separator
    packets.append(bytes(16))

    # Bitmap packets (12 bytes per char)
    bitmap = bytearray()
    for char in text.upper():
        bitmap.extend(FONT.get(char, FONT[' ']))

    # Split bitmap into 16-byte packets
    for i in range(0, len(bitmap), 16):
        chunk = bitmap[i:i+16]
        if len(chunk) < 16:
            chunk = chunk + bytes(16 - len(chunk))
        packets.append(bytes(chunk))

    return packets


async def send_encrypted(client: BleakClient, packet: bytes):
    await client.write_gatt_char(Characteristics.COMMAND, packet, response=True)


async def main():
    print(f"Connecting to {ADDRESS}...")

    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")

        # Set up notification handlers for both notify characteristics
        def on_notify_main(sender, data):
            cipher = AES.new(AES_KEY, AES.MODE_ECB)
            decrypted = cipher.decrypt(data)
            text = ''.join(chr(b) if 0x20 <= b <= 0x7E else f'[{b:02x}]' for b in decrypted)
            print(f"  >> main: {text}")

        def on_notify_ae02(sender, data):
            print(f"  >> ae02: {data.hex()}")

        await client.start_notify(Characteristics.NOTIFY, on_notify_main)
        try:
            await client.start_notify(CHAR_AE02, on_notify_ae02)
            print("  (Subscribed to ae02 notifications)")
        except Exception as e:
            print(f"  (Could not subscribe to ae02: {e})")

        # Build packets for "HI"
        packets = build_wang_packets("HI")

        print(f"\n=== Writing wang packets to ae01 ===")
        for i, packet in enumerate(packets):
            print(f"  Packet {i}: {packet.hex()}")
            try:
                await client.write_gatt_char(CHAR_AE01, packet, response=False)
                await asyncio.sleep(0.05)
            except Exception as e:
                print(f"  Error: {e}")

        print("  >>> Check badge! <<<")
        await asyncio.sleep(3)

        # Try setting mode via encrypted command
        print("\n=== Setting MODE LEFT ===")
        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(3)

        # Try with longer text
        print(f"\n=== Writing 'HELLO' to ae01 ===")
        packets = build_wang_packets("HELLO")
        for i, packet in enumerate(packets):
            print(f"  Packet {i}: {packet[:16].hex()}...")
            await client.write_gatt_char(CHAR_AE01, packet, response=False)
            await asyncio.sleep(0.05)

        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(3)

        await client.stop_notify(Characteristics.NOTIFY)
        print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
