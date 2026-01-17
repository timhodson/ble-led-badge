# BLE LED Badge Protocol Analysis

## Known Protocol Information

From reverse-engineered "Shining Masks" protocol (https://gist.github.com/Staars/71e63e4bdefc7e3fd22377bf9c50ac12):

- **Encryption**: AES-ECB with key: `32 67 2f 79 74 ad 43 45 1d 9c 6c 89 4a 0e 87 64`
- **Command Characteristic**: `d44bc439-abfd-45a2-b575-925416129600` (Handle 0x0006)
- **Image Upload Characteristic**: `d44bc439-abfd-45a2-b575-92541612960a`
- **Notify Characteristic**: `d44bc439-abfd-45a2-b575-925416129601`

## Original Captured Packets

### Turn badge off BLE packet

Write Request - Handle:0x0006 - D44BC439-ABFD-45A2-B575-925416129600 - Value: CBB1 FDBF C560 D5E4 53C2 CBD9 28B5 3FAB

### Turn badge on BLE packet

Write Request - Handle:0x0006 - Value: EBD3 72ED 9885 7317 F2F5 4CD2 130F DC9C

### Fast scroll

0000   5f 00 17 00 13 00 04 00 12 06 00 7f ac 12 69 17   _.............i.
0010   0d 88 85 45 8f a5 1c fe 71 08 41                  ...E....q.A

Extracted payload (16 bytes): `7fac1269170d8885458fa51cfe710841`

### Slow scroll

0000   5f 00 17 00 13 00 04 00 12 06 00 5f 91 d6 ea e4   _.........._....
0010   d3 44 8b a4 c6 4e be 95 0d 78 b8                  .D...N...x.

Extracted payload (16 bytes): `5f91d6eae4d3448ba4c64ebe950d78b8`

---

## BTSnoop Trace Analysis (January 2026)

### Tools Created
- `parse_btsnoop.py` - Parses BTSnoop HCI logs and extracts ATT write operations
- `decrypt_traces.py` - Attempts to decrypt captured packets with known AES key

### Extracted Write Operations from Traces

| Trace | Handle | Encrypted Value (hex) |
|-------|--------|----------------------|
| A-no-scroll #1 | 0x0006 | 361d18ea05dc95e06047553f10edb8e9 |
| A-no-scroll #2 | 0x0009 | ee321ff315ef87b496ff70fd0dbf834d |
| A-no-scroll #3 | 0x0006 | 8ac86ae07a1436224437d4d2c1cf4503 |
| A-no-scroll #4 | 0x0006 | c525a8e825a9f13b6c5ee00b48fa1d52 |
| A-no-scroll #5 | 0x0006 | 12be7e044087149279944078890f457a |
| A-no-scroll #6 | 0x0006 | 4e9ae0e7d5e04af7491651e2e57610a7 |
| FastScroll | 0x0006 | 7fac1269170d8885458fa51cfe710841 |
| LeftScroll | 0x0006 | 0adbfdd9e856e54e61f3c9d35452d5d0 |
| RightScroll | 0x0006 | fdc28903b4aa1f8b586b4d899bc27a94 |
| SlowScroll | 0x0006 | 5f91d6eae4d3448ba4c64ebe950d78b8 |

### Notification Responses Observed

From A-no-scroll trace:
- `0f00efc06dd3b73de903702bd2aa7fced35f` (18 bytes)
- `0f00b7882dabe2536709ab8cddb9d5673189` (18 bytes)

Format appears to be: `[length byte][unknown byte][16 bytes encrypted data][extra byte?]`

### Key Findings - PROTOCOL CRACKED! ✓

**The badge uses the "idealLED" AES key, NOT the "Shining Masks" key!**

```
AES Key: 34 52 2A 5B 7A 6E 49 2C 08 09 0A 9D 8D 2A 23 F8
```

Reference: https://github.com/8none1/idealLED

### Decrypted Commands

| Encrypted | Decrypted | Command | Args | Meaning |
|-----------|-----------|---------|------|---------|
| `cbb1fdbf...` | `064c45444f4646...` | LEDOFF | - | Turn badge off |
| `ebd372ed...` | `054c45444f4e...` | LEDON | - | Turn badge on |
| `361d18ea...` | `08444154530009...` | DATS | 0,9,0,0 | Data transfer start |
| `8ac86ae0...` | `05444154435000...` | DATCP | - | Data complete |
| `c525a8e8...` | `054d4f44450100...` | MODE | 1 | Mode 1 (no scroll/static) |
| `12be7e04...` | `064c4947485432...` | LIGHT | 50 | Brightness level 50 |
| `4e9ae0e7...` | `06535045454432...` | SPEED | 50 | Scroll speed 50 |
| `7fac1269...` | `06535045454460...` | SPEED | 96 | Fast scroll speed |
| `5f91d6ea...` | `06535045454405...` | SPEED | 5 | Slow scroll speed |
| `0adbfdd9...` | `054d4f44450300...` | MODE | 3 | Left scroll |
| `fdc28903...` | `054d4f44450400...` | MODE | 4 | Right scroll |

### Command Reference

| Command | Args | Description |
|---------|------|-------------|
| **LEDON** | - | Turn the badge display on |
| **LEDOFF** | - | Turn the badge display off |
| **MODE** | 1 byte | Set scroll mode: 1=static, 3=left, 4=right |
| **SPEED** | 1 byte | Set scroll speed (5=slow, 50=medium, 96=fast) |
| **LIGHT** | 1 byte | Set brightness level |
| **DATS** | 4 bytes | Start data/image transfer |
| **DATCP** | - | Data transfer complete |

### Packet Format

```
[length][command][args...][zero padding to 16 bytes]
```
Then encrypted with AES-ECB using the idealLED key.

### Running the Analysis Tools

```bash
# Parse BTSnoop traces
python parse_btsnoop.py

# Parse with verbose output
python parse_btsnoop.py -v traces/A-no-scroll.log

# Show all ATT operations
python parse_btsnoop.py -a traces/A-no-scroll.log

# Try decryption with known key (for comparison)
poetry run python decrypt_traces.py
```

---

## Text/Image Upload Protocol (January 2026)

### Discovery Process

The text upload protocol was reverse-engineered by capturing Bluetooth traces from the official iPhone app ("LED Badge" app) using Apple's Bluetooth Debug Profile and analyzing the packets.

Key insight: The IMAGE_UPLOAD data is **encrypted** with the same AES key as commands, not plaintext.

### Working Protocol Flow

To display text on the badge:

1. **DATS** (Data Start) - Send to COMMAND characteristic (0x0006)
   - Format: `DATS[0x00][length][0x00][0x00]`
   - `length` = total bytes of bitmap data (9 bytes per character)
   - Badge responds with `DATSOK` via NOTIFY characteristic

2. **Image Data** - Send to IMAGE_UPLOAD characteristic (0x0009)
   - Data is split into 16-byte packets
   - Each packet format (before encryption): `[chunk_length][data...][zero padding to 16 bytes]`
   - Maximum 15 bytes of data per packet (1 byte for length prefix)
   - Each packet is AES-ECB encrypted before sending

3. **DATCP** (Data Complete) - Send to COMMAND characteristic (0x0006)
   - Signals end of data transfer
   - Badge responds with `DATCPOK` via NOTIFY characteristic

4. **MODE** - Set scroll mode (1=static, 3=left, 4=right)

5. **LIGHT** - Set brightness (0-255)

6. **SPEED** - Set scroll speed (0-255)

### Font Format

The badge uses a **column-based bitmap font**:
- 9 bytes per character
- Each byte represents a vertical column of 8 pixels
- Bit 0 is at the top, bit 7 at the bottom
- Characters are 9 pixels wide × 8 pixels tall

Example - Letter 'B' from trace:
```
Bytes: [0x20, 0x4c, 0x3f, 0x24, 0x44, 0x24, 0x1b, 0x80, 0x00]

Visual (each column is one byte, bit 0 at top):
Col:  0    1    2    3    4    5    6    7    8
      0x20 0x4c 0x3f 0x24 0x44 0x24 0x1b 0x80 0x00
```

### Verified Working Characters

Characters extracted from iPhone app traces (exact byte patterns):
- Uppercase: B, M
- Lowercase: a, c, d, e, g, i, n, r
- Space

### Characteristics Used

| Characteristic | Handle | UUID | Purpose |
|---------------|--------|------|---------|
| COMMAND | 0x0006 | d44bc439-abfd-45a2-b575-925416129600 | Encrypted commands |
| IMAGE_UPLOAD | 0x0009 | d44bc439-abfd-45a2-b575-92541612960a | Encrypted image data |
| NOTIFY | - | d44bc439-abfd-45a2-b575-925416129601 | Response notifications |

### Example: Sending "Badger"

```python
# 1. Calculate data length: 6 chars × 9 bytes = 54 bytes
# 2. Send DATS command
DATS[0x00][0x36][0x00][0x00]  # 0x36 = 54

# 3. Send encrypted image packets (54 bytes split into 4 packets)
# Packet 1: [15][15 bytes of data][padding] -> encrypt
# Packet 2: [15][15 bytes of data][padding] -> encrypt
# Packet 3: [15][15 bytes of data][padding] -> encrypt
# Packet 4: [9][9 bytes of data][padding]   -> encrypt

# 4. Send DATCP command
# 5. Send MODE, LIGHT, SPEED commands
```

### What Didn't Work

During reverse engineering, several approaches were tried that failed:
- "wang" header protocol (from nilhcem.com) - different badge type
- Unencrypted image data - badge expects encrypted packets
- Row-based font format - badge uses column-based format
- Writing to ae01 characteristic - different service, not used for text

All failed experiments are preserved in the `experiments/` directory.

---

## References

- [idealLED Protocol Analysis](https://github.com/8none1/idealLED) - Source of the correct AES key
- [Shining Masks Protocol](https://gist.github.com/Staars/71e63e4bdefc7e3fd22377bf9c50ac12) - Alternative protocol for similar devices
- [Reverse Engineering BLE Devices](https://reverse-engineering-ble-devices.readthedocs.io/) - General guide
- [BLE LED Name Badge (Nilhcem)](http://nilhcem.com/iot/reverse-engineering-bluetooth-led-name-badge) - Similar project

## Tools Used

- **LightBlue** - iOS BLE scanner for advertising data capture
- **Wireshark** - Network protocol analyzer
- **Apple Bluetooth Debug Profile** - For BTSnoop log capture on macOS/iOS
- **Python + pycryptodome** - For AES decryption testing
