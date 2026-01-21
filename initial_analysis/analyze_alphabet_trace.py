#!/usr/bin/env python3
"""
Analyze the alphabet btsnoop trace to extract font bitmap data for each character.

This trace contains writes of the full alphabet: ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz(,.!?)
"""
import struct
import sys
from pathlib import Path
from Crypto.Cipher import AES

# Add project root for imports
sys.path.insert(0, str(Path(__file__).parent))
from badge_controller.protocol import AES_KEY

# Initialize cipher for decryption
cipher = AES.new(AES_KEY, AES.MODE_ECB)

# Known handles from protocol analysis
HANDLE_COMMAND = 0x0006  # Encrypted commands (characteristic 9600)
HANDLE_NOTIFY = 0x0009   # Notifications
HANDLE_IMAGE = 0x000E    # Image upload (characteristic 960a)
HANDLE_WRITE3 = 0x000B   # Third write channel (characteristic 960b)


def find_att_writes(data: bytes):
    """
    Scan for ATT write patterns in the raw trace data.
    This is a simple pattern-matching approach for Apple PacketLogger format.
    """
    writes = []
    handles_of_interest = {0x0006, 0x0009, 0x000B, 0x000E, 0x0081, 0x0083, 0x0014}

    for i in range(len(data) - 20):
        opcode = data[i]
        if opcode in (0x12, 0x52):  # Write Request / Write Command
            handle = struct.unpack('<H', data[i+1:i+3])[0]

            if handle in handles_of_interest:
                # Find end of value - look for next ATT packet or limit
                value_end = i + 3
                max_len = min(i + 120, len(data))

                while value_end < max_len:
                    # Stop at likely next ATT packet
                    if value_end > i + 5 and data[value_end] in (0x12, 0x52, 0x13, 0x1B):
                        next_handle = struct.unpack('<H', data[value_end+1:value_end+3])[0]
                        if next_handle in handles_of_interest:
                            break
                    value_end += 1

                value = data[i+3:value_end]
                if len(value) >= 2:
                    writes.append({
                        'offset': i,
                        'opcode': opcode,
                        'handle': handle,
                        'value': value
                    })

    return writes


def decrypt_block(data: bytes) -> bytes:
    """Decrypt a 16-byte AES-ECB block."""
    if len(data) < 16:
        return None
    return cipher.decrypt(data[:16])


def decode_command(encrypted_data: bytes) -> str:
    """Decrypt and decode a command packet."""
    decrypted = decrypt_block(encrypted_data)
    if not decrypted:
        return None

    # Format: [length][command...][padding]
    length = decrypted[0]
    if length > 15:
        return None

    cmd_bytes = decrypted[1:1+length]
    # Try to decode as ASCII
    try:
        return cmd_bytes.decode('ascii', errors='replace')
    except:
        return cmd_bytes.hex()


def analyze_trace(filepath: Path):
    """Main analysis function."""
    data = filepath.read_bytes()
    print(f"File size: {len(data)} bytes")

    # Find all ATT writes
    writes = find_att_writes(data)
    print(f"Found {len(writes)} ATT write operations")

    # Group by handle
    by_handle = {}
    for w in writes:
        h = w['handle']
        if h not in by_handle:
            by_handle[h] = []
        by_handle[h].append(w)

    print("\nWrites by handle:")
    for h in sorted(by_handle.keys()):
        print(f"  Handle 0x{h:04X}: {len(by_handle[h])} writes")

    # Analyze command writes (encrypted)
    print("\n" + "="*60)
    print("ENCRYPTED COMMANDS (Handle 0x0006)")
    print("="*60)

    if 0x0006 in by_handle:
        seen_cmds = set()
        for w in by_handle[0x0006][:30]:  # First 30 commands
            cmd = decode_command(w['value'])
            if cmd and cmd not in seen_cmds:
                seen_cmds.add(cmd)
                print(f"  {cmd}")

    # Look for image upload data
    print("\n" + "="*60)
    print("IMAGE UPLOAD DATA")
    print("="*60)

    # Check each handle for image data patterns
    for handle in sorted(by_handle.keys()):
        writes_list = by_handle[handle]
        if len(writes_list) < 5:
            continue

        # Concatenate all values
        all_values = []
        for w in writes_list:
            all_values.append(w['value'])

        # Check for image upload patterns
        # Image packets typically start with a sequence byte
        first_val = all_values[0] if all_values else b''
        print(f"\nHandle 0x{handle:04X}:")
        print(f"  {len(writes_list)} writes, first value: {first_val[:30].hex()}")

        # Try decryption on first value
        if len(first_val) >= 16:
            dec = decrypt_block(first_val)
            if dec:
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in dec)
                print(f"  Decrypted: {dec.hex()}")
                print(f"  ASCII: {ascii_str}")

    return by_handle


def extract_bitmap_from_handle(writes_list, expected_text: str):
    """
    Try to extract font bitmap data from a sequence of writes.

    For the badge protocol, image data is sent as:
    - Packets with sequence byte followed by bitmap data
    - Each character is 9 bytes (9 columns of 8 pixels each)
    """
    # Concatenate all write values
    all_data = bytearray()
    for w in writes_list:
        all_data.extend(w['value'])

    print(f"\nTotal raw data: {len(all_data)} bytes")
    print(f"Expected for {len(expected_text)} chars @ 9 bytes: {len(expected_text) * 9} bytes")

    # The expected text
    # ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz(,.!?)
    # = 26 + 26 + 5 = 57 characters = 513 bytes

    # Print first 100 bytes as hex for analysis
    print(f"\nFirst 100 bytes: {all_data[:100].hex()}")

    return all_data


def visualize_char(data: list, char: str, compact: bool = False):
    """
    Visualize a character bitmap (9 columns, 11 rows).

    The badge uses a column-based format:
    - Each byte represents one vertical column (9 columns total)
    - Bit 0 of each byte is the topmost pixel of that column
    - The display is 11 rows tall (bits 0-10, using lower bits)
    """
    if len(data) < 9:
        print(f"  (insufficient data: {len(data)} bytes)")
        return

    if not compact:
        print(f"\n'{char}': {[f'0x{b:02x}' for b in data]}")

    # Display 11 rows (the badge matrix height)
    for row in range(11):
        line = ""
        for col in range(9):
            # Check if this pixel is set
            # The 9-byte format stores columns, bit 0 = top
            if col < len(data) and (data[col] & (1 << row)):
                line += "##"
            else:
                line += "  "
        if not compact or any(c != ' ' for c in line):
            print(f"  |{line}|")


def extract_writes_from_raw(data: bytes, handle: int = 0x0009):
    """
    Extract all write values to a specific handle by scanning raw bytes.
    Looking for pattern: 0x12 [handle_lo] [handle_hi] [value...]
    """
    writes = []
    handle_lo = handle & 0xFF
    handle_hi = (handle >> 8) & 0xFF

    i = 0
    while i < len(data) - 20:
        # Look for Write Request (0x12) or Write Command (0x52) with correct handle
        if data[i] == 0x12 and data[i+1] == handle_lo and data[i+2] == handle_hi:
            # Found a write - extract the value
            # The value continues until we hit another pattern or limit
            value_start = i + 3
            value_end = value_start

            # Look for the next packet indicator or limit to ~100 bytes
            while value_end < min(i + 103, len(data)):
                # Check for patterns that indicate next packet
                if value_end - value_start > 10:
                    # Check for common packet boundaries
                    if data[value_end:value_end+2] == b'\x12\x09':
                        break
                    if data[value_end:value_end+2] == b'\x52\x09':
                        break
                    # Also check for timestamp patterns (0x35 0x6f 0x69 = "5oi")
                    if data[value_end:value_end+3] == b'5oi':
                        # Back up to find the actual boundary
                        while value_end > value_start and data[value_end-1] in (0x00, 0x01, 0x02, 0x03, 0x04):
                            value_end -= 1
                        break
                value_end += 1

            value = data[value_start:value_end]
            if len(value) >= 16:  # Valid AES block size
                writes.append({
                    'offset': i,
                    'value': value[:16]  # First 16 bytes (AES block)
                })

            i = value_end
        else:
            i += 1

    return writes


def main():
    trace_path = Path("traces/alphabet-trace.btsnoop")

    if not trace_path.exists():
        print(f"Trace file not found: {trace_path}")
        return

    print(f"Analyzing: {trace_path}")
    data = trace_path.read_bytes()

    # Extract writes to handle 0x0009
    writes = extract_writes_from_raw(data, handle=0x0009)
    print(f"Found {len(writes)} writes to handle 0x0009")

    # Decrypt each write and look for bitmap data
    print("\n" + "="*60)
    print("DECRYPTED DATA FROM HANDLE 0x0009")
    print("="*60)

    all_bitmap_data = bytearray()
    seen_blocks = set()

    for i, w in enumerate(writes):
        dec = decrypt_block(w['value'])
        if dec:
            hex_str = dec.hex()
            if hex_str not in seen_blocks:
                seen_blocks.add(hex_str)
                print(f"\n#{i}: Offset {w['offset']}")
                print(f"  Encrypted: {w['value'].hex()}")
                print(f"  Decrypted: {hex_str}")
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in dec)
                print(f"  ASCII: {ascii_str}")

                # Check if this looks like bitmap data (not a command)
                # Commands start with a length byte followed by ASCII
                if not (32 <= dec[1] < 127 and 32 <= dec[2] < 127):
                    # This might be image data
                    all_bitmap_data.extend(dec)

    print("\n" + "="*60)
    print("POTENTIAL BITMAP DATA")
    print("="*60)
    print(f"Total collected: {len(all_bitmap_data)} bytes")
    print(f"First 64 bytes: {all_bitmap_data[:64].hex()}")

    # Expected text from the trace
    # A-Z, a-z, then 4 card suit emojis (each taking 2 slots = 8 blank positions), then ,.!?
    expected_text = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz________,.!?"
    # 8 underscores represent the 4 emoji characters (2 slots each)
    print(f"\nExpected text: A-Z, a-z, [4 emojis x 2 slots = 8 blanks], ,.!?")
    print(f"Character count: {len(expected_text)}")

    # Now let's try to extract font data
    # Each decrypted block is 16 bytes, first byte is 0x0f (length marker)
    # Remaining 15 bytes are bitmap data
    # 9 bytes per character

    print("\n" + "="*60)
    print("EXTRACTING FONT DATA")
    print("="*60)

    # Collect decrypted blocks in order (no deduplication - order matters!)
    all_font_bytes = bytearray()
    block_count = 0

    for i, w in enumerate(writes):
        dec = decrypt_block(w['value'])
        if dec:
            # Check if this looks like font data (not a command)
            # Commands typically have ASCII letters after the length byte
            first_content = dec[1] if len(dec) > 1 else 0

            # Font data packets start with 0x0f or 0x06 and don't have ASCII commands
            if dec[0] == 0x0f and not (65 <= first_content <= 90 or 97 <= first_content <= 122):
                all_font_bytes.extend(dec[1:16])
                block_count += 1
            elif dec[0] == 0x06 and not (65 <= first_content <= 90 or 97 <= first_content <= 122):
                # Shorter final packet
                all_font_bytes.extend(dec[1:7])
                block_count += 1

    print(f"\nCollected {block_count} font data blocks")

    # Debug: show all block decryptions
    print("\n" + "="*60)
    print("ALL DECRYPTED BLOCKS (showing content bytes)")
    print("="*60)
    block_idx = 0
    for i, w in enumerate(writes):
        dec = decrypt_block(w['value'])
        if dec:
            first_content = dec[1] if len(dec) > 1 else 0
            is_font = dec[0] in (0x0f, 0x06) and not (65 <= first_content <= 90 or 97 <= first_content <= 122)
            if is_font:
                content = dec[1:16] if dec[0] == 0x0f else dec[1:7]
                print(f"Block {block_idx}: {content.hex()}")
                block_idx += 1

    print(f"Font data collected: {len(all_font_bytes)} bytes")
    print(f"Expected for {len(expected_text)} chars: {len(expected_text) * 9} bytes")

    # Now extract 9 bytes per character
    font_dict = {}
    bytes_per_char = 9

    for idx, char in enumerate(expected_text):
        start = idx * bytes_per_char
        end = start + bytes_per_char
        if end <= len(all_font_bytes):
            char_data = list(all_font_bytes[start:end])
            font_dict[char] = char_data
            visualize_char(char_data, char)

    # Output as Python dict
    print("\n" + "="*60)
    print("FONT DICTIONARY")
    print("="*60)
    print("FONT = {")
    for char in expected_text:
        if char in font_dict and char != '_':  # Skip placeholder underscores
            hex_list = ', '.join(f'0x{b:02x}' for b in font_dict[char])
            print(f"    {repr(char)}: [{hex_list}],")
    print("}")

    # Show raw bytes at positions 52-60 (blank suits + punctuation)
    print("\n" + "="*60)
    print("RAW DATA AT END OF TRACE (positions 52-60)")
    print("="*60)
    print(f"Total font bytes: {len(all_font_bytes)}")
    print(f"Positions 52-60 (chars 52-59):")
    for pos in range(52, min(60, len(all_font_bytes) // 9)):
        start = pos * 9
        end = start + 9
        if end <= len(all_font_bytes):
            char_data = list(all_font_bytes[start:end])
            hex_list = ', '.join(f'0x{b:02x}' for b in char_data)
            char_label = expected_text[pos] if pos < len(expected_text) else '?'
            print(f"\nPos {pos} ('{char_label}'): [{hex_list}]")
            visualize_char(char_data, char_label, compact=True)

    # Check if there's remaining data
    remaining_start = 60 * 9
    if len(all_font_bytes) > remaining_start:
        print(f"\nRemaining bytes after position 60: {all_font_bytes[remaining_start:].hex()}")


if __name__ == '__main__':
    main()
