# BLE LED Badge Controller

A Python project for controlling BLE-enabled LED badges via Bluetooth Low Energy (BLE). This project allows you to send text and graphics to LED name badges that use the standard BLE LED badge protocol.

## Overview

This project provides tools to scan for BLE devices, connect to LED badges, and send custom text messages that are rendered as dot matrix graphics on the badge display.

## Files

### Main Application Files

#### [badge-1.py](badge-1.py)
Main script to connect to a BLE LED badge and write display data. Contains pre-defined write requests for sending specific text and graphics to the badge. Uses the Bleak library for BLE communication.

**Key features:**
- Connects to a specific badge by MAC address
- Sends a series of hexadecimal write requests to the FEE1 characteristic
- Demonstrates the basic protocol for badge communication

#### [character_mapper.py](character_mapper.py)
A comprehensive character mapping class that converts text strings into 8x11 dot matrix representations suitable for LED badge displays.

**Key features:**
- `CharacterMapper` class with support for both GFX fonts and legacy bitmap fonts
- Converts individual characters to bitmap matrices
- Validates character support and string compatibility
- Methods for batch conversion of strings to display matrices
- Legacy font includes full ASCII character set with dot matrix patterns

### Utility Scripts

#### [ble_scan.py](ble_scan.py)
Simple BLE device scanner that discovers and lists all available Bluetooth Low Energy devices in range.

**Usage:** Run to find the MAC address of your LED badge before connecting.

#### [list_characteristics.py](list_characteristics.py)
Diagnostic tool to enumerate all BLE services, characteristics, and descriptors on a connected device. Attempts to read values from each characteristic when possible.

**Usage:** Helpful for exploring the BLE structure of your badge or debugging connection issues.

#### [experiment.py](experiment.py)
Test script demonstrating the `CharacterMapper` functionality. Converts a sample string ("Hello, BLE!") to dot matrix format and prints the binary representation.

**Usage:** Run to see how text is converted to bitmap matrices.

#### [test_gfx_fonts.py](test_gfx_fonts.py)
Comprehensive test suite for the character mapping system. Demonstrates visual rendering of character bitmaps with multiple display styles.

**Features:**
- Tests both GFX and legacy font systems
- Multiple visualization styles (hash, block, ASCII, minimal)
- Visual comparison of different font rendering methods
- Useful for debugging font implementations

### Configuration and Documentation

#### [pyproject.toml](pyproject.toml)
Poetry project configuration file defining:
- Project metadata (name, version, author, license)
- Python version requirement (^3.8)
- Dependencies (Bleak ^0.20.2 for BLE communication)

#### [Analysis.md](Analysis.md)
Technical documentation containing captured BLE packet data for various badge operations:
- Turn badge on/off commands
- Fast and slow scroll configurations
- Raw hex packet dumps for reverse engineering

## Dependencies

- **Python 3.8+**
- **Bleak 0.20.2+** - Cross-platform BLE library for Python

## Installation

```bash
# Install with poetry
poetry install

# Or install dependencies directly
pip install bleak
```

## Quick Start

1. **Find your badge:**
   ```bash
   python ble_scan.py
   ```

2. **Update the MAC address** in [badge-1.py](badge-1.py) with your badge's address

3. **Run the badge controller:**
   ```bash
   python badge-1.py
   ```

## Project Structure

```
ble-led-badge/
├── badge-1.py              # Main badge control script
├── character_mapper.py     # Text-to-bitmap conversion
├── ble_scan.py            # BLE device scanner
├── list_characteristics.py # BLE diagnostic tool
├── experiment.py          # Character mapper demo
├── test_gfx_fonts.py      # Font testing suite
├── pyproject.toml         # Project configuration
├── Analysis.md            # Protocol documentation
└── README.md             # This file
```

## How It Works

1. **Connection**: Uses Bleak to establish a BLE connection with the badge
2. **Character Conversion**: Text is converted to 8x11 dot matrix bitmaps using `CharacterMapper`
3. **Protocol**: Data is sent as hex-encoded byte arrays to the FEE1 characteristic UUID
4. **Display**: The badge renders the bitmap data on its LED matrix

## Notes

- The badge characteristic UUID is: `d44bc439-abfd-45a2-b575-925416129600`
- Default connection uses the FEE1 characteristic for write operations
- The badge supports various display modes (scrolling speed, effects, etc.)
- See [Analysis.md](Analysis.md) for protocol details and packet structures

## License

MIT
