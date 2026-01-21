#!/usr/bin/env python3
"""
Test the updated text sending protocol.
"""
import asyncio
import sys

sys.path.insert(0, '.')
from badge_controller import badge
from badge_controller.badge import Badge
from badge_controller.commands import ScrollMode
from bleak import BleakScanner

ADDRESS = sys.argv[1] if len(sys.argv) > 1 else None


async def find_badge():
    """Scan for the LED badge device."""
    print("Scanning for LED badge...")
    devices = await BleakScanner.discover(timeout=5.0)

    for d in devices:
        name = d.name or ""
        # Look for common badge names
        if "LED" in name.upper() or "BADGE" in name.upper() or "DSD" in name:
            print(f"Found potential badge: {d.name} ({d.address})")
            return d.address

    print("\nAll discovered devices:")
    for d in devices:
        print(f"  {d.name or 'Unknown'}: {d.address}")

    return None


async def main():
    global ADDRESS

    if ADDRESS is None:
        ADDRESS = await find_badge()
        if ADDRESS is None:
            print("\nNo badge found. Please turn on the badge and try again.")
            print("Or specify address: python test_text_send.py <address>")
            return

    print(f"\nConnecting to {ADDRESS}...")

    async with Badge(ADDRESS) as badge:
        print(f"Connected!")

        # send some known working text to clear the display
        print("\nClearing display with 'cleared' message...")
        success = await badge.send_text(
            "cleared",
            scroll_mode=ScrollMode.LEFT,
            brightness=50,
            speed=50
        )

        await asyncio.sleep(5)
        print("\nTest 1: Sending complex text with special characters...")
    
        text = "Ace of ♠️ was your card!"

        success = await badge.send_text(
            text,
            scroll_mode=ScrollMode.LEFT,
            brightness=100,
            speed=50
        )

        if success:
            print("Sent!")
            print("\n>>> Describe what you see: <<<")
            print("- Which column(s)?")
            print("- Which rows (full column? partial? scattered?)")
        else:
            print("Failed to send")
        

if __name__ == "__main__":
    asyncio.run(main())
