#!/usr/bin/env python3
"""
Try decrypting the IMAGE_UPLOAD data from the trace.
"""
import sys
sys.path.insert(0, '.')
from badge_controller.protocol import AES_KEY
from Crypto.Cipher import AES

cipher = AES.new(AES_KEY, AES.MODE_ECB)

# First IMAGE_UPLOAD blocks from trace (first 16 bytes of each)
image_blocks = [
    "75d9307b730cd85c69bf0187c9c82ab6",  # First upload packet for "Badger"
    "1f4e5c00b5d28182b3b6e69dcfa713f3",
    "8f8f6313de11b1b62263ce9fa958db0f",
    "fef47c4c1cb36e3cf0aa2ba47d368656",
]

print("Decrypting IMAGE_UPLOAD data:\n")

for i, block_hex in enumerate(image_blocks):
    block = bytes.fromhex(block_hex)
    decrypted = cipher.decrypt(block)

    ascii_str = ''.join(chr(b) if 32 <= b < 127 else f'[{b:02x}]' for b in decrypted)

    print(f"Block {i+1}:")
    print(f"  Encrypted: {block_hex}")
    print(f"  Decrypted: {decrypted.hex()}")
    print(f"  ASCII: {ascii_str}")
    print()

# Also try the second sequence (Magician)
print("\nSecond sequence (Magician):\n")
magician_blocks = [
    "79e078251a259de8f071834f36c8b6b6",
    "57c94f81af1a5fe6ddd891888c881f2b",
    "9a24f2ce133f53795ae95631eb5210d7",
    "a0f9af8081682f1d21d188cff8407d61",
    "51a1023a2fc89411df75bbccd6ad96d8",
]

for i, block_hex in enumerate(magician_blocks):
    block = bytes.fromhex(block_hex)
    decrypted = cipher.decrypt(block)

    ascii_str = ''.join(chr(b) if 32 <= b < 127 else f'[{b:02x}]' for b in decrypted)

    print(f"Block {i+1}:")
    print(f"  Encrypted: {block_hex}")
    print(f"  Decrypted: {decrypted.hex()}")
    print(f"  ASCII: {ascii_str}")
    print()
