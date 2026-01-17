#!/usr/bin/env python3
"""Decrypt the ae02 responses we received."""
import sys
sys.path.insert(0, '.')
from badge_controller.protocol import AES_KEY
from Crypto.Cipher import AES

# Responses from ae02 (17 bytes each - 1 byte prefix + 16 encrypted)
responses = [
    "019e43df377b3a46ce751634667e215de5",
    "0138ac4a71937eae3e15d3ae5b96b3207f",
    "01c1a285baa9c9177543c13b1132a550d4",
    "01dc2156a533bd2823d9560d65d475fded",
]

cipher = AES.new(AES_KEY, AES.MODE_ECB)

print("Decrypting ae02 responses:\n")
for resp in responses:
    data = bytes.fromhex(resp)
    prefix = data[0]
    encrypted = data[1:17]

    decrypted = cipher.decrypt(encrypted)
    ascii_str = ''.join(chr(b) if 0x20 <= b <= 0x7E else f'[{b:02x}]' for b in decrypted)

    print(f"Raw: {resp}")
    print(f"  Prefix: 0x{prefix:02x}")
    print(f"  Decrypted hex: {decrypted.hex()}")
    print(f"  Decrypted ASCII: {ascii_str}")
    print()
