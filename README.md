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

## Badge Controller CLI

The `badge-controller` CLI provides a convenient way to interact with your LED badge. First, set your badge address as an environment variable:

```bash
# Set your badge address (find it using the scan command)
export BADGE_ADDR="AA:BB:CC:DD:EE:FF"
```

### Available Commands

#### Scan for devices
```bash
# Find nearby BLE devices (default 10 second timeout)
badge-controller scan

# Custom timeout
badge-controller scan --timeout 20
```

#### Send text to the badge
```bash
# Basic text (scrolls left by default)
# NOT WORKING
badge-controller text $BADGE_ADDR "Hello World"

# Static text (no scrolling)
# scroll option works as expected. left right and static
badge-controller text $BADGE_ADDR "Hi!" --scroll static

# Scroll right
badge-controller text $BADGE_ADDR "Welcome" --scroll right

# With custom brightness (0-255)
# brightness works as expected, but is not saved between badge power cycles.
badge-controller text $BADGE_ADDR "Bright!" --brightness 255

# With custom speed (0-255)
#speed works as expected, but is not saved between badge power cycles.
badge-controller text $BADGE_ADDR "Fast scroll" --speed 100

# Combine options
badge-controller text $BADGE_ADDR "Custom" --scroll left --brightness 200 --speed 75
```

#### Set brightness
```bash
# Set brightness level (0-255)
# works, but not saved between badge power cycles
badge-controller brightness $BADGE_ADDR 128
badge-controller brightness $BADGE_ADDR 255  # Maximum
```

#### Set scroll/transition speed
```bash
# Set speed level (0-255)
#works, but not saved between badge power cycles
badge-controller speed $BADGE_ADDR 50
badge-controller speed $BADGE_ADDR 100  # Faster
```

#### Play animations
```bash
# Play animation by ID
badge-controller animation $BADGE_ADDR 1
badge-controller animation $BADGE_ADDR 2
```
No animation at index 0. Other animations are as follows

1. Falling leaves turn into flashing word love.
2. Four animated hearts
3. Cheers beer tankards
4. The word COME builds with flashing face
5. Two radiating and flashing hearts
6. Animated Dollar signs
7. Two fish kissing
8. Animal face appears and radiates thought waves. I really have no idea what it is supposed to be!

Only eight animations

#### Show stored images
```bash
# Show image by ID
# NEEDS TESTING
badge-controller image $BADGE_ADDR 1
badge-controller image $BADGE_ADDR 2
```

#### Check stored images
```bash
# Query what images are stored on the badge
badge-controller check $BADGE_ADDR
```

This gives a response like this

```txt
Checking stored images...
Response: 0b535459504531325834384e00000000
Decoded:
          STYPE12X48N
```

#### Interactive mode
```bash
# Start interactive session for experimentation
badge-controller interactive $BADGE_ADDR

# In interactive mode, use commands like:
#   brightness 128
#   animation 1
#   speed 50
#   image 1
#   check
#   quit
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
