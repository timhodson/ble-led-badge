#!/usr/bin/env python3
"""
Test script for uploading a custom image to the LED badge.

Creates a 12x48 pixel sunglasses image and uploads it to the badge.

Usage:
    python test_image_upload.py <badge_address>

Example:
    python test_image_upload.py AA:BB:CC:DD:EE:FF
"""

import asyncio
import sys

# Add parent directory to path for imports
sys.path.insert(0, '..')

from badge_controller import Badge, ScrollMode


def create_sunglasses_bitmap():
    """
    Create a 12x48 pixel sunglasses image.

    Returns the raw bitmap data in the badge's expected format:
    - 8 segments of 6 columns each (48 total columns)
    - 9 bytes per segment
    - Total: 72 bytes
    """

    # Define the sunglasses as a 12-row × 48-column grid
    # 1 = pixel on, 0 = pixel off
    # Each string is one row, left to right
    image = [
        #        1111111111222222222233333333334444444
        #23456789012345678901234567890123456789012345678
        "000000000000000000000000000000000000000000000000",  # Row 0
        "000000000000000000000000000000000000000000000000",  # Row 1
        "000111111111000000000000000000001111111110000000",  # Row 2
        "001111111111100000000000000000011111111111000000",  # Row 3
        "011111111111110000111111110000111111111111100000",  # Row 4
        "011111111111110000111111110000111111111111100000",  # Row 5
        "011111111111110000111111110000111111111111100000",  # Row 6
        "011111111111110000111111110000111111111111100000",  # Row 7
        "001111111111100000011111100000011111111111000000",  # Row 8
        "000111111111000000000000000000001111111110000000",  # Row 9
        "000000000000000000000000000000000000000000000000",  # Row 10
        "000000000000000000000000000000000000000000000000",  # Row 11
    ]

    # Convert to a 2D array of booleans for easier manipulation
    pixels = []
    for row_str in image:
        row = [c == '1' for c in row_str]
        # Ensure exactly 48 columns
        while len(row) < 48:
            row.append(False)
        pixels.append(row[:48])

    # Convert to byte format
    # The badge uses the same format as the font: 9 bytes per 6-column segment
    # Byte layout per segment:
    #   B0: col0 rows 0-7 (bit 7 = row 0)
    #   B1: col0 rows 8-11 (bits 7-4) | col1 rows 8-11 (bits 3-0)
    #   B2: col1 rows 0-7
    #   B3: col2 rows 0-7
    #   B4: col2 rows 8-11 (bits 7-4) | col3 rows 8-11 (bits 3-0)
    #   B5: col3 rows 0-7
    #   B6: col4 rows 0-7
    #   B7: col4 rows 8-11 (bits 7-4) | col5 rows 8-11 (bits 3-0)
    #   B8: col5 rows 0-7

    def encode_segment(pixels, start_col):
        """Encode 6 columns starting at start_col into 9 bytes."""
        segment = [0] * 9

        for local_col in range(6):
            col = start_col + local_col

            # Rows 0-7: one byte per column
            byte_val = 0
            for row in range(8):
                if pixels[row][col]:
                    byte_val |= (1 << (7 - row))

            # Map local column to byte index for rows 0-7
            byte_map = [0, 2, 3, 5, 6, 8]
            segment[byte_map[local_col]] = byte_val

            # Rows 8-11: nibble-packed into shared bytes
            nibble_val = 0
            for row in range(8, 12):
                if pixels[row][col]:
                    nibble_val |= (1 << (11 - row))  # bits 3-0 for rows 8-11

            # Map local column to nibble byte and position
            # Cols 0,1 share byte 1; cols 2,3 share byte 4; cols 4,5 share byte 7
            nibble_byte_map = [1, 1, 4, 4, 7, 7]
            byte_idx = nibble_byte_map[local_col]

            if local_col % 2 == 0:
                # Even columns: upper nibble (bits 7-4)
                segment[byte_idx] |= (nibble_val << 4)
            else:
                # Odd columns: lower nibble (bits 3-0)
                segment[byte_idx] |= nibble_val

        return segment

    # Encode all 8 segments (48 columns / 6 = 8 segments)
    all_bytes = []
    for seg_idx in range(8):
        start_col = seg_idx * 6
        segment_bytes = encode_segment(pixels, start_col)
        all_bytes.extend(segment_bytes)

    return bytes(all_bytes)


def print_bitmap_preview(bitmap_data):
    """Print a text preview of the bitmap data."""
    print("\nBitmap preview (48x12):")
    print("-" * 50)

    # Decode the bytes back to pixels for display
    def get_pixel(data, segment, col, row):
        """Get pixel value from encoded segment data."""
        base = segment * 9
        local_col = col

        if row < 8:
            byte_map = [0, 2, 3, 5, 6, 8]
            byte_idx = base + byte_map[local_col]
            bit = 7 - row
            return (data[byte_idx] >> bit) & 1
        else:
            nibble_byte_map = [1, 1, 4, 4, 7, 7]
            byte_idx = base + nibble_byte_map[local_col]
            if local_col % 2 == 0:
                bit = 7 - (row - 8)
            else:
                bit = 3 - (row - 8)
            return (data[byte_idx] >> bit) & 1

    for row in range(12):
        line = ""
        for segment in range(8):
            for col in range(6):
                if get_pixel(bitmap_data, segment, col, row):
                    line += "█"
                else:
                    line += "."
        print(f"Row {row:2d}: {line}")

    print("-" * 50)
    print(f"Total bytes: {len(bitmap_data)}")
    print(f"Hex: {bitmap_data.hex()}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_image_upload.py <badge_address>")
        print("       python test_image_upload.py --preview   (preview only, no upload)")
        print()
        print("Example: python test_image_upload.py AA:BB:CC:DD:EE:FF")
        sys.exit(1)

    # Create the sunglasses bitmap
    print("Creating sunglasses bitmap...")
    bitmap_data = create_sunglasses_bitmap()
    print_bitmap_preview(bitmap_data)

    # Check for preview-only mode
    if sys.argv[1] == "--preview":
        print("\nPreview mode - no upload performed.")
        return

    address = sys.argv[1]

    # Upload to badge
    print(f"\nConnecting to badge at {address}...")

    async with Badge(address) as badge:
        print("Connected!")

        # Upload the image
        print("Uploading image...")
        success = await badge.upload_image(bitmap_data)

        if success:
            print("Upload successful!")

            # Set display to static mode so it doesn't scroll
            print("Setting static display mode...")
            await badge.set_scroll_mode(ScrollMode.STATIC)
            await badge.set_brightness(128)

            print("Done! The sunglasses should now be displayed on your badge.")
        else:
            print("Upload may have failed (no acknowledgment received).")
            print("The image might still be displayed - check your badge.")

    print("\nDisconnected.")


if __name__ == "__main__":
    asyncio.run(main())
