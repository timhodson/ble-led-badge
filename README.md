# BLE LED Badge Controller

A Python library and CLI for controlling Bluetooth Low Energy LED name badges. Supports sending text, controlling brightness, animations, and includes a web-based font editor for creating custom characters.

## Features

- Scan for LED badge devices
- Send text with various scroll modes (static, left, right, up, down, snow)
- Control brightness and scroll speed
- Play built-in animations
- Interactive mode for real-time experimentation
- Web-based font editor with multi-width character support
- Python API for integration into other applications

## Installation

```bash
# Install with poetry
poetry install

# Or install from local path
pip install /path/to/ble-led-badge

# Or install in development mode
pip install -e /path/to/ble-led-badge
```

## Dependencies

- **Python 3.8+**
- **Bleak** - Cross-platform BLE library
- **pycryptodome** - AES encryption for badge protocol

## Quick Start

1. **Find your badge:**
   ```bash
   badge-controller scan
   ```

2. **Set your badge address:**
   ```bash
   export BADGE_ADDR="AA:BB:CC:DD:EE:FF"
   ```

3. **Send text:**
   ```bash
   badge-controller text $BADGE_ADDR "Hello World"
   ```

## CLI Commands

### Scan for devices

```bash
# Scan for LED badges (filtered by service UUID and common name patterns)
badge-controller scan

# Scan for all BLE devices (unfiltered)
badge-controller scan --all

# Custom timeout (default 10 seconds)
badge-controller scan --timeout 20
```

### Send text

```bash
# Basic text (scrolls left by default)
badge-controller text $BADGE_ADDR "Hello World"

# Static text (no scrolling)
badge-controller text $BADGE_ADDR "Hi!" --scroll static

# Scroll right
badge-controller text $BADGE_ADDR "Welcome" --scroll right

# With custom brightness (0-255)
badge-controller text $BADGE_ADDR "Bright!" --brightness 255

# With custom speed (0-255, higher = faster)
badge-controller text $BADGE_ADDR "Fast scroll" --speed 100

# Combine options
badge-controller text $BADGE_ADDR "Custom" --scroll left --brightness 200 --speed 75
```

### Set brightness

```bash
badge-controller brightness $BADGE_ADDR 128
badge-controller brightness $BADGE_ADDR 255  # Maximum
```

Note: Brightness is not saved between badge power cycles.

### Set scroll speed

```bash
badge-controller speed $BADGE_ADDR 50
badge-controller speed $BADGE_ADDR 100  # Faster
```

Note: Speed is not saved between badge power cycles.

### Play animations

```bash
badge-controller animation $BADGE_ADDR 1
```

Available animations (1-8):
1. Falling leaves turn into flashing word "love"
2. Four animated hearts
3. Cheers beer tankards
4. The word "COME" builds with flashing face
5. Two radiating and flashing hearts
6. Animated dollar signs
7. Two fish kissing
8. Animal face with radiating thought waves

### Show stored images

```bash
badge-controller image $BADGE_ADDR 1
```

### Check stored images

```bash
badge-controller check $BADGE_ADDR
```

## Interactive Mode

Interactive mode keeps a persistent BLE connection open, allowing you to send multiple commands without reconnecting each time.

```bash
badge-controller interactive $BADGE_ADDR
```

### Available Commands

| Command | Description |
|---------|-------------|
| `text <message>` | Send text to display |
| `scroll <mode>` | Set scroll mode: static, left, right, up, down, snow |
| `brightness <0-255>` | Set brightness level |
| `speed <0-255>` | Set scroll speed |
| `animation <id>` | Play animation (1-8) |
| `image <id>` | Show stored image |
| `check` | Check stored images |
| `status` | Show current settings |
| `quit` | Exit interactive mode |

### Features

- **Command chaining:** Separate multiple commands with `;`
  ```
  > scroll static; brightness 200; text Hello World
  ```
- **Command history:** Use up/down arrows to recall previous commands
- **Settings persistence:** Scroll mode, brightness, and speed are remembered for subsequent text commands

### Example Session

```
$ badge-controller interactive AA:BB:CC:DD:EE:FF
Connected! Interactive mode.
Commands:
  text <message>      - Send text to display
  scroll <mode>       - Set scroll mode (static, left, right, up, down, snow)
  brightness <0-255>  - Set brightness
  ...

> brightness 200
OK
> scroll left
OK - scroll mode: left
> text Hello World
OK - sent: Hello World
> speed 100; text Fast scrolling!
OK
OK - sent: Fast scrolling!
> status
Scroll: left, Brightness: 200, Speed: 100
> quit
```

## Python API

The badge controller can be imported into other Python applications:

```python
from badge_controller import Badge, ScrollMode, TextRenderer, scan_for_badges

# Scan for badges
badges = await scan_for_badges()
for badge in badges:
    print(f"{badge.name}: {badge.address}")

# Control a badge
async with Badge("AA:BB:CC:DD:EE:FF") as badge:
    await badge.set_brightness(128)
    await badge.send_text("Hello", scroll_mode=ScrollMode.LEFT)
    await badge.play_animation(1)

# Extend the font with custom characters
TextRenderer.FONT['©'] = [0x1c, 0x22, 0x49, 0x45, 0x49, 0x22, 0x1c, 0x00, 0x00]

# Load custom font from JSON
import json
with open('my_font.json') as f:
    TextRenderer.FONT.update(json.load(f))
```

### Available Exports

- `Badge` - Main controller class
- `scan_for_badges()` - Scan for nearby badges
- `find_badge_by_name()` - Find badge by name pattern
- `TextRenderer` - Text-to-bitmap rendering with font data
- `ScrollMode` - Enum for scroll modes (STATIC, LEFT, RIGHT, UP, DOWN, SNOW)
- `Animation` - Enum for animations
- `Command` - Low-level command builders

## Font Editor

A web-based font editor is included for creating and editing character bitmaps.

### Running the Editor

Open `font-editor/index.html` in a web browser. No server required.

### Features

- **Visual pixel editor** - Click to toggle pixels on/off
- **Character grid** - Quick selection of all characters in the font
- **Add/delete characters** - Add new characters including emojis
- **Multi-width characters** - Create wide characters spanning multiple segments (e.g., for emojis)
- **Live preview** - See how text will appear on the badge
- **JSON import/export** - Save and load font files

### Multi-Width Characters

Characters can span multiple standard widths (6 pixels each). This is useful for emojis or wide symbols:

1. Enter a character and set the desired width
2. Click "Add Character"
3. The pixel grid expands to show multiple segments
4. Design your character across all segments
5. Save the JSON to persist your changes

The font data format:
- Single-width: `[b0, b1, ..., b8]` (9 bytes)
- Multi-width: `[[b0...b8], [b0...b8], ...]` (array of 9-byte segments)

### Screenshots

![Font Editor - Character Grid and Pixel Editor](images/Screenshot%202026-01-21%20at%2019.08.21.png)
*Character selection grid with multi-width emoji (3 segments), and the pixel editor showing the character design*

![Font Editor - Preview and JSON](images/Screenshot%202026-01-21%20at%2019.08.43.png)
*Live preview of text, orientation display, and JSON data editor for saving/loading fonts*

## Project Structure

```
ble-led-badge/
├── badge_controller/        # Main Python package
│   ├── __init__.py         # Package exports
│   ├── badge.py            # Badge controller class
│   ├── cli.py              # Command-line interface
│   ├── commands.py         # Command packet builders
│   ├── encryption.py       # AES-ECB encryption
│   ├── protocol.py         # BLE UUIDs and constants
│   └── text_renderer.py    # Text-to-bitmap conversion
├── font-editor/            # Web-based font editor
│   ├── index.html          # Font editor application
│   └── font.json           # Font data file
├── examples/               # Example scripts
├── experiments/            # Experimental code
├── initial_analysis/       # Reverse engineering notes
├── images/                 # Screenshots and images
├── pyproject.toml          # Poetry configuration
└── README.md               # This file
```

## How It Works

1. **Discovery**: Scans for BLE devices advertising the badge service UUID (`0000fee9-0000-1000-8000-00805f9b34fb`) or matching common name patterns
2. **Connection**: Establishes BLE connection using Bleak
3. **Text Rendering**: Converts text to bitmap using the font (9 bytes per character segment)
4. **Encryption**: Commands are AES-ECB encrypted before sending
5. **Communication**: Data sent via GATT characteristics:
   - Command channel (encrypted): `d44bc439-abfd-45a2-b575-925416129600`
   - Image upload (unencrypted): `d44bc439-abfd-45a2-b575-92541612960a`
   - Notifications: `d44bc439-abfd-45a2-b575-925416129601`

## License

MIT
