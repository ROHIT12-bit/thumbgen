#!/usr/bin/env python3
"""
Sample test script to validate thumbnail generation with fallback flows.

Usage:
    python test_thumbnail.py

This script tests:
1. Font loading with fallbacks
2. Placeholder image generation when poster is missing
3. Text outline rendering
4. Title truncation for long titles
"""

import os
import sys
import tempfile

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thumbnail import (
    generate_thumbnail,
    generate_placeholder_image,
    draw_text_with_outline,
    truncate_text,
    TITLE_FONT,
    BOLD_FONT,
    MEDIUM_FONT,
    REG_FONT,
    GENRE_FONT,
    CANVAS_WIDTH,
    CANVAS_HEIGHT,
    logger
)
from PIL import Image, ImageDraw

# Use cross-platform temp directory
TEMP_DIR = tempfile.gettempdir()


def test_font_loading():
    """Test that fonts are loaded properly."""
    print("Testing font loading...")
    fonts = {
        'TITLE_FONT': TITLE_FONT,
        'BOLD_FONT': BOLD_FONT,
        'MEDIUM_FONT': MEDIUM_FONT,
        'REG_FONT': REG_FONT,
        'GENRE_FONT': GENRE_FONT,
    }
    
    for name, font in fonts.items():
        if font is not None:
            print(f"  ✓ {name} loaded successfully")
        else:
            print(f"  ✗ {name} failed to load")
    print()


def test_placeholder_generation():
    """Test placeholder image generation."""
    print("Testing placeholder image generation...")
    
    placeholder = generate_placeholder_image(400, 300)
    assert placeholder is not None, "Placeholder should not be None"
    assert placeholder.size == (400, 300), f"Expected size (400, 300), got {placeholder.size}"
    print(f"  ✓ Generated placeholder: {placeholder.size}, mode={placeholder.mode}")
    
    # Save for visual inspection
    output_path = os.path.join(TEMP_DIR, "test_placeholder.png")
    placeholder.save(output_path)
    print(f"  ✓ Saved placeholder to {output_path}")
    print()


def test_truncate_text():
    """Test text truncation with ellipsis."""
    print("Testing text truncation...")
    
    # Short text - no truncation
    result = truncate_text("Short Title", 50)
    assert result == "Short Title", f"Expected 'Short Title', got '{result}'"
    print(f"  ✓ Short text unchanged: '{result}'")
    
    # Long text - should be truncated
    long_text = "This is a very long anime title that should be truncated with ellipsis"
    result = truncate_text(long_text, 30)
    assert len(result) == 30, f"Expected length 30, got {len(result)}"
    assert result.endswith("..."), f"Expected text to end with '...', got '{result}'"
    print(f"  ✓ Long text truncated: '{result}'")
    print()


def test_text_outline():
    """Test text with outline rendering."""
    print("Testing text outline rendering...")
    
    img = Image.new("RGBA", (400, 100), (50, 50, 50))
    draw = ImageDraw.Draw(img)
    
    draw_text_with_outline(
        draw, 
        (20, 30), 
        "Test Outline", 
        BOLD_FONT, 
        fill=(255, 255, 255),
        outline_color=(0, 0, 0),
        outline_width=2
    )
    
    output_path = os.path.join(TEMP_DIR, "test_outline.png")
    img.save(output_path)
    print(f"  ✓ Saved outline test to {output_path}")
    print()


def test_thumbnail_generation():
    """Test full thumbnail generation with sample data."""
    print("Testing thumbnail generation...")
    
    # Sample anime data (mock)
    sample_anime = {
        'title': {
            'english': 'Attack on Titan',
            'romaji': 'Shingeki no Kyojin'
        },
        'coverImage': {
            'extraLarge': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx16498-C6FPmWm59CyP.jpg'
        },
        'averageScore': 84,
        'genres': ['Action', 'Drama', 'Fantasy'],
        'description': 'Several hundred years ago, humans were nearly exterminated by titans. Titans are typically several stories tall, seem to have no intelligence, devour human beings and, worst of all, seem to do it for the pleasure rather than as a food source.'
    }
    
    try:
        result = generate_thumbnail(sample_anime)
        if result:
            # Save the generated thumbnail
            output_path = os.path.join(TEMP_DIR, "test_thumbnail.png")
            with open(output_path, 'wb') as f:
                f.write(result.read())
            print(f"  ✓ Generated thumbnail saved to {output_path}")
        else:
            print("  ✗ Thumbnail generation returned None")
    except Exception as e:
        print(f"  ✗ Thumbnail generation failed: {e}")
        import traceback
        traceback.print_exc()
    print()


def test_thumbnail_with_missing_poster():
    """Test thumbnail generation with missing/invalid poster URL."""
    print("Testing thumbnail with missing poster (placeholder fallback)...")
    
    # Sample anime data with invalid poster URL
    sample_anime = {
        'title': {
            'english': 'Test Anime',
            'romaji': 'Tesuto Anime'
        },
        'coverImage': {
            'extraLarge': 'https://invalid-url.example.com/nonexistent.jpg'
        },
        'averageScore': 75,
        'genres': ['Comedy', 'Romance'],
        'description': 'This is a test anime with a missing poster image to verify placeholder generation.'
    }
    
    try:
        result = generate_thumbnail(sample_anime)
        if result:
            output_path = os.path.join(TEMP_DIR, "test_thumbnail_placeholder.png")
            with open(output_path, 'wb') as f:
                f.write(result.read())
            print(f"  ✓ Generated thumbnail with placeholder saved to {output_path}")
        else:
            print("  ✗ Thumbnail generation returned None")
    except Exception as e:
        print(f"  ✗ Thumbnail generation failed: {e}")
        import traceback
        traceback.print_exc()
    print()


def test_long_title():
    """Test thumbnail generation with a very long title."""
    print("Testing thumbnail with long title (truncation)...")
    
    sample_anime = {
        'title': {
            'english': 'My Very Long Anime Title That Should Be Properly Truncated With Ellipsis For Better Display',
            'romaji': 'Watashi no Totemo Nagai Anime Title'
        },
        'coverImage': {
            'extraLarge': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx16498-C6FPmWm59CyP.jpg'
        },
        'averageScore': 90,
        'genres': ['Action', 'Adventure', 'Fantasy'],
        'description': 'An anime with a very long title to test truncation.'
    }
    
    try:
        result = generate_thumbnail(sample_anime)
        if result:
            output_path = os.path.join(TEMP_DIR, "test_thumbnail_long_title.png")
            with open(output_path, 'wb') as f:
                f.write(result.read())
            print(f"  ✓ Generated thumbnail with long title saved to {output_path}")
        else:
            print("  ✗ Thumbnail generation returned None")
    except Exception as e:
        print(f"  ✗ Thumbnail generation failed: {e}")
        import traceback
        traceback.print_exc()
    print()


def main():
    print("=" * 60)
    print("Thumbnail Generator Test Suite")
    print("=" * 60)
    print()
    
    test_font_loading()
    test_placeholder_generation()
    test_truncate_text()
    test_text_outline()
    test_thumbnail_generation()
    test_thumbnail_with_missing_poster()
    test_long_title()
    
    print("=" * 60)
    print("All tests completed!")
    print(f"Check {TEMP_DIR}/test_*.png files for visual verification.")
    print("=" * 60)


if __name__ == "__main__":
    main()
