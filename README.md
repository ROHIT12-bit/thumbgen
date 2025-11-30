# Thumbgen - Anime Thumbnail Generator

A Telegram bot that generates beautiful AnimeFlicker-style thumbnails for anime series.

## Features

- 🎨 **Honeycomb poster design** - Unique hexagonal pattern overlay on anime poster
- 📝 **Auto-fetches anime info** - Gets title, rating, genres, and description from AniList
- 🔤 **Robust font handling** - Multiple fallback fonts with graceful degradation
- 🖼️ **Placeholder support** - Generates placeholder image when poster is unavailable
- ✨ **Text outlines** - Black stroke around text for better readability on any background
- 📐 **Smart text handling** - Auto-wrapping and truncation with ellipsis for long titles

## Setup

### Prerequisites

- Python 3.7+
- PIL/Pillow

### Installation

```bash
pip install -r requirements.txt
```

### Environment Variables

Set your Telegram bot token:

```bash
export BOT_TOKEN="your_telegram_bot_token_here"
```

### Running the Bot

```bash
python thumbnail.py
```

## Usage

1. Start a chat with your bot
2. Send `/thumb <anime name>` (e.g., `/thumb Attack on Titan`)
3. The bot will generate and send the thumbnail

## Font Configuration

The generator uses a fallback font loading system:

### Font Priority (Title)
1. `BebasNeue-Regular.ttf` (root directory)
2. `fonts/BebasNeue-Regular.ttf`
3. `fonts/Roboto-Bold.ttf`
4. System default font

### Font Priority (Body Text)
1. `fonts/Roboto-SemiBold.ttf`
2. `fonts/Roboto-Bold.ttf`
3. `fonts/Roboto-Medium.ttf`
4. `BebasNeue-Regular.ttf`
5. System default font

### Customizing Fonts

To use custom fonts:
1. Place `.ttf` files in the `fonts/` directory
2. Update the font path constants in `thumbnail.py`

### Font Size Configuration

Edit these constants in `thumbnail.py` to adjust font sizes:

```python
TITLE_FONT_SIZE = 128      # Anime title (reduced from 160)
BOLD_FONT_SIZE = 42        # Buttons
MEDIUM_FONT_SIZE = 36      # Logo text
REG_FONT_SIZE = 30         # Description, rating
GENRE_FONT_SIZE = 38       # Genre tags

FONT_SCALE = 1.0           # Global scaling factor (1.0 = 100%)
```

## Placeholder Images

When a poster image fails to load, the generator creates a placeholder automatically.

### Custom Placeholder

To use a custom placeholder image:
1. Create `assets/placeholder.jpg`
2. The generator will use it instead of the programmatic placeholder

### Placeholder Configuration

```python
PLACEHOLDER_BG_COLOR = (30, 40, 70)    # Dark blue background
PLACEHOLDER_TEXT = "NO IMAGE"          # Centered text
PLACEHOLDER_PATH = "assets/placeholder.jpg"  # Custom placeholder path
```

## Text Styling

The generator includes text outlines for better readability:

```python
TEXT_OUTLINE_COLOR = (0, 0, 0)   # Black outline
TEXT_OUTLINE_WIDTH = 2           # Pixels for body text
TITLE_OUTLINE_WIDTH = 3          # Pixels for title text
```

### Title Handling

- **Max width**: 650 pixels before wrapping
- **Max characters**: 50 before truncation with "..."
- **Max lines**: 2 lines displayed

## Testing

Run the test script to validate thumbnail generation:

```bash
python test_thumbnail.py
```

This tests:
- Font loading with fallbacks
- Placeholder image generation
- Text outline rendering
- Title truncation for long titles

Test outputs are saved to `/tmp/test_*.png` for visual inspection.

## Project Structure

```
thumbgen/
├── thumbnail.py          # Main bot and thumbnail generator
├── test_thumbnail.py     # Test script for validation
├── requirements.txt      # Python dependencies
├── BebasNeue-Regular.ttf # Title font
├── fonts/                # Additional fonts
│   ├── Roboto-*.ttf     # Roboto font family
│   └── hex_bg.png       # Pre-generated hex background
├── background.jpg        # Background image (optional)
├── plp.jpg              # Poster layout placeholder (optional)
└── assets/              # Custom assets (optional)
    └── placeholder.jpg  # Custom placeholder image
```

## Deployment

For Heroku or similar platforms, a `Procfile` is included:

```
worker: python thumbnail.py
```

## License

This project uses the following open-source fonts:
- **Bebas Neue** - SIL Open Font License
- **Roboto** - Apache License 2.0

## Troubleshooting

### "Could not load font" warnings

This is normal if some font files are missing or empty. The generator will use fallback fonts automatically.

### "Using placeholder image for poster"

The poster URL was unreachable. Check your internet connection or the AniList API status.

### Font appears too small/large

Adjust `FONT_SCALE` in `thumbnail.py`:
- `FONT_SCALE = 1.2` for 20% larger
- `FONT_SCALE = 0.8` for 20% smaller
