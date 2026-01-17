#!/usr/bin/env python3
"""
Parse iPhone trace specifically for badge-related writes and decrypt commands.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, '.')
from badge_controller.protocol import AES_KEY
from Crypto.Cipher import AES

# Badge handles from list_characteristics.py
BADGE_HANDLES = {
    0x0006: "COMMAND",
    0x0009: "IMAGE_UPLOAD",
    0x000B: "WRITE_3",
    0x000E: "NOTIFY_CCCD",
}


def decrypt_command(data: bytes) -> str:
    """Decrypt a command packet and return description."""
    if len(data) != 16:
        return f"[not 16 bytes: {len(data)}]"

    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    decrypted = cipher.decrypt(data)

    # Format: [length][command ASCII][args...][padding]
    length = decrypted[0]
    if length > 15:
        return f"[invalid length {length}]"

    content = decrypted[1:length+1]
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else f'[{b:02x}]' for b in content)
    args_hex = content.hex()

    return f"{ascii_str} (hex: {args_hex})"


def find_badge_writes(data: bytes):
    """Find all badge-related ATT writes."""
    writes = []

    for i in range(len(data) - 20):
        opcode = data[i]
        if opcode not in (0x12, 0x52):  # Write Request/Command
            continue

        handle = struct.unpack('<H', data[i+1:i+3])[0]
        if handle not in BADGE_HANDLES:
            continue

        # Extract value - look for 16-byte aligned data for COMMAND
        # or variable length for IMAGE_UPLOAD
        if handle == 0x0006:  # COMMAND - always 16 bytes encrypted
            value = data[i+3:i+19]
            if len(value) == 16:
                writes.append({
                    'offset': i,
                    'handle': handle,
                    'handle_name': BADGE_HANDLES[handle],
                    'value': value,
                    'opcode': 'Write Request' if opcode == 0x12 else 'Write Command',
                })
        else:
            # For other handles, try to get value until next ATT opcode
            value_end = i + 3
            while value_end < min(i + 120, len(data)):
                # Stop at common BLE patterns
                if value_end + 3 < len(data):
                    next_handle = struct.unpack('<H', data[value_end+1:value_end+3])[0]
                    if data[value_end] in (0x12, 0x52) and next_handle in BADGE_HANDLES:
                        break
                value_end += 1

            value = data[i+3:value_end]
            if len(value) >= 1:
                writes.append({
                    'offset': i,
                    'handle': handle,
                    'handle_name': BADGE_HANDLES[handle],
                    'value': value[:100],  # Limit for display
                    'opcode': 'Write Request' if opcode == 0x12 else 'Write Command',
                })

    return writes


def main():
    filepath = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("traces/iPhoneTrace-16-01-2025-btsnoop.btsnoop")

    print(f"Parsing: {filepath}")
    data = filepath.read_bytes()

    writes = find_badge_writes(data)

    print(f"\nFound {len(writes)} badge writes:\n")

    # Deduplicate and show
    seen = set()
    command_sequence = []
    image_data = bytearray()

    for w in writes:
        key = (w['handle'], w['value'].hex())
        if key in seen:
            continue
        seen.add(key)

        print(f"\n[{w['handle_name']}] Handle 0x{w['handle']:04X}")
        print(f"  Raw: {w['value'].hex()}")

        if w['handle'] == 0x0006:  # COMMAND - decrypt
            decrypted = decrypt_command(w['value'])
            print(f"  Decrypted: {decrypted}")
            command_sequence.append(decrypted)
        elif w['handle'] == 0x0009:  # IMAGE_UPLOAD
            print(f"  Length: {len(w['value'])} bytes")
            ascii_preview = ''.join(chr(b) if 32 <= b < 127 else '.' for b in w['value'][:40])
            print(f"  ASCII: {ascii_preview}")
            image_data.extend(w['value'])

    print("\n" + "="*60)
    print("COMMAND SEQUENCE (decrypted):")
    print("="*60)
    for i, cmd in enumerate(command_sequence):
        print(f"  {i+1}. {cmd}")

    if image_data:
        print("\n" + "="*60)
        print(f"IMAGE_UPLOAD DATA ({len(image_data)} bytes total):")
        print("="*60)
        print(f"  First 100 bytes: {image_data[:100].hex()}")
        ascii_all = ''.join(chr(b) if 32 <= b < 127 else '.' for b in image_data[:100])
        print(f"  ASCII: {ascii_all}")


if __name__ == "__main__":
    main()
