"""
OSC Server for BLE LED Badge control.

This server maintains persistent connections to badges and exposes
control via OSC messages, enabling integration with creative tools.
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
from typing import Dict, List, Optional

from pythonosc import osc_server
from pythonosc.dispatcher import Dispatcher
from pythonosc.udp_client import SimpleUDPClient

# Add parent directory to path for badge_controller import
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from badge_controller import Badge, ScrollMode
from badge_controller.text_renderer import TextRenderer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


class BadgeOSCServer:
    """
    OSC Server that manages badge connections and forwards OSC commands.

    OSC Address Patterns:
        /badge/connect <address>        - Connect to a badge by BLE address
        /badge/disconnect               - Disconnect from current badge
        /badge/status                   - Request connection status

        /badge/text <string>            - Send text to badge
        /badge/image <bytes...>         - Upload raw image bytes (9 bytes per segment)
        /badge/image/json <json_string> - Upload image from JSON format (font-editor export)

        /badge/brightness <0-255>       - Set brightness level
        /badge/speed <0-255>            - Set scroll speed
        /badge/scroll <mode>            - Set scroll mode (static/left/right/up/down/snow)

        /badge/on                       - Turn display on
        /badge/off                      - Turn display off
        /badge/animation <1-8>          - Play built-in animation

    Response messages are sent back to the client on the configured reply port.
    """

    SCROLL_MODES = {
        "static": ScrollMode.STATIC,
        "left": ScrollMode.LEFT,
        "right": ScrollMode.RIGHT,
        "up": ScrollMode.UP,
        "down": ScrollMode.DOWN,
        "snow": ScrollMode.SNOW,
        # Also support numeric strings
        "1": ScrollMode.STATIC,
        "3": ScrollMode.LEFT,
        "4": ScrollMode.RIGHT,
        "5": ScrollMode.UP,
        "6": ScrollMode.DOWN,
        "7": ScrollMode.SNOW,
    }

    def __init__(
        self,
        listen_host: str = "0.0.0.0",
        listen_port: int = 9000,
        reply_host: str = "127.0.0.1",
        reply_port: int = 9001
    ):
        """
        Initialize the OSC server.

        Args:
            listen_host: Host to listen on for OSC messages
            listen_port: Port to listen on for OSC messages
            reply_host: Host to send reply messages to
            reply_port: Port to send reply messages to
        """
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.reply_host = reply_host
        self.reply_port = reply_port

        self.badge: Optional[Badge] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.reply_client: Optional[SimpleUDPClient] = None
        self._server: Optional[osc_server.ThreadingOSCUDPServer] = None
        self._running = False

        # Current settings (for persistence across commands)
        self.current_brightness = 200
        self.current_speed = 50
        self.current_scroll_mode = ScrollMode.LEFT

    def _setup_dispatcher(self) -> Dispatcher:
        """Set up OSC message dispatcher with all handlers."""
        dispatcher = Dispatcher()

        # Connection management
        dispatcher.map("/badge/connect", self._handle_connect)
        dispatcher.map("/badge/disconnect", self._handle_disconnect)
        dispatcher.map("/badge/status", self._handle_status)

        # Content commands
        dispatcher.map("/badge/text", self._handle_text)
        dispatcher.map("/badge/image", self._handle_image)
        dispatcher.map("/badge/image/json", self._handle_image_json)

        # Display settings
        dispatcher.map("/badge/brightness", self._handle_brightness)
        dispatcher.map("/badge/speed", self._handle_speed)
        dispatcher.map("/badge/scroll", self._handle_scroll)

        # Power and animation
        dispatcher.map("/badge/on", self._handle_on)
        dispatcher.map("/badge/off", self._handle_off)
        dispatcher.map("/badge/animation", self._handle_animation)

        # Catch-all for unknown messages
        dispatcher.set_default_handler(self._handle_unknown)

        return dispatcher

    def _send_reply(self, address: str, *args):
        """Send an OSC reply message to the client."""
        if self.reply_client:
            try:
                self.reply_client.send_message(address, args)
            except Exception as e:
                logger.error(f"Failed to send reply: {e}")

    def _run_async(self, coro):
        """Run an async coroutine from sync context."""
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            try:
                return future.result(timeout=30)
            except Exception as e:
                logger.error(f"Async operation failed: {e}")
                return None
        return None

    # OSC Handlers

    def _handle_connect(self, address: str, *args):
        """Handle /badge/connect <address>"""
        if not args:
            self._send_reply("/badge/error", "Missing badge address")
            return

        badge_address = str(args[0])
        logger.info(f"Connecting to badge: {badge_address}")

        async def do_connect():
            # Disconnect existing connection if any
            if self.badge and self.badge.is_connected:
                await self.badge.disconnect()

            self.badge = Badge(badge_address)
            await self.badge.connect()

            # Set up notification callback
            def on_notify(data: bytes):
                # Decode and sanitize - remove null bytes and non-printable characters
                text = data.decode('utf-8', errors='ignore')
                # Keep only printable ASCII characters
                text = ''.join(c for c in text if c.isprintable() or c == ' ')
                text = text.strip()
                if text:
                    logger.info(f"Badge notification: {text}")
                    self._send_reply("/badge/notification", text)

            self.badge.on_notification(on_notify)
            return self.badge.is_connected

        try:
            success = self._run_async(do_connect())
            if success:
                logger.info(f"Connected to badge: {badge_address}")
                self._send_reply("/badge/connected", badge_address)
            else:
                logger.error(f"Failed to connect to badge: {badge_address}")
                self._send_reply("/badge/error", f"Failed to connect to {badge_address}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self._send_reply("/badge/error", str(e))

    def _handle_disconnect(self, address: str, *args):
        """Handle /badge/disconnect"""
        logger.info("Disconnecting from badge")

        async def do_disconnect():
            if self.badge:
                await self.badge.disconnect()
                self.badge = None

        try:
            self._run_async(do_disconnect())
            self._send_reply("/badge/disconnected", "OK")
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            self._send_reply("/badge/error", str(e))

    def _handle_status(self, address: str, *args):
        """Handle /badge/status"""
        if self.badge and self.badge.is_connected:
            self._send_reply("/badge/status", "connected", self.badge.address)
        else:
            self._send_reply("/badge/status", "disconnected")

    def _handle_text(self, address: str, *args):
        """Handle /badge/text <string>"""
        if not self.badge or not self.badge.is_connected:
            self._send_reply("/badge/error", "Not connected to badge")
            return

        if not args:
            self._send_reply("/badge/error", "Missing text argument")
            return

        text = str(args[0])
        logger.info(f"Sending text: {text}")

        async def do_send_text():
            success = await self.badge.send_text(
                text,
                scroll_mode=self.current_scroll_mode,
                brightness=self.current_brightness,
                speed=self.current_speed
            )
            return success

        try:
            success = self._run_async(do_send_text())
            if success:
                self._send_reply("/badge/text/ok", text)
            else:
                self._send_reply("/badge/error", "Failed to send text")
        except Exception as e:
            logger.error(f"Send text error: {e}")
            self._send_reply("/badge/error", str(e))

    def _handle_image(self, address: str, *args):
        """Handle /badge/image <bytes...>"""
        if not self.badge or not self.badge.is_connected:
            self._send_reply("/badge/error", "Not connected to badge")
            return

        if not args:
            self._send_reply("/badge/error", "Missing image data")
            return

        # Convert args to bytes (each arg should be an int 0-255)
        try:
            image_bytes = bytes(int(b) for b in args)
        except (ValueError, TypeError) as e:
            self._send_reply("/badge/error", f"Invalid image data: {e}")
            return

        logger.info(f"Uploading image: {len(image_bytes)} bytes")

        async def do_upload():
            success = await self.badge.upload_image(image_bytes)
            if success:
                await self.badge.set_scroll_mode(self.current_scroll_mode)
                await self.badge.set_brightness(self.current_brightness)
                await self.badge.set_speed(self.current_speed)
            return success

        try:
            success = self._run_async(do_upload())
            if success:
                self._send_reply("/badge/image/ok", len(image_bytes))
            else:
                self._send_reply("/badge/error", "Failed to upload image")
        except Exception as e:
            logger.error(f"Upload image error: {e}")
            self._send_reply("/badge/error", str(e))

    def _handle_image_json(self, address: str, *args):
        """Handle /badge/image/json <json_string>

        Accepts JSON in the format exported by the font-editor:
        {"width": 48, "height": 12, "segments": 8, "bytes": [0, 1, 2, ...]}
        """
        if not self.badge or not self.badge.is_connected:
            self._send_reply("/badge/error", "Not connected to badge")
            return

        if not args:
            self._send_reply("/badge/error", "Missing JSON data")
            return

        try:
            data = json.loads(str(args[0]))
            image_bytes = bytes(data.get("bytes", []))
        except (json.JSONDecodeError, TypeError) as e:
            self._send_reply("/badge/error", f"Invalid JSON: {e}")
            return

        if not image_bytes:
            self._send_reply("/badge/error", "No bytes in JSON data")
            return

        logger.info(f"Uploading image from JSON: {len(image_bytes)} bytes")

        async def do_upload():
            success = await self.badge.upload_image(image_bytes)
            if success:
                await self.badge.set_scroll_mode(self.current_scroll_mode)
                await self.badge.set_brightness(self.current_brightness)
                await self.badge.set_speed(self.current_speed)
            return success

        try:
            success = self._run_async(do_upload())
            if success:
                self._send_reply("/badge/image/ok", len(image_bytes))
            else:
                self._send_reply("/badge/error", "Failed to upload image")
        except Exception as e:
            logger.error(f"Upload image error: {e}")
            self._send_reply("/badge/error", str(e))

    def _handle_brightness(self, address: str, *args):
        """Handle /badge/brightness <0-255>"""
        if not args:
            self._send_reply("/badge/error", "Missing brightness value")
            return

        try:
            brightness = max(0, min(255, int(args[0])))
        except (ValueError, TypeError):
            self._send_reply("/badge/error", "Invalid brightness value")
            return

        self.current_brightness = brightness
        logger.info(f"Setting brightness: {brightness}")

        if self.badge and self.badge.is_connected:
            async def do_set():
                await self.badge.set_brightness(brightness)

            try:
                self._run_async(do_set())
                self._send_reply("/badge/brightness/ok", brightness)
            except Exception as e:
                logger.error(f"Set brightness error: {e}")
                self._send_reply("/badge/error", str(e))
        else:
            # Store for later use
            self._send_reply("/badge/brightness/stored", brightness)

    def _handle_speed(self, address: str, *args):
        """Handle /badge/speed <0-255>"""
        if not args:
            self._send_reply("/badge/error", "Missing speed value")
            return

        try:
            speed = max(0, min(255, int(args[0])))
        except (ValueError, TypeError):
            self._send_reply("/badge/error", "Invalid speed value")
            return

        self.current_speed = speed
        logger.info(f"Setting speed: {speed}")

        if self.badge and self.badge.is_connected:
            async def do_set():
                await self.badge.set_speed(speed)

            try:
                self._run_async(do_set())
                self._send_reply("/badge/speed/ok", speed)
            except Exception as e:
                logger.error(f"Set speed error: {e}")
                self._send_reply("/badge/error", str(e))
        else:
            self._send_reply("/badge/speed/stored", speed)

    def _handle_scroll(self, address: str, *args):
        """Handle /badge/scroll <mode>"""
        if not args:
            self._send_reply("/badge/error", "Missing scroll mode")
            return

        mode_str = str(args[0]).lower()

        if mode_str not in self.SCROLL_MODES:
            valid = ", ".join(k for k in self.SCROLL_MODES.keys() if not k.isdigit())
            self._send_reply("/badge/error", f"Invalid scroll mode. Valid: {valid}")
            return

        mode = self.SCROLL_MODES[mode_str]
        self.current_scroll_mode = mode
        logger.info(f"Setting scroll mode: {mode_str} ({mode})")

        if self.badge and self.badge.is_connected:
            async def do_set():
                await self.badge.set_scroll_mode(mode)

            try:
                self._run_async(do_set())
                self._send_reply("/badge/scroll/ok", mode_str)
            except Exception as e:
                logger.error(f"Set scroll mode error: {e}")
                self._send_reply("/badge/error", str(e))
        else:
            self._send_reply("/badge/scroll/stored", mode_str)

    def _handle_on(self, address: str, *args):
        """Handle /badge/on"""
        if not self.badge or not self.badge.is_connected:
            self._send_reply("/badge/error", "Not connected to badge")
            return

        logger.info("Turning display on")

        async def do_on():
            await self.badge.turn_on()

        try:
            self._run_async(do_on())
            self._send_reply("/badge/on/ok", "OK")
        except Exception as e:
            logger.error(f"Turn on error: {e}")
            self._send_reply("/badge/error", str(e))

    def _handle_off(self, address: str, *args):
        """Handle /badge/off"""
        if not self.badge or not self.badge.is_connected:
            self._send_reply("/badge/error", "Not connected to badge")
            return

        logger.info("Turning display off")

        async def do_off():
            await self.badge.turn_off()

        try:
            self._run_async(do_off())
            self._send_reply("/badge/off/ok", "OK")
        except Exception as e:
            logger.error(f"Turn off error: {e}")
            self._send_reply("/badge/error", str(e))

    def _handle_animation(self, address: str, *args):
        """Handle /badge/animation <1-8>"""
        if not self.badge or not self.badge.is_connected:
            self._send_reply("/badge/error", "Not connected to badge")
            return

        if not args:
            self._send_reply("/badge/error", "Missing animation ID")
            return

        try:
            anim_id = int(args[0])
        except (ValueError, TypeError):
            self._send_reply("/badge/error", "Invalid animation ID")
            return

        logger.info(f"Playing animation: {anim_id}")

        async def do_anim():
            await self.badge.play_animation(anim_id)

        try:
            self._run_async(do_anim())
            self._send_reply("/badge/animation/ok", anim_id)
        except Exception as e:
            logger.error(f"Animation error: {e}")
            self._send_reply("/badge/error", str(e))

    def _handle_unknown(self, address: str, *args):
        """Handle unknown OSC addresses."""
        logger.warning(f"Unknown OSC address: {address} {args}")
        self._send_reply("/badge/error", f"Unknown command: {address}")

    def start(self):
        """Start the OSC server."""
        import threading

        logger.info(f"Starting OSC server on {self.listen_host}:{self.listen_port}")
        logger.info(f"Replies will be sent to {self.reply_host}:{self.reply_port}")

        # Set up async event loop for badge operations
        self.loop = asyncio.new_event_loop()

        # Start event loop in background
        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        loop_thread = threading.Thread(target=run_loop, daemon=True)
        loop_thread.start()

        # Set up reply client
        self.reply_client = SimpleUDPClient(self.reply_host, self.reply_port)

        # Set up dispatcher and server
        dispatcher = self._setup_dispatcher()
        self._server = osc_server.ThreadingOSCUDPServer(
            (self.listen_host, self.listen_port),
            dispatcher
        )

        self._running = True
        logger.info("OSC server started. Waiting for commands...")
        logger.info("")
        logger.info("Available commands:")
        logger.info("  /badge/connect <address>     - Connect to badge")
        logger.info("  /badge/disconnect            - Disconnect from badge")
        logger.info("  /badge/status                - Get connection status")
        logger.info("  /badge/text <string>         - Send text")
        logger.info("  /badge/image <bytes...>      - Upload raw image bytes")
        logger.info("  /badge/image/json <json>     - Upload image from JSON")
        logger.info("  /badge/brightness <0-255>    - Set brightness")
        logger.info("  /badge/speed <0-255>         - Set speed")
        logger.info("  /badge/scroll <mode>         - Set scroll mode")
        logger.info("  /badge/on                    - Turn display on")
        logger.info("  /badge/off                   - Turn display off")
        logger.info("  /badge/animation <1-8>       - Play animation")
        logger.info("")
        logger.info("Press Ctrl+C to stop the server.")

        self._send_reply("/badge/server/started", self.listen_port)

        # Run server in a daemon thread so main thread can handle signals
        server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        server_thread.start()

        # Main thread just waits
        try:
            while self._running:
                server_thread.join(timeout=0.5)
                if not server_thread.is_alive():
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """Stop the OSC server and clean up."""
        if not self._running:
            return  # Already stopped

        self._running = False
        logger.info("Stopping OSC server...")

        # Disconnect from badge
        if self.badge and self.badge.is_connected:
            try:
                self._run_async(self.badge.disconnect())
            except Exception:
                pass

        # Stop server
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass
            self._server = None

        # Stop event loop
        if self.loop:
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception:
                pass
            self.loop = None

        logger.info("OSC server stopped")


def main():
    """Main entry point for the OSC server."""
    parser = argparse.ArgumentParser(
        description="OSC Server for BLE LED Badge control"
    )
    parser.add_argument(
        "--host", "-H",
        default="0.0.0.0",
        help="Host to listen on (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=9000,
        help="Port to listen on (default: 9000)"
    )
    parser.add_argument(
        "--reply-host", "-r",
        default="127.0.0.1",
        help="Host to send replies to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--reply-port", "-R",
        type=int,
        default=9001,
        help="Port to send replies to (default: 9001)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    server = BadgeOSCServer(
        listen_host=args.host,
        listen_port=args.port,
        reply_host=args.reply_host,
        reply_port=args.reply_port
    )

    # SIGTERM handler (SIGINT/Ctrl+C is handled by KeyboardInterrupt in start())
    def signal_handler(sig, frame):
        logger.info("Received SIGTERM")
        server.stop()

    signal.signal(signal.SIGTERM, signal_handler)

    server.start()


if __name__ == "__main__":
    main()
