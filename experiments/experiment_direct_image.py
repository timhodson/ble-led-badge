#!/usr/bin/env python3
"""
Experiment: Write wang packets directly to IMAGE_UPLOAD characteristic
(without DATS/DATCP wrapper).
"""
import asyncio
import sys

sys.path.insert(0, '.')
from badge_controller.commands import Command, ScrollMode
from badge_controller.protocol import Characteristics, AES_KEY
from bleak import BleakClient
from Crypto.Cipher import AES

ADDRESS = sys.argv[1] if len(sys.argv) > 1 else "FE5DCE05-1120-2974-BCBF-7AE2F6A509DF"

# 12-row font
FONT = {
    'H': [0x00, 0x00, 0x42, 0x42, 0x42, 0x7E, 0x42, 0x42, 0x42, 0x42, 0x00, 0x00],
    'I': [0x00, 0x00, 0x3E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x3E, 0x00, 0x00],
    'E': [0x00, 0x00, 0x7E, 0x40, 0x40, 0x7C, 0x40, 0x40, 0x40, 0x7E, 0x00, 0x00],
    'L': [0x00, 0x00, 0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0x7E, 0x00, 0x00],
    'O': [0x00, 0x00, 0x3C, 0x42, 0x42, 0x42, 0x42, 0x42, 0x42, 0x3C, 0x00, 0x00],
    ' ': [0x00] * 12,
}


def build_wang_packets(text: str) -> list[bytes]:
    """Build 16-byte packets in wang format."""
    packets = []

    # Packet 1: Header with "wang" + lengths
    header = bytearray(16)
    header[0:4] = b'wang'
    header[4] = 0x00  # flash
    header[5] = 0x00  # marquee
    header[6] = 0x00  # speed1
    header[7] = 0x00  # speed2
    header[8] = 0x00  # len high
    header[9] = len(text)  # len low
    packets.append(bytes(header))

    # Packet 2: Timestamp
    packets.append(bytes(16))

    # Packet 3: Padding
    packets.append(bytes(16))

    # Bitmap data
    bitmap = bytearray()
    for char in text.upper():
        bitmap.extend(FONT.get(char, FONT[' ']))

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

        def on_notify(sender, data):
            cipher = AES.new(AES_KEY, AES.MODE_ECB)
            decrypted = cipher.decrypt(data)
            text = ''.join(chr(b) if 0x20 <= b <= 0x7E else f'[{b:02x}]' for b in decrypted)
            if 'STYPE' not in text:
                print(f"  >> {text}")

        await client.start_notify(Characteristics.NOTIFY, on_notify)

        # Test 1: Write wang packets directly to IMAGE_UPLOAD
        print(f"\n=== Writing wang 'HI' to IMAGE_UPLOAD directly ===")
        packets = build_wang_packets("HI")
        for i, packet in enumerate(packets):
            print(f"  Packet {i}: {packet.hex()}")
            await client.write_gatt_char(Characteristics.IMAGE_UPLOAD, packet, response=False)
            await asyncio.sleep(0.05)

        print("  Setting MODE...")
        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        # Test 2: Try WRITE_3 characteristic
        print(f"\n=== Writing wang 'HI' to WRITE_3 ===")
        WRITE_3 = "d44bc439-abfd-45a2-b575-92541612960b"
        packets = build_wang_packets("HI")
        for i, packet in enumerate(packets):
            print(f"  Packet {i}: {packet.hex()}")
            await client.write_gatt_char(WRITE_3, packet, response=False)
            await asyncio.sleep(0.05)

        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        # Test 3: Write encrypted wang packets to COMMAND
        print(f"\n=== Writing encrypted wang to COMMAND ===")
        cipher = AES.new(AES_KEY, AES.MODE_ECB)
        packets = build_wang_packets("HI")
        for i, packet in enumerate(packets):
            encrypted = cipher.encrypt(packet)
            print(f"  Packet {i}: {encrypted.hex()}")
            await client.write_gatt_char(Characteristics.COMMAND, encrypted, response=True)
            await asyncio.sleep(0.05)

        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        print("  >>> Check badge! <<<")
        await asyncio.sleep(4)

        await client.stop_notify(Characteristics.NOTIFY)
        print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
