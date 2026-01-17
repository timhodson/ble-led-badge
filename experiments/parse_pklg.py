#!/usr/bin/env python3
"""
Parse Apple PacketLogger (.pklg) files to extract BLE ATT writes.
"""
import struct
import sys
from pathlib import Path

def parse_pklg(filepath: Path):
    """Parse a PacketLogger file and extract ATT writes."""
    data = filepath.read_bytes()
    offset = 0
    records = []

    print(f"File size: {len(data)} bytes")

    while offset < len(data) - 8:
        # PacketLogger record format seems to be:
        # [4 bytes: length] [4 bytes: timestamp?] [4 bytes: type?] [data]
        try:
            rec_len = struct.unpack('<I', data[offset:offset+4])[0]

            if rec_len == 0 or rec_len > 10000:  # Sanity check
                offset += 1
                continue

            if offset + 4 + rec_len > len(data):
                break

            rec_data = data[offset+4:offset+4+rec_len]

            # Look for ATT write operations in the data
            # ATT Write Request = 0x12, Write Command = 0x52
            # They appear after L2CAP header (4 bytes) in BLE packets

            # Try to find ATT writes within this record
            for i in range(len(rec_data) - 5):
                # Look for patterns that could be ATT writes
                if rec_data[i] in (0x12, 0x52):  # ATT write opcodes
                    # Check if this looks like a valid ATT write
                    # Next 2 bytes would be handle (little-endian)
                    handle = struct.unpack('<H', rec_data[i+1:i+3])[0]

                    # Valid GATT handles are typically 0x0001-0x00FF for our badge
                    if 0x0001 <= handle <= 0x00FF:
                        value = rec_data[i+3:i+3+20]  # Get up to 20 bytes of value
                        records.append({
                            'offset': offset,
                            'opcode': rec_data[i],
                            'handle': handle,
                            'value': value,
                            'context': rec_data[max(0,i-4):i+25]
                        })

            offset += 4 + rec_len

        except struct.error:
            offset += 1

    return records


def find_att_writes_simple(data: bytes):
    """Simpler approach: scan for ATT write patterns in raw data."""
    writes = []

    # Look for Write Request (0x12) or Write Command (0x52)
    # followed by valid handle bytes
    for i in range(len(data) - 20):
        opcode = data[i]
        if opcode in (0x12, 0x52):
            handle = struct.unpack('<H', data[i+1:i+3])[0]
            # Our badge uses handles like 0x0006, 0x0009, 0x000B, 0x0081
            if handle in (0x0006, 0x0009, 0x000B, 0x000E, 0x0081, 0x0083):
                # Get value - find next occurrence of opcode pattern or limit to 100 bytes
                value_end = i + 3
                while value_end < min(i + 103, len(data)):
                    # Stop at what looks like another ATT packet
                    if data[value_end] in (0x12, 0x52, 0x13, 0x1B) and value_end > i + 5:
                        next_handle = struct.unpack('<H', data[value_end+1:value_end+3])[0]
                        if next_handle in (0x0006, 0x0009, 0x000B, 0x000E, 0x0081, 0x0083):
                            break
                    value_end += 1

                value = data[i+3:value_end]
                # Filter out likely false positives (very short values)
                if len(value) >= 2:
                    writes.append({
                        'offset': i,
                        'opcode': 'Write Request' if opcode == 0x12 else 'Write Command',
                        'handle': handle,
                        'value': value[:50]  # Limit display
                    })

    return writes


def main():
    filepath = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("traces/iPhoneTrace-16-01-2025-btsnoop.btsnoop")

    print(f"Parsing: {filepath}")
    data = filepath.read_bytes()

    writes = find_att_writes_simple(data)

    print(f"\nFound {len(writes)} potential ATT writes:\n")

    seen = set()
    for w in writes:
        # Deduplicate
        key = (w['handle'], w['value'][:16].hex())
        if key in seen:
            continue
        seen.add(key)

        print(f"Handle 0x{w['handle']:04X} - {w['opcode']}")
        print(f"  Value ({len(w['value'])} bytes): {w['value'].hex()}")

        # Try to decode as ASCII where possible
        try:
            ascii_preview = ''.join(chr(b) if 32 <= b < 127 else '.' for b in w['value'][:32])
            print(f"  ASCII: {ascii_preview}")
        except:
            pass
        print()


if __name__ == "__main__":
    main()
