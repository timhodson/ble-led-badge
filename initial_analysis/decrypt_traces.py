#!/usr/bin/env python3
"""
Decrypt captured BLE packets from BTSnoop traces using known AES key.
"""
from Crypto.Cipher import AES

# AES key from protocol.py
AES_KEY = bytes([
    0x32, 0x67, 0x2f, 0x79, 0x74, 0xad, 0x43, 0x45,
    0x1d, 0x9c, 0x6c, 0x89, 0x4a, 0x0e, 0x87, 0x64
])


def decrypt(data: bytes) -> bytes:
    """Decrypt a 16-byte packet using AES-ECB."""
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    return cipher.decrypt(data)


def format_decrypted(decrypted: bytes) -> str:
    """Format decrypted data showing ASCII and hex."""
    # Try to find ASCII command portion
    ascii_part = ""
    hex_part = decrypted.hex()

    # First byte is usually length
    length = decrypted[0]

    # Try to extract ASCII command
    try:
        for i in range(1, min(length + 1, len(decrypted))):
            c = decrypted[i]
            if 0x20 <= c <= 0x7E:  # Printable ASCII
                ascii_part += chr(c)
            else:
                ascii_part += f"[{c:02x}]"
    except:
        pass

    return f"len={length}, content: {ascii_part!r}, hex: {hex_part}"


# Captured encrypted packets from traces
captures = {
    "Analysis.md - Badge OFF": bytes.fromhex("CBB1FDBFC560D5E453C2CBD928B53FAB"),
    "Analysis.md - Badge ON": bytes.fromhex("EBD372ED98857317F2F54CD2130FDC9C"),
    "Analysis.md - Fast scroll": bytes.fromhex("7fac1269170d8885458fa51cfe710841"),
    "Analysis.md - Slow scroll": bytes.fromhex("5f91d6eae4d3448ba4c64ebe950d78b8"),

    # From parsed traces
    "A-no-scroll Write 1": bytes.fromhex("361d18ea05dc95e06047553f10edb8e9"),
    "A-no-scroll Write 2 (handle 0x09)": bytes.fromhex("ee321ff315ef87b496ff70fd0dbf834d"),
    "A-no-scroll Write 3": bytes.fromhex("8ac86ae07a1436224437d4d2c1cf4503"),
    "A-no-scroll Write 4": bytes.fromhex("c525a8e825a9f13b6c5ee00b48fa1d52"),
    "A-no-scroll Write 5": bytes.fromhex("12be7e044087149279944078890f457a"),
    "A-no-scroll Write 6": bytes.fromhex("4e9ae0e7d5e04af7491651e2e57610a7"),

    "FastScroll Write 1": bytes.fromhex("7fac1269170d8885458fa51cfe710841"),
    "LeftScroll Write 1": bytes.fromhex("0adbfdd9e856e54e61f3c9d35452d5d0"),
    "RightScroll Write 1": bytes.fromhex("fdc28903b4aa1f8b586b4d899bc27a94"),
    "SlowScroll Write 1": bytes.fromhex("5f91d6eae4d3448ba4c64ebe950d78b8"),
}

print("Decrypting captured BLE packets using known AES key...\n")
print("="*70)

for name, encrypted in captures.items():
    print(f"\n{name}")
    print(f"  Encrypted: {encrypted.hex()}")
    decrypted = decrypt(encrypted)
    print(f"  Decrypted: {format_decrypted(decrypted)}")
    print(f"  Raw bytes: {' '.join(f'{b:02x}' for b in decrypted)}")

print("\n" + "="*70)
print("\nLet's see what known commands encrypt to:")
print("-" * 50)

def encrypt(data: bytes) -> bytes:
    """Encrypt data using AES-ECB."""
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    # Pad to 16 bytes
    if len(data) < 16:
        data = data + bytes(16 - len(data))
    return cipher.encrypt(data[:16])

# Known command format from existing code: [length][command ASCII][args...][padding]
known_commands = {
    "LIGHT 0": b"\x06LIGHT\x00",
    "LIGHT 255": b"\x06LIGHT\xff",
    "ANIM 0": b"\x05ANIM\x00",
    "SPEED 1": b"\x06SPEED\x01",
    "SPEED 5": b"\x06SPEED\x05",
    "PLAY 1,0": b"\x06PLAY\x01\x00",
    "CHEC": b"\x04CHEC",
    "DATS": b"\x06DATS\x00\x00",
}

print("\nExpected encrypted values for known commands:")
for name, cmd in known_commands.items():
    encrypted = encrypt(cmd)
    print(f"  {name}: {encrypted.hex()}")

print("\n" + "="*70)
print("\nTrying byte-reversed decryption:")
print("-" * 50)

for name, encrypted in captures.items():
    # Try with bytes reversed
    reversed_enc = bytes(reversed(encrypted))
    decrypted = decrypt(reversed_enc)
    print(f"\n{name} (reversed)")
    print(f"  Decrypted: {format_decrypted(decrypted)}")
    print(f"  Raw: {' '.join(f'{b:02x}' for b in decrypted)}")

print("\n" + "="*70)
print("\nSearching for matching encrypted patterns:")
print("-" * 50)

# Let's brute-force search for patterns by encrypting possible commands
import itertools

# Generate possible scroll-related commands
scroll_commands = []
for cmd in ["SCROL", "SCROLL", "MODE", "ANIM", "SPEED", "MOVE", "DIR", "DIREC"]:
    for arg in range(256):
        data = bytes([len(cmd) + 1]) + cmd.encode() + bytes([arg])
        if len(data) <= 16:
            scroll_commands.append((f"{cmd} {arg}", data))

# Also try without length byte
for cmd in ["SCROL", "SCROLL", "MODE", "ANIM", "SPEED", "MOVE"]:
    for arg in range(256):
        data = cmd.encode() + bytes([arg])
        if len(data) <= 16:
            scroll_commands.append((f"NoLen:{cmd} {arg}", data))

# Try to match
target_encrypted = list(captures.values())
for name, cmd_data in scroll_commands:
    encrypted = encrypt(cmd_data)
    if encrypted in target_encrypted:
        idx = target_encrypted.index(encrypted)
        target_name = list(captures.keys())[idx]
        print(f"MATCH! {name} -> {target_name}")
        print(f"  Encrypted: {encrypted.hex()}")

print("\n(No matches found means different command structure or key)")
