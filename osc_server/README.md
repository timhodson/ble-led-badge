# OSC Server for BLE LED Badge

An OSC (Open Sound Control) server that provides a network interface for controlling BLE LED badges. This enables integration with creative tools like TouchDesigner, Max/MSP, Processing, Pure Data, and more.

## Installation

### From source (development)

The OSC server is part of the main project. Install dependencies using Poetry:

```bash
cd /path/to/ble-led-badge
poetry install
```

### Pre-built binary (Raspberry Pi / macOS)

Download the latest binary for your platform from the [GitHub Releases](../../releases) page:

- `badge-osc-server-linux-arm64` — Raspberry Pi / Linux ARM64
- `badge-osc-server-macos-arm64` — macOS Apple Silicon

```bash
chmod +x badge-osc-server-linux-arm64
./badge-osc-server-linux-arm64 --help
```

No Python, pip, or Poetry required when using the pre-built binary.

## CLI Commands

The tool uses subcommands. Running without a subcommand defaults to `run`.

```bash
badge-osc-server <command> [options]
```

| Command | Description |
|---------|-------------|
| `run` | Start the OSC server (default) |
| `scan` | Scan for nearby BLE LED badges |
| `install` | Install as a systemd service (Linux, requires root) |
| `uninstall` | Remove the systemd service (Linux, requires root) |
| `status` | Show systemd service status (Linux) |

### Scanning for badges

Find the BLE address of nearby badges before connecting:

```bash
# Scan for LED badges (filtered by service UUID and name patterns)
badge-osc-server scan

# Scan for all BLE devices
badge-osc-server scan --all

# Custom timeout (default 10 seconds)
badge-osc-server scan --timeout 20
```

Example output:

```
Scanning for LED badges (10.0s)...

Found 1 badge(s):

  1. LSLED
     Address: AA:BB:CC:DD:EE:FF
```

### Starting the server

```bash
# Start with defaults
badge-osc-server run

# Or simply (run is the default subcommand)
badge-osc-server

# With custom ports
badge-osc-server run --port 9000 --reply-port 9001

# All options
badge-osc-server run --host 0.0.0.0 --port 9000 --reply-host 127.0.0.1 --reply-port 9001 --verbose
```

**`run` options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--host`, `-H` | `0.0.0.0` | Host to listen on for OSC messages |
| `--port`, `-p` | `9000` | Port to listen on for OSC messages |
| `--reply-host`, `-r` | `127.0.0.1` | Host to send reply messages to |
| `--reply-port`, `-R` | `9001` | Port to send reply messages to |
| `--verbose`, `-v` | - | Enable verbose logging |

### Installing as a systemd service (Raspberry Pi)

Run the pre-built binary on a Pi to install it as a service that starts on boot:

```bash
# Install and start the service
sudo ./badge-osc-server install

# With custom options
sudo ./badge-osc-server install --port 8000 --badge-address AA:BB:CC:DD:EE:FF

# Check service status
sudo badge-osc-server status

# View logs
journalctl -u badge-osc-server -f

# Remove the service
sudo badge-osc-server uninstall
```

**`install` options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--host`, `-H` | `0.0.0.0` | Host the service listens on |
| `--port`, `-p` | `9000` | Port the service listens on |
| `--reply-host`, `-r` | `127.0.0.1` | Host for reply messages |
| `--reply-port`, `-R` | `9001` | Port for reply messages |
| `--badge-address`, `-b` | - | Badge BLE address (set as `BADGE_ADDRESS` env var in service) |

The installer copies the binary to `/usr/local/bin/badge-osc-server` and creates a systemd unit at `/etc/systemd/system/badge-osc-server.service`.

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
