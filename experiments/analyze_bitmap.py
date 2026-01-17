#!/usr/bin/env python3
"""
Extract and analyze the bitmap data from the decrypted IMAGE_UPLOAD packets.
Format: [length_byte][data...][padding to 16 bytes]
"""
import sys
sys.path.insert(0, '.')
from badge_controller.protocol import AES_KEY
from Crypto.Cipher import AES

cipher = AES.new(AES_KEY, AES.MODE_ECB)

# Encrypted blocks for "Badger" (from trace)
badger_blocks = [
    "75d9307b730cd85c69bf0187c9c82ab6",
    "1f4e5c00b5d28182b3b6e69dcfa713f3",
    "8f8f6313de11b1b62263ce9fa958db0f",
    "fef47c4c1cb36e3cf0aa2ba47d368656",
]

# Encrypted blocks for "Magician" (from trace)
magician_blocks = [
    "79e078251a259de8f071834f36c8b6b6",
    "57c94f81af1a5fe6ddd891888c881f2b",
    "9a24f2ce133f53795ae95631eb5210d7",
    "a0f9af8081682f1d21d188cff8407d61",
    "51a1023a2fc89411df75bbccd6ad96d8",
]


def extract_bitmap_data(encrypted_blocks):
    """Decrypt blocks and extract bitmap data (skip length byte, remove padding)."""
    all_data = bytearray()

    for block_hex in encrypted_blocks:
        block = bytes.fromhex(block_hex)
        decrypted = cipher.decrypt(block)

        length = decrypted[0]
        data = decrypted[1:1+length]
        all_data.extend(data)

    return bytes(all_data)


def visualize_bitmap(data: bytes, chars: int, rows_per_char: int = 9):
    """Visualize bitmap data as text."""
    print(f"\nBitmap visualization ({chars} chars × {rows_per_char} rows):")
    print("-" * 50)

    bytes_per_char = rows_per_char
    for char_idx in range(chars):
        start = char_idx * bytes_per_char
        char_data = data[start:start+bytes_per_char]

        print(f"\nChar {char_idx + 1} (bytes: {char_data.hex()}):")
        for row_idx, byte in enumerate(char_data):
            # Display as binary pattern
            bits = f"{byte:08b}"
            visual = bits.replace('0', ' ').replace('1', '█')
            print(f"  Row {row_idx}: {visual} ({byte:02x})")


print("="*60)
print("BADGER (6 characters)")
print("="*60)

badger_data = extract_bitmap_data(badger_blocks)
print(f"\nExtracted {len(badger_data)} bytes")
print(f"Raw hex: {badger_data.hex()}")
visualize_bitmap(badger_data, 6, 9)


print("\n" + "="*60)
print("MAGICIAN (8 characters)")
print("="*60)

magician_data = extract_bitmap_data(magician_blocks)
print(f"\nExtracted {len(magician_data)} bytes")
print(f"Raw hex: {magician_data.hex()}")
visualize_bitmap(magician_data, 8, 9)
