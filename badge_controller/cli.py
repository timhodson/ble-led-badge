"""
Command-line interface for BLE LED Badge controller.

Usage:
    badge-controller scan
    badge-controller brightness <address> <level>
    badge-controller animation <address> <id>
    badge-controller check <address>
"""

import argparse
import asyncio
import sys

from .badge import Badge, scan_for_badges


async def cmd_scan(args: argparse.Namespace) -> int:
    """Scan for nearby BLE devices."""
    print(f"Scanning for BLE devices ({args.timeout}s)...")
    devices = await scan_for_badges(timeout=args.timeout)

    if not devices:
        print("No devices found.")
        return 1

    print(f"\nFound {len(devices)} device(s):\n")
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


async def cmd_interactive(args: argparse.Namespace) -> int:
    """Interactive mode for experimentation."""
    print(f"Connecting to {args.address}...")
    async with Badge(args.address) as badge:
        print("Connected! Interactive mode.")
        print("Commands: brightness <0-255>, animation <id>, speed <0-255>, image <id>, check, quit")
        print()

        while True:
            try:
                line = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not line:
                continue

            parts = line.split()
            cmd = parts[0]

            try:
                if cmd in ("quit", "exit", "q"):
                    break
                elif cmd == "brightness" and len(parts) == 2:
                    await badge.set_brightness(int(parts[1]))
                    print("OK")
                elif cmd == "animation" and len(parts) == 2:
                    await badge.play_animation(int(parts[1]))
                    print("OK")
                elif cmd == "speed" and len(parts) == 2:
                    await badge.set_speed(int(parts[1]))
                    print("OK")
                elif cmd == "image" and len(parts) == 2:
                    await badge.show_image(int(parts[1]))
                    print("OK")
                elif cmd == "check":
                    response = await badge.check_images()
                    print(f"Response: {response.hex() if response else 'None'}")
                else:
                    print("Unknown command. Try: brightness, animation, speed, image, check, quit")
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
    scan_parser = subparsers.add_parser("scan", help="Scan for nearby BLE devices")
    scan_parser.add_argument("-t", "--timeout", type=float, default=10.0,
                             help="Scan timeout in seconds (default: 10)")

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
