"""
Command-line interface for BLE LED Badge controller.

Usage:
    badge-controller scan
    badge-controller text <address> <text> [options]
    badge-controller brightness <address> <level>
    badge-controller animation <address> <id>
    badge-controller check <address>
"""

import argparse
import asyncio
import sys

# Enable command history for interactive mode (up/down arrows)
try:
    import readline  # noqa: F401 - import enables history for input()
except ImportError:
    pass  # readline not available on some platforms

from .badge import Badge, scan_for_badges
from .commands import ScrollMode


async def cmd_scan(args: argparse.Namespace) -> int:
    """Scan for nearby BLE devices."""
    filter_badges = not args.all
    scan_type = "all BLE devices" if args.all else "LED badges"
    print(f"Scanning for {scan_type} ({args.timeout}s)...")

    devices = await scan_for_badges(timeout=args.timeout, filter_badges=filter_badges)

    if not devices:
        if filter_badges:
            print("No badges found. Try --all to see all BLE devices.")
        else:
            print("No devices found.")
        return 1

    device_type = "device" if args.all else "badge"
    print(f"\nFound {len(devices)} {device_type}(s):\n")
    for i, device in enumerate(devices, 1):
        name = device.name or "(unnamed)"
        print(f"  {i}. {name}")
        print(f"     Address: {device.address}")
        print()

    return 0


async def cmd_brightness(args: argparse.Namespace) -> int:
    """Set badge brightness."""
    print(f"Connecting to {args.address}...")
    async with Badge(args.address) as badge:
        print(f"Setting brightness to {args.level}...")
        await badge.set_brightness(args.level)
        print("Done.")
    return 0


async def cmd_animation(args: argparse.Namespace) -> int:
    """Play an animation."""
    print(f"Connecting to {args.address}...")
    async with Badge(args.address) as badge:
        print(f"Playing animation {args.id}...")
        await badge.play_animation(args.id)
        print("Done.")
    return 0


async def cmd_speed(args: argparse.Namespace) -> int:
    """Set transition speed."""
    print(f"Connecting to {args.address}...")
    async with Badge(args.address) as badge:
        print(f"Setting speed to {args.level}...")
        await badge.set_speed(args.level)
        print("Done.")
    return 0


async def cmd_image(args: argparse.Namespace) -> int:
    """Show a stored image."""
    print(f"Connecting to {args.address}...")
    async with Badge(args.address) as badge:
        print(f"Showing image {args.id}...")
        await badge.show_image(args.id)
        print("Done.")
    return 0


async def cmd_check(args: argparse.Namespace) -> int:
    """Check stored images on badge."""
    print(f"Connecting to {args.address}...")
    async with Badge(args.address) as badge:
        print("Checking stored images...")
        response = await badge.check_images()
        if response:
            print(f"Response: {response.hex()}")
            # Try to decode as ASCII where possible
            try:
                decoded = response.rstrip(b'\x00').decode('ascii', errors='replace')
                print(f"Decoded:  {decoded}")
            except Exception:
                pass
        else:
            print("No response received.")
    return 0


async def cmd_text(args: argparse.Namespace) -> int:
    """Send text to the badge."""
    print(f"Connecting to {args.address}...")
    async with Badge(args.address) as badge:
        print(f"Sending text: {args.text}")
        
        # Parse scroll mode
        scroll_mode = ScrollMode.LEFT  # Default
        if args.scroll:
            scroll_lower = args.scroll.lower()
            if scroll_lower == "static" or scroll_lower == "none":
                scroll_mode = ScrollMode.STATIC
            elif scroll_lower == "left":
                scroll_mode = ScrollMode.LEFT
            elif scroll_lower == "right":
                scroll_mode = ScrollMode.RIGHT
            else:
                print(f"Warning: Unknown scroll mode '{args.scroll}', using LEFT")
        
        success = await badge.send_text(
            args.text,
            scroll_mode=scroll_mode,
            brightness=args.brightness,
            speed=args.speed
        )
        
        if success:
            print("Text sent successfully!")
        else:
            print("Failed to send text.")
            return 1
    
    return 0


async def cmd_interactive(args: argparse.Namespace) -> int:
    """Interactive mode for experimentation."""
    print(f"Connecting to {args.address}...")
    async with Badge(args.address) as badge:
        print("Connected! Interactive mode.")
        print("Commands:")
        print("  text <message>      - Send text to display")
        print("  scroll <mode>       - Set scroll mode (static, left, right, up, down, snow)")
        print("  brightness <0-255>  - Set brightness")
        print("  animation <id>      - Play animation")
        print("  speed <0-255>       - Set scroll speed")
        print("  image <id>          - Show stored image")
        print("  check               - Check stored images")
        print("  status              - Show current settings")
        print("  quit                - Exit")
        print()
        print("Tip: Chain commands with ; (e.g., scroll static; brightness 200; text Hello)")
        print()

        # Current settings
        current_scroll = ScrollMode.LEFT
        current_brightness = 128
        current_speed = 50

        scroll_modes = {
            'static': ScrollMode.STATIC,
            'left': ScrollMode.LEFT,
            'right': ScrollMode.RIGHT,
            'up': ScrollMode.UP,
            'down': ScrollMode.DOWN,
            'snow': ScrollMode.SNOW,
        }

        async def run_command(cmd_line):
            """Execute a single command. Returns False to quit, True to continue."""
            nonlocal current_scroll, current_brightness, current_speed

            cmd_line = cmd_line.strip()
            if not cmd_line:
                return True

            parts = cmd_line.split()
            cmd = parts[0].lower()

            if cmd in ("quit", "exit", "q"):
                return False
            elif cmd == "text" and len(parts) >= 2:
                # Join remaining parts to preserve spaces in text
                text_content = cmd_line[len(parts[0]):].strip()
                await badge.send_text(
                    text_content,
                    scroll_mode=current_scroll,
                    brightness=current_brightness,
                    speed=current_speed
                )
                print(f"OK - sent: {text_content}")
            elif cmd == "scroll" and len(parts) == 2:
                mode_name = parts[1].lower()
                if mode_name in scroll_modes:
                    current_scroll = scroll_modes[mode_name]
                    await badge.set_scroll_mode(current_scroll)
                    print(f"OK - scroll mode: {mode_name}")
                else:
                    print(f"Unknown mode. Try: {', '.join(scroll_modes.keys())}")
            elif cmd == "brightness" and len(parts) == 2:
                current_brightness = int(parts[1])
                await badge.set_brightness(current_brightness)
                print("OK")
            elif cmd == "animation" and len(parts) == 2:
                await badge.play_animation(int(parts[1]))
                print("OK")
            elif cmd == "speed" and len(parts) == 2:
                current_speed = int(parts[1])
                await badge.set_speed(current_speed)
                print("OK")
            elif cmd == "image" and len(parts) == 2:
                await badge.show_image(int(parts[1]))
                print("OK")
            elif cmd == "check":
                response = await badge.check_images()
                print(f"Response: {response.hex() if response else 'None'}")
            elif cmd == "status":
                mode_name = [k for k, v in scroll_modes.items() if v == current_scroll][0]
                print(f"Scroll: {mode_name}, Brightness: {current_brightness}, Speed: {current_speed}")
            else:
                print("Unknown command. Try: text, scroll, brightness, animation, speed, image, check, quit")
            return True

        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not line:
                continue

            # Split by semicolon to allow multiple commands
            commands = line.split(';')

            try:
                should_continue = True
                for cmd_line in commands:
                    should_continue = await run_command(cmd_line)
                    if not should_continue:
                        break
                if not should_continue:
                    break
            except Exception as e:
                print(f"Error: {e}")

    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="badge-controller",
        description="Control BLE LED badges"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan for nearby LED badges")
    scan_parser.add_argument("-t", "--timeout", type=float, default=10.0,
                             help="Scan timeout in seconds (default: 10)")
    scan_parser.add_argument("-a", "--all", action="store_true",
                             help="Show all BLE devices, not just badges")

    # Brightness command
    bright_parser = subparsers.add_parser("brightness", help="Set badge brightness")
    bright_parser.add_argument("address", help="Badge BLE address")
    bright_parser.add_argument("level", type=int, help="Brightness level (0-255)")

    # Animation command
    anim_parser = subparsers.add_parser("animation", help="Play an animation")
    anim_parser.add_argument("address", help="Badge BLE address")
    anim_parser.add_argument("id", type=int, help="Animation ID")

    # Speed command
    speed_parser = subparsers.add_parser("speed", help="Set transition speed")
    speed_parser.add_argument("address", help="Badge BLE address")
    speed_parser.add_argument("level", type=int, help="Speed level (0-255)")

    # Image command
    image_parser = subparsers.add_parser("image", help="Show a stored image")
    image_parser.add_argument("address", help="Badge BLE address")
    image_parser.add_argument("id", type=int, help="Image ID")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check stored images")
    check_parser.add_argument("address", help="Badge BLE address")

    # Text command
    text_parser = subparsers.add_parser("text", help="Send text to the badge")
    text_parser.add_argument("address", help="Badge BLE address")
    text_parser.add_argument("text", help="Text to display")
    text_parser.add_argument("-s", "--scroll", default="left",
                            help="Scroll mode: static, left, right (default: left)")
    text_parser.add_argument("-b", "--brightness", type=int, default=128,
                            help="Brightness level 0-255 (default: 128)")
    text_parser.add_argument("--speed", type=int, default=50,
                            help="Scroll speed 0-255 (default: 50)")

    # Interactive command
    int_parser = subparsers.add_parser("interactive", help="Interactive experimentation mode")
    int_parser.add_argument("address", help="Badge BLE address")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to async handler
    handlers = {
        "scan": cmd_scan,
        "brightness": cmd_brightness,
        "animation": cmd_animation,
        "speed": cmd_speed,
        "image": cmd_image,
        "check": cmd_check,
        "text": cmd_text,
        "interactive": cmd_interactive,
    }

    handler = handlers.get(args.command)
    if handler:
        return asyncio.run(handler(args))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
