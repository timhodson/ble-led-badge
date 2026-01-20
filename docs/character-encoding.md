# LED Badge Character Encoding

This document describes how characters are encoded as bitmap data for the BLE LED badge display.

## Display Dimensions

Each character occupies a **6 column × 12 row** grid of pixels, totaling 72 pixels.

```
     Col 0  Col 1  Col 2  Col 3  Col 4  Col 5
Row 0   ·      ·      ·      ·      ·      ·
Row 1   ·      ·      ·      ·      ·      ·
Row 2   ·      ·      ·      ·      ·      ·
Row 3   ·      ·      ·      ·      ·      ·
Row 4   ·      ·      ·      ·      ·      ·
Row 5   ·      ·      ·      ·      ·      ·
Row 6   ·      ·      ·      ·      ·      ·
Row 7   ·      ·      ·      ·      ·      ·
Row 8   ·      ·      ·      ·      ·      ·
Row 9   ·      ·      ·      ·      ·      ·
Row 10  ·      ·      ·      ·      ·      ·
Row 11  ·      ·      ·      ·      ·      ·
```

## Data Format

Each character is encoded as **9 bytes** (72 bits = 72 pixels).

The bytes use an **interleaved nibble layout** where:
- Rows 0-7 of each column are stored in dedicated bytes (8 bits = 8 rows)
- Rows 8-11 of adjacent column pairs are packed into shared bytes (4 bits per column)

## Byte Layout

| Byte | Content | Bit 7 | Bit 6 | Bit 5 | Bit 4 | Bit 3 | Bit 2 | Bit 1 | Bit 0 |
|------|---------|-------|-------|-------|-------|-------|-------|-------|-------|
| 0 | Col 0, Rows 0-7 | r0 | r1 | r2 | r3 | r4 | r5 | r6 | r7 |
| 1 | Col 0+1, Rows 8-11 | c0r8 | c0r9 | c0r10 | c0r11 | c1r8 | c1r9 | c1r10 | c1r11 |
| 2 | Col 1, Rows 0-7 | r0 | r1 | r2 | r3 | r4 | r5 | r6 | r7 |
| 3 | Col 2, Rows 0-7 | r0 | r1 | r2 | r3 | r4 | r5 | r6 | r7 |
| 4 | Col 2+3, Rows 8-11 | c2r8 | c2r9 | c2r10 | c2r11 | c3r8 | c3r9 | c3r10 | c3r11 |
| 5 | Col 3, Rows 0-7 | r0 | r1 | r2 | r3 | r4 | r5 | r6 | r7 |
| 6 | Col 4, Rows 0-7 | r0 | r1 | r2 | r3 | r4 | r5 | r6 | r7 |
| 7 | Col 4+5, Rows 8-11 | c4r8 | c4r9 | c4r10 | c4r11 | c5r8 | c5r9 | c5r10 | c5r11 |
| 8 | Col 5, Rows 0-7 | r0 | r1 | r2 | r3 | r4 | r5 | r6 | r7 |

### Key Points

- **MSB = Top Row**: Within each byte, bit 7 (MSB) corresponds to the topmost row
- **Column Pairs**: Bytes 1, 4, and 7 contain the bottom 4 rows of two adjacent columns
  - Upper nibble (bits 7-4): even column (0, 2, 4)
  - Lower nibble (bits 3-0): odd column (1, 3, 5)

## Visual Diagram

```
Byte 0                    Byte 2                    Byte 3                    Byte 5                    Byte 6                    Byte 8
Col 0, Rows 0-7           Col 1, Rows 0-7           Col 2, Rows 0-7           Col 3, Rows 0-7           Col 4, Rows 0-7           Col 5, Rows 0-7
┌─────────┐               ┌─────────┐               ┌─────────┐               ┌─────────┐               ┌─────────┐               ┌─────────┐
│ bit7=r0 │               │ bit7=r0 │               │ bit7=r0 │               │ bit7=r0 │               │ bit7=r0 │               │ bit7=r0 │
│ bit6=r1 │               │ bit6=r1 │               │ bit6=r1 │               │ bit6=r1 │               │ bit6=r1 │               │ bit6=r1 │
│ bit5=r2 │               │ bit5=r2 │               │ bit5=r2 │               │ bit5=r2 │               │ bit5=r2 │               │ bit5=r2 │
│ bit4=r3 │               │ bit4=r3 │               │ bit4=r3 │               │ bit4=r3 │               │ bit4=r3 │               │ bit4=r3 │
│ bit3=r4 │               │ bit3=r4 │               │ bit3=r4 │               │ bit3=r4 │               │ bit3=r4 │               │ bit3=r4 │
│ bit2=r5 │               │ bit2=r5 │               │ bit2=r5 │               │ bit2=r5 │               │ bit2=r5 │               │ bit2=r5 │
│ bit1=r6 │               │ bit1=r6 │               │ bit1=r6 │               │ bit1=r6 │               │ bit1=r6 │               │ bit1=r6 │
│ bit0=r7 │               │ bit0=r7 │               │ bit0=r7 │               │ bit0=r7 │               │ bit0=r7 │               │ bit0=r7 │
└─────────┘               └─────────┘               └─────────┘               └─────────┘               └─────────┘               └─────────┘

        Byte 1                          Byte 4                          Byte 7
        Col 0+1, Rows 8-11              Col 2+3, Rows 8-11              Col 4+5, Rows 8-11
        ┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
        │ bit7=c0r8       │             │ bit7=c2r8       │             │ bit7=c4r8       │
        │ bit6=c0r9       │             │ bit6=c2r9       │             │ bit6=c4r9       │
        │ bit5=c0r10      │             │ bit5=c2r10      │             │ bit5=c4r10      │
        │ bit4=c0r11      │             │ bit4=c2r11      │             │ bit4=c4r11      │
        │ bit3=c1r8       │             │ bit3=c3r8       │             │ bit3=c5r8       │
        │ bit2=c1r9       │             │ bit2=c3r9       │             │ bit2=c5r9       │
        │ bit1=c1r10      │             │ bit1=c3r10      │             │ bit1=c5r10      │
        │ bit0=c1r11      │             │ bit0=c3r11      │             │ bit0=c5r11      │
        └─────────────────┘             └─────────────────┘             └─────────────────┘
```

## Example: Letter 'A'

The letter 'A' is encoded as: `[0, 76, 7, 57, 0, 15, 1, 196, 0]`

Decoding this produces:

```
     Col 0  Col 1  Col 2  Col 3  Col 4  Col 5
Row 0   ·      ·      ·      ·      ·      ·
Row 1   ·      ·      ·      ·      ·      ·
Row 2   ·      ·      #      #      ·      ·
Row 3   ·      ·      #      #      ·      ·
Row 4   ·      ·      #      #      #      #
Row 5   ·      #      #      ·      #      #
Row 6   ·      #      #      ·      #      #
Row 7   ·      #      #      #      #      #      #
Row 8   ·      #      #      ·      ·      #      #
Row 9   #      #      ·      ·      ·      ·      #      #
Row 10  ·      ·      ·      ·      ·      ·
Row 11  ·      ·      ·      ·      ·      ·
```

## Encoding Algorithm (Pseudocode)

```python
def encode_character(grid):
    """
    Encode a 6x12 pixel grid to 9 bytes.
    grid[row][col] = 1 for on, 0 for off
    """
    data = [0] * 9

    # Byte mapping: which byte holds rows 0-7 for each column
    col_to_byte = {0: 0, 1: 2, 2: 3, 3: 5, 4: 6, 5: 8}

    # Byte mapping: which byte holds rows 8-11 for each column pair
    col_pair_to_byte = {0: 1, 2: 4, 4: 7}  # even columns

    for col in range(6):
        # Rows 0-7: stored in dedicated bytes
        byte_idx = col_to_byte[col]
        for row in range(8):
            if grid[row][col]:
                data[byte_idx] |= (1 << (7 - row))

        # Rows 8-11: stored in shared nibble bytes
        nibble_byte = col_pair_to_byte[col - (col % 2)]
        is_upper_nibble = (col % 2 == 0)

        for row in range(8, 12):
            if grid[row][col]:
                row_in_nibble = row - 8
                if is_upper_nibble:
                    data[nibble_byte] |= (1 << (7 - row_in_nibble))
                else:
                    data[nibble_byte] |= (1 << (3 - row_in_nibble))

    return data
```

## Decoding Algorithm (Pseudocode)

```python
def decode_character(data):
    """
    Decode 9 bytes to a 6x12 pixel grid.
    Returns grid[row][col] = 1 for on, 0 for off
    """
    grid = [[0] * 6 for _ in range(12)]

    col_to_byte = {0: 0, 1: 2, 2: 3, 3: 5, 4: 6, 5: 8}
    col_pair_to_byte = {0: 1, 2: 4, 4: 7}

    for col in range(6):
        # Rows 0-7
        byte_idx = col_to_byte[col]
        for row in range(8):
            grid[row][col] = (data[byte_idx] >> (7 - row)) & 1

        # Rows 8-11
        nibble_byte = col_pair_to_byte[col - (col % 2)]
        is_upper_nibble = (col % 2 == 0)

        for row in range(8, 12):
            row_in_nibble = row - 8
            if is_upper_nibble:
                grid[row][col] = (data[nibble_byte] >> (7 - row_in_nibble)) & 1
            else:
                grid[row][col] = (data[nibble_byte] >> (3 - row_in_nibble)) & 1

    return grid
```

## Related Files

- `font-editor/font.json` - Font data for all characters
- `font-editor/index.html` - Visual font editor
- `badge_controller/text_renderer.py` - Python implementation for rendering text
