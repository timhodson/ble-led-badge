# OSC Server for BLE LED Badge

An OSC (Open Sound Control) server that provides a network interface for controlling BLE LED badges. This enables integration with creative tools like TouchDesigner, Max/MSP, Processing, Pure Data, and more.

## Installation

The OSC server is part of the main project. Install dependencies using Poetry:

```bash
cd /path/to/ble-led-badge
poetry install
```

## Usage

### Starting the Server

```bash
# Using poetry run
poetry run badge-osc-server

# Or with custom ports
poetry run badge-osc-server --port 9000 --reply-port 9001

# All options
poetry run badge-osc-server --host 0.0.0.0 --port 9000 --reply-host 127.0.0.1 --reply-port 9001 --verbose
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host`, `-H` | `0.0.0.0` | Host to listen on for OSC messages |
| `--port`, `-p` | `9000` | Port to listen on for OSC messages |
| `--reply-host`, `-r` | `127.0.0.1` | Host to send reply messages to |
| `--reply-port`, `-R` | `9001` | Port to send reply messages to |
| `--verbose`, `-v` | - | Enable verbose logging |

## OSC Commands

### Connection Management

| Address | Arguments | Description |
|---------|-----------|-------------|
| `/badge/connect` | `<address>` | Connect to a badge by BLE address (e.g., `AA:BB:CC:DD:EE:FF`) |
| `/badge/disconnect` | - | Disconnect from current badge |
| `/badge/status` | - | Request connection status |

### Content Commands

| Address | Arguments | Description |
|---------|-----------|-------------|
| `/badge/text` | `<string>` | Send text to the badge display |
| `/badge/image` | `<byte0> <byte1> ...` | Upload raw image bytes (9 bytes per segment) |
| `/badge/image/json` | `<json_string>` | Upload image from JSON (font-editor export format) |

### Display Settings

| Address | Arguments | Description |
|---------|-----------|-------------|
| `/badge/brightness` | `<0-255>` | Set brightness level |
| `/badge/speed` | `<0-255>` | Set scroll speed |
| `/badge/scroll` | `<mode>` | Set scroll mode: `static`, `left`, `right`, `up`, `down`, `snow` |

### Power and Animation

| Address | Arguments | Description |
|---------|-----------|-------------|
| `/badge/on` | - | Turn display on |
| `/badge/off` | - | Turn display off |
| `/badge/animation` | `<1-8>` | Play built-in animation |

## Reply Messages

The server sends reply messages to the configured reply host/port:

| Address | Arguments | Description |
|---------|-----------|-------------|
| `/badge/connected` | `<address>` | Successfully connected to badge |
| `/badge/disconnected` | `"OK"` | Successfully disconnected |
| `/badge/status` | `<status>` `[address]` | Connection status |
| `/badge/error` | `<message>` | Error message |
| `/badge/notification` | `<text>` | Notification from badge |
| `/badge/text/ok` | `<text>` | Text sent successfully |
| `/badge/image/ok` | `<bytes>` | Image uploaded successfully |
| `/badge/brightness/ok` | `<value>` | Brightness set successfully |
| `/badge/speed/ok` | `<value>` | Speed set successfully |
| `/badge/scroll/ok` | `<mode>` | Scroll mode set successfully |
| `/badge/on/ok` | `"OK"` | Display turned on |
| `/badge/off/ok` | `"OK"` | Display turned off |
| `/badge/animation/ok` | `<id>` | Animation started |

## Examples

### Python (python-osc)

```python
from pythonosc import udp_client

client = udp_client.SimpleUDPClient("127.0.0.1", 9000)

# Connect to badge
client.send_message("/badge/connect", "AA:BB:CC:DD:EE:FF")

# Send text
client.send_message("/badge/text", "Hello World!")

# Set brightness
client.send_message("/badge/brightness", 200)

# Set scroll mode
client.send_message("/badge/scroll", "left")
```

### TouchDesigner

Use a `OSC Out` CHOP or DAT to send messages:

```
Address: /badge/text
Arguments: "Hello from TD!"
```

### Max/MSP

```
[udpsend 127.0.0.1 9000]
    |
[prepend /badge/text]
    |
[message "Hello from Max!"]
```

### Processing

```java
import oscP5.*;
import netP5.*;

OscP5 oscP5;
NetAddress badgeServer;

void setup() {
  oscP5 = new OscP5(this, 9001);  // Listen for replies
  badgeServer = new NetAddress("127.0.0.1", 9000);
}

void sendText(String text) {
  OscMessage msg = new OscMessage("/badge/text");
  msg.add(text);
  oscP5.send(msg, badgeServer);
}
```

## Image Data Format

The `/badge/image/json` command accepts JSON in the format exported by the font-editor:

```json
{
  "width": 48,
  "height": 12,
  "segments": 8,
  "bytes": [0, 1, 2, 3, ...]
}
```

Each segment is 9 bytes, encoding a 6x12 pixel block. See the main project documentation for details on the byte encoding format.

## Architecture

The OSC server maintains a persistent Bluetooth connection to the badge, allowing rapid command execution without reconnection overhead. This makes it suitable for real-time applications.

```
┌─────────────────┐     OSC      ┌─────────────────┐    BLE     ┌─────────┐
│  Creative Tool  │ ──────────▶  │   OSC Server    │ ─────────▶ │  Badge  │
│  (TD, Max, etc) │ ◀────────── │  (this script)  │ ◀───────── │         │
└─────────────────┘   Replies    └─────────────────┘  Notify    └─────────┘
```

## Future Enhancements

- Multi-badge support (connect to multiple badges simultaneously)
- HTTP/WebSocket interface
- MIDI input support
- Auto-reconnection on disconnect
