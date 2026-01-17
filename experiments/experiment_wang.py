#!/usr/bin/env python3
"""
Experiment: Try the "wang" protocol on different characteristics.
"""
import asyncio
import sys
from bleak import BleakClient

# Badge address from command line or default
ADDRESS = sys.argv[1] if len(sys.argv) > 1 else "YOUR_BADGE_ADDRESS"

# Characteristics to try
CHAR_AE01 = "0000ae01-0000-1000-8000-00805f9b34fb"  # Second service
CHAR_IMAGE = "d44bc439-abfd-45a2-b575-92541612960a"  # IMAGE_UPLOAD
CHAR_WRITE3 = "d44bc439-abfd-45a2-b575-92541612960b"  # WRITE_3

# Simple "A" character bitmap (11 rows, from Nilhcem article)
CHAR_A_11ROW = bytes([0x00, 0x38, 0x6C, 0xC6, 0xC6, 0xFE, 0xC6, 0xC6, 0xC6, 0xC6, 0x00])

# Same but 12 rows (padding at end) - matching STYPE12X48N
CHAR_A_12ROW = bytes([0x00, 0x38, 0x6C, 0xC6, 0xC6, 0xFE, 0xC6, 0xC6, 0xC6, 0xC6, 0x00, 0x00])


def build_wang_packets(text: str, rows: int = 12) -> list[bytes]:
    """Build packets using the 'wang' protocol."""
    packets = []

    # Packet 1: Header "wang" + message lengths
    # Bytes 0-3: "wang"
    # Bytes 4-5: length of message 1 (2 bytes, but seems to be just the char count)
    # Bytes 6-15: lengths of messages 2-8 (zeros if not used)
    header = bytearray(16)
    header[0:4] = b'wang'
    header[4] = 0x00
    header[5] = len(text)  # Number of characters
    packets.append(bytes(header))

    # Packet 2: Timestamp (can be zeros)
    timestamp = bytes(16)
    packets.append(timestamp)

    # Packet 3: Separator/padding
    separator = bytes(16)
    packets.append(separator)

    # Remaining packets: bitmap data
    # Each character is `rows` bytes
    bitmap = bytearray()
    for char in text:
        if char == 'A':
            if rows == 12:
                bitmap.extend(CHAR_A_12ROW)
            else:
                bitmap.extend(CHAR_A_11ROW)
        else:
            # Use space (all zeros) for other chars
            bitmap.extend(bytes(rows))

    # Split bitmap into 16-byte packets
    for i in range(0, len(bitmap), 16):
        chunk = bitmap[i:i+16]
        if len(chunk) < 16:
            chunk = chunk + bytes(16 - len(chunk))
        packets.append(bytes(chunk))

    return packets


async def try_characteristic(client: BleakClient, char_uuid: str, packets: list[bytes], name: str):
    """Try sending packets to a characteristic."""
    print(f"\n--- Trying {name} ({char_uuid}) ---")
    try:
        for i, packet in enumerate(packets):
            print(f"  Packet {i}: {packet.hex()}")
            await client.write_gatt_char(char_uuid, packet, response=False)
            await asyncio.sleep(0.05)
        print(f"  SUCCESS: All packets sent to {name}")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


async def main():
    print(f"Connecting to {ADDRESS}...")

    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")

        # Build packets for "A"
        packets_11 = build_wang_packets("A", rows=11)
        packets_12 = build_wang_packets("A", rows=12)

        print("\n=== Testing with 12-row bitmap (matches STYPE12X48N) ===")

        # Try ae01 first (the unexplored characteristic)
        await try_characteristic(client, CHAR_AE01, packets_12, "AE01 (new service)")
        await asyncio.sleep(1)

        # Try IMAGE_UPLOAD without encryption
        await try_characteristic(client, CHAR_IMAGE, packets_12, "IMAGE_UPLOAD")
        await asyncio.sleep(1)

        # Try WRITE_3
        await try_characteristic(client, CHAR_WRITE3, packets_12, "WRITE_3")
        await asyncio.sleep(1)

        print("\n=== Testing with 11-row bitmap ===")
        await try_characteristic(client, CHAR_AE01, packets_11, "AE01 (11-row)")
        await asyncio.sleep(1)

        print("\n=== Done! Check if badge display changed ===")


if __name__ == "__main__":
    asyncio.run(main())
