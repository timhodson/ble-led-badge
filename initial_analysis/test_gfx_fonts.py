#!/usr/bin/env python3
"""
Test script to demonstrate the updated CharacterMapper with GFX fonts
"""

from character_mapper import CharacterMapper

def print_char_bitmap(char_matrix, char, style="hash"):
    """Print a visual representation of a character bitmap
    
    Args:
        char_matrix: List of 11 integers representing the bitmap
        char: The character being displayed
        style: Display style - 'hash', 'block', 'ascii', or 'minimal'
    """
    print(f"\nCharacter '{char}':")
    
    if style == "hash":
        on_char, off_char = "##", ".."
    elif style == "block":
        on_char, off_char = "██", "  "
    elif style == "ascii":
        on_char, off_char = "**", "  "
    elif style == "minimal":
        on_char, off_char = "#", "."
    else:
        on_char, off_char = "##", ".."
    
    for row in char_matrix:
        row_str = ""
        for bit in range(8):
            if row & (0x80 >> bit):
                row_str += on_char
            else:
                row_str += off_char
        print(row_str)

def test_fonts():
    """Test both GFX and legacy fonts"""
    
    print("=== Testing GFX Font ===")
    gfx_mapper = CharacterMapper(use_gfx_font=True)
    
    test_chars = "ABC123!@#"
    for char in test_chars:
        if gfx_mapper.char_is_allowed(char):
            bitmap = gfx_mapper.char_to_matrix(char)
            print_char_bitmap(bitmap, char, style="minimal")  # Use minimal style for cleaner output
        else:
            print(f"Character '{char}' not supported in GFX font")
    
    print(f"\nGFX Font supports: {len(gfx_mapper.allowed_characters())} characters")
    print(f"First 20: {gfx_mapper.allowed_characters()[:20]}")
    
    print("\n" + "="*50)
    print("=== Testing Legacy Font ===")
    legacy_mapper = CharacterMapper(use_gfx_font=False)
    
    for char in "ABC123":
        if legacy_mapper.char_is_allowed(char):
            bitmap = legacy_mapper.char_to_matrix(char)
            print_char_bitmap(bitmap, char, style="minimal")  # Use minimal style for cleaner output
        else:
            print(f"Character '{char}' not supported in legacy font")
    
    print(f"\nLegacy Font supports: {len(legacy_mapper.allowed_characters())} characters")

def test_display_styles():
    """Test different visual styles for displaying fonts"""
    print("\n=== Testing Different Display Styles ===")
    
    gfx_mapper = CharacterMapper(use_gfx_font=True)
    test_char = 'A'
    bitmap = gfx_mapper.char_to_matrix(test_char)
    
    styles = ['minimal', 'hash', 'ascii', 'block']
    for style in styles:
        print(f"\n--- Style: {style} ---")
        print_char_bitmap(bitmap, test_char, style=style)

def test_string_conversion():
    """Test converting entire strings"""
    print("\n=== Testing String Conversion ===")
    
    gfx_mapper = CharacterMapper(use_gfx_font=True)
    test_string = "HELLO"
    
    if gfx_mapper.is_string_allowed(test_string):
        matrices = gfx_mapper.string_to_matrices(test_string)
        print(f"String '{test_string}' converted to {len(matrices)} character matrices")
        
        # Print each character side by side
        print("\nVisual representation:")
        for row in range(11):
            line = ""
            for char_matrix in matrices:
                for bit in range(8):
                    if char_matrix[row] & (0x80 >> bit):
                        line += "#"  # Use single # for compact display
                    else:
                        line += "."  # Use dots for empty pixels
                line += " "  # Space between characters
            print(line)
    else:
        print(f"String '{test_string}' contains unsupported characters")

if __name__ == "__main__":
    test_display_styles()  # Test display options first
    test_fonts()
    test_string_conversion()