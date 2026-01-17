#!/usr/bin/env python3
"""
1. Decrypt the notifications we received
2. Try uploading and then activating with PLAY/IMAGE commands
"""
import asyncio
import sys

sys.path.insert(0, '.')
from badge_controller.encryption import decrypt_response
from badge_controller.commands import Command, ScrollMode
from badge_controller.protocol import Characteristics, AES_KEY
from bleak import BleakClient
from Crypto.Cipher import AES

ADDRESS = sys.argv[1] if len(sys.argv) > 1 else "FE5DCE05-1120-2974-BCBF-7AE2F6A509DF"

# Notifications we received
NOTIFICATIONS = [
    "23663db1dd91971c88cde4642796107c",
    "efc06dd3b73de903702bd2aa7fced35f",
    "e041372d21ca14d912ba49fbb8c504cc",
    "b7882dabe2536709ab8cddb9d5673189",
]

def decrypt_and_show(hex_data: str):
    """Decrypt and display notification."""
    data = bytes.fromhex(hex_data)
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    decrypted = cipher.decrypt(data)

    # Try to extract ASCII
    ascii_part = ""
    for b in decrypted:
        if 0x20 <= b <= 0x7E:
            ascii_part += chr(b)
        else:
            ascii_part += f"[{b:02x}]"

    print(f"  Encrypted: {hex_data}")
    print(f"  Decrypted: {decrypted.hex()}")
    print(f"  ASCII:     {ascii_part}")
    print()


print("=== Decrypting badge notifications ===\n")
for notif in NOTIFICATIONS:
    decrypt_and_show(notif)


# Character 'A' bitmap - 11 rows
CHAR_A = bytes([0x00, 0x38, 0x6C, 0xC6, 0xC6, 0xFE, 0xC6, 0xC6, 0xC6, 0xC6, 0x00])


async def send_encrypted(client: BleakClient, packet: bytes):
    await client.write_gatt_char(Characteristics.COMMAND, packet, response=True)


async def send_image_data(client: BleakClient, data: bytes):
    await client.write_gatt_char(Characteristics.IMAGE_UPLOAD, data, response=False)


async def main():
    print(f"\n=== Trying upload with PLAY/IMAGE activation ===")
    print(f"Connecting to {ADDRESS}...")

    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}\n")

        def on_notify(sender, data):
            cipher = AES.new(AES_KEY, AES.MODE_ECB)
            decrypted = cipher.decrypt(data)
            ascii_str = ''.join(chr(b) if 0x20 <= b <= 0x7E else f'[{b:02x}]' for b in decrypted)
            print(f"  >> Notification: {data.hex()} -> {ascii_str}")

        await client.start_notify(Characteristics.NOTIFY, on_notify)

        # Upload bitmap
        data = CHAR_A
        print(f"1. Sending DATS ({len(data)} bytes)...")
        await send_encrypted(client, Command.data_start(len(data)))
        await asyncio.sleep(0.2)

        print(f"2. Sending bitmap data...")
        await send_image_data(client, data)
        await asyncio.sleep(0.2)

        print(f"3. Sending DATCP...")
        await send_encrypted(client, Command.data_complete())
        await asyncio.sleep(0.5)

        print(f"\n4. Trying PLAY command with image 0...")
        await send_encrypted(client, Command.play([0]))
        await asyncio.sleep(1)
        print("  Check badge now!")
        await asyncio.sleep(2)

        print(f"\n5. Trying IMAGE command with id 0...")
        await send_encrypted(client, Command.image(0))
        await asyncio.sleep(1)
        print("  Check badge now!")
        await asyncio.sleep(2)

        print(f"\n6. Trying IMAGE command with id 1...")
        await send_encrypted(client, Command.image(1))
        await asyncio.sleep(1)
        print("  Check badge now!")
        await asyncio.sleep(2)

        print(f"\n7. Trying MODE STATIC again...")
        await send_encrypted(client, Command.mode(ScrollMode.STATIC))
        await asyncio.sleep(1)

        print(f"\n8. Trying MODE LEFT...")
        await send_encrypted(client, Command.mode(ScrollMode.LEFT))
        await asyncio.sleep(1)

        await client.stop_notify(Characteristics.NOTIFY)
        print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
