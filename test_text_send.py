#!/usr/bin/env python3
"""
Test the updated text sending protocol.
"""
import asyncio
import sys

sys.path.insert(0, '.')
from badge_controller.badge import Badge
from badge_controller.commands import ScrollMode

ADDRESS = sys.argv[1] if len(sys.argv) > 1 else "FE5DCE05-1120-2974-BCBF-7AE2F6A509DF"


async def main():
    print(f"Connecting to {ADDRESS}...")

    async with Badge(ADDRESS) as badge:
        print(f"Connected!")

        # Test sending text - use "Magician" which we have exact trace data for
        text = "Magician"
        print(f"\nSending text: '{text}'")

        success = await badge.send_text(
            text,
            scroll_mode=ScrollMode.STATIC,
            brightness=50,
            speed=50
        )

        if success:
            print("Text sent successfully!")
        else:
            print("Failed to send text")

        print("\n>>> Check the badge display! <<<")
        await asyncio.sleep(5)

        # # Try scrolling text - use "Badger" which we also have trace data for
        # text2 = "Badger"
        # print(f"\nSending scrolling text: '{text2}'")

        # await badge.send_text(
        #     text2,
        #     scroll_mode=ScrollMode.LEFT,
        #     brightness=50,
        #     speed=50
        # )

        # print(">>> Check the badge display! <<<")
        # await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
