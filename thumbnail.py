# thumbnail_bot.py - Final AnimeFlicker Exact Match Generator
import telebot
import requests
import os
import math
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ⚠️ YAHAN APNA NAYA TOKEN DAALNA (purana wala mat daalna)
API_TOKEN = os.getenv("BOT_TOKEN", "7597391690:AAFdUlJBP46IJNvkaM6vIhW6J1fbmUTlkjA")
bot = telebot.TeleBot(API_TOKEN)

# ==========================
# Font Configuration
# ==========================
FONTS_DIR = "fonts"

# Configurable font sizes - Reduced title font size by ~20% (160 -> 128)
TITLE_FONT_SIZE = 128  # Reduced from 160 for smaller anime name
BOLD_FONT_SIZE = 42
MEDIUM_FONT_SIZE = 36
REG_FONT_SIZE = 30
GENRE_FONT_SIZE = 38

# Font scaling factor (adjust this to scale all fonts)
FONT_SCALE = 1.0

# Track logged warnings to avoid repeats
_font_warnings_logged = set()


def _load_font_safe(font_path, size, font_name="font"):
    """
    Safely load a font with fallback to default.
    Returns the loaded font or None if failed.
    """
    scaled_size = int(size * FONT_SCALE)
    
    # Try primary font path
    if os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, scaled_size)
            return font
        except Exception as e:
            if font_path not in _font_warnings_logged:
                logger.warning(f"Could not load font '{font_path}': {e}")
                _font_warnings_logged.add(font_path)
    else:
        if font_path not in _font_warnings_logged:
            logger.warning(f"Font file not found: '{font_path}'")
            _font_warnings_logged.add(font_path)
    
    return None


def _load_font_with_fallbacks(primary_paths, size, font_name="font"):
    """
    Load font from a list of fallback paths.
    Falls back to ImageFont.load_default() if all fail.
    """
    for path in primary_paths:
        font = _load_font_safe(path, size, font_name)
        if font:
            return font
    
    # Final fallback to default
    if font_name not in _font_warnings_logged:
        logger.warning(f"All font paths failed for {font_name}, using default font.")
        _font_warnings_logged.add(font_name)
    
    return ImageFont.load_default()


# Define font fallback chains
TITLE_FONT_PATHS = [
    "BebasNeue-Regular.ttf",
    os.path.join(FONTS_DIR, "BebasNeue-Regular.ttf"),
    os.path.join(FONTS_DIR, "Roboto-Bold.ttf"),
]

BOLD_FONT_PATHS = [
    os.path.join(FONTS_DIR, "Roboto-SemiBold.ttf"),
    os.path.join(FONTS_DIR, "Roboto-Bold.ttf"),
    os.path.join(FONTS_DIR, "Roboto-Medium.ttf"),
    "BebasNeue-Regular.ttf",
]

MEDIUM_FONT_PATHS = [
    os.path.join(FONTS_DIR, "Roboto-SemiBold.ttf"),
    os.path.join(FONTS_DIR, "Roboto-Medium.ttf"),
    os.path.join(FONTS_DIR, "Roboto-Regular.ttf"),
    "BebasNeue-Regular.ttf",
]

REG_FONT_PATHS = [
    os.path.join(FONTS_DIR, "Roboto-Light.ttf"),
    os.path.join(FONTS_DIR, "Roboto-Regular.ttf"),
    os.path.join(FONTS_DIR, "Roboto-Medium.ttf"),
    "BebasNeue-Regular.ttf",
]

GENRE_FONT_PATHS = [
    os.path.join(FONTS_DIR, "Roboto-SemiBold.ttf"),
    os.path.join(FONTS_DIR, "Roboto-Bold.ttf"),
    os.path.join(FONTS_DIR, "Roboto-Medium.ttf"),
    "BebasNeue-Regular.ttf",
]

# Load fonts with fallbacks
TITLE_FONT = _load_font_with_fallbacks(TITLE_FONT_PATHS, TITLE_FONT_SIZE, "title")
BOLD_FONT = _load_font_with_fallbacks(BOLD_FONT_PATHS, BOLD_FONT_SIZE, "bold")
MEDIUM_FONT = _load_font_with_fallbacks(MEDIUM_FONT_PATHS, MEDIUM_FONT_SIZE, "medium")
REG_FONT = _load_font_with_fallbacks(REG_FONT_PATHS, REG_FONT_SIZE, "regular")
GENRE_FONT = _load_font_with_fallbacks(GENRE_FONT_PATHS, GENRE_FONT_SIZE, "genre")

LOGO_FONT = MEDIUM_FONT

CANVAS_WIDTH, CANVAS_HEIGHT = 1280, 720

# Colors
BG_COLOR = (20, 35, 60) # Bluish Dark Background
HEX_OUTLINE = (40, 55, 85)  # Lighter blue outline for background grid
TEXT_COLOR = (255, 255, 255)
SUBTEXT_COLOR = (210, 210, 210)
GENRE_COLOR = (140, 150, 190) # Bluish grey
BUTTON_BG = (40, 60, 100) # Blue button bg
LOGO_COLOR = (255, 255, 255)
HONEYCOMB_OUTLINE_COLOR = (255, 255, 255)
HONEYCOMB_STROKE = 6
TEXT_OUTLINE_COLOR = (0, 0, 0)  # Black outline for text readability

# Text styling configuration
TEXT_OUTLINE_WIDTH = 2  # Pixels of outline around text
TITLE_OUTLINE_WIDTH = 3  # Larger outline for title text
TITLE_MAX_WIDTH = 650  # Max width for title text wrapping
TITLE_MAX_CHARS = 50  # Max characters before truncation with ellipsis
TEXT_PADDING = 50  # Padding from edges

# Placeholder image configuration
PLACEHOLDER_BG_COLOR = (30, 40, 70)  # Dark blue placeholder background
PLACEHOLDER_TEXT = "NO IMAGE"
PLACEHOLDER_PATH = "assets/placeholder.jpg"


def draw_text_with_outline(draw, position, text, font, fill, outline_color=TEXT_OUTLINE_COLOR, outline_width=TEXT_OUTLINE_WIDTH):
    """
    Draw text with an outline/stroke for better readability on varied backgrounds.
    """
    x, y = position
    # Draw outline by rendering text in multiple offset positions
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    # Draw main text on top
    draw.text((x, y), text, font=font, fill=fill)


def truncate_text(text, max_chars=TITLE_MAX_CHARS, ellipsis="..."):
    """
    Truncate text with ellipsis if it exceeds max_chars.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars - len(ellipsis)].rstrip() + ellipsis


def generate_placeholder_image(width, height):
    """
    Generate a placeholder image when the poster is missing.
    Uses a solid color background with centered text.
    """
    # Check if custom placeholder exists
    if os.path.exists(PLACEHOLDER_PATH):
        try:
            img = Image.open(PLACEHOLDER_PATH).convert("RGBA")
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            return img
        except Exception as e:
            logger.warning(f"Could not load placeholder from '{PLACEHOLDER_PATH}': {e}")
    
    # Generate programmatic placeholder
    img = Image.new("RGBA", (width, height), PLACEHOLDER_BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Draw centered placeholder text
    try:
        text = PLACEHOLDER_TEXT
        bbox = draw.textbbox((0, 0), text, font=BOLD_FONT)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        draw_text_with_outline(draw, (x, y), text, BOLD_FONT, TEXT_COLOR)
    except Exception:
        # If font fails, just return solid color
        pass
    
    # Add a subtle border/frame
    border_width = 4
    draw.rectangle(
        [border_width, border_width, width - border_width - 1, height - border_width - 1],
        outline=(60, 80, 120),
        width=border_width
    )
    
    return img


# Helper Functions
def draw_regular_polygon(draw, center, radius, n_sides=6, rotation=30, fill=None, outline=None, width=1):
    points = []
    for i in range(n_sides):
        angle = math.radians(rotation + 360 / n_sides * i)
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        points.append((x, y))
    if fill:
        draw.polygon(points, fill=fill)
    if outline:
        draw.polygon(points, outline=outline, width=width)

def generate_hex_background():
    # Use the hex_bg.png from fonts folder if available
    hex_bg_path = os.path.join(FONTS_DIR, "hex_bg.png")
    if os.path.exists(hex_bg_path):
        try:
            return Image.open(hex_bg_path).convert("RGBA")
        except Exception:
            pass  # Fall through to programmatic generation
    
    # Otherwise generate programmatically
    img = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Background Grid
    hex_radius = 55
    import math
    dx = math.sqrt(3) * hex_radius
    dy = 1.5 * hex_radius

    cols = int(CANVAS_WIDTH / dx) + 2
    rows = int(CANVAS_HEIGHT / dy) + 2

    for row in range(rows):
        for col in range(cols):
            cx = col * dx
            cy = row * dy
            if row % 2 == 1:
                cx += dx / 2

            # Draw faint outline
            draw_regular_polygon(draw, (cx, cy), hex_radius, outline=HEX_OUTLINE, width=2)

    return img

def wrap_text(text, font, max_width):
    avg_char_width = font.getlength('x')
    chars_per_line = int(max_width / avg_char_width)
    wrapped = textwrap.fill(text, width=chars_per_line)
    return wrapped.split('\n')

def generate_thumbnail(anime):
    title = anime['title']['english'] or anime['title']['romaji']
    poster_url = anime['coverImage']['extraLarge']
    score = anime['averageScore']
    genres = anime['genres'][:3]
    desc = (anime['description'] or "").replace("<br>", " ").replace("<i>", "").replace("</i>", "")
    desc = " ".join(desc.split()[:40]) + "..." # Shorter desc for larger text

    # Convert title to uppercase and truncate if too long
    title = truncate_text(title.upper(), TITLE_MAX_CHARS)

    # Background
    bg = generate_hex_background()
    canvas = bg.copy()
    draw = ImageDraw.Draw(canvas)

    # 1. Logo (Top Left)
    icon_x, icon_y = TEXT_PADDING, 40
    sz = 18
    draw.polygon([(icon_x, icon_y+sz), (icon_x+sz, icon_y), (icon_x+2*sz, icon_y+sz), (icon_x+sz, icon_y+2*sz)], outline=LOGO_COLOR, width=3)
    draw.polygon([(icon_x+10, icon_y+sz), (icon_x+sz+10, icon_y), (icon_x+2*sz+10, icon_y+sz), (icon_x+sz+10, icon_y+2*sz)], outline=LOGO_COLOR, width=3)
    draw_text_with_outline(draw, (icon_x + 65, icon_y + 2), "ANIME FLICKER", LOGO_FONT, LOGO_COLOR, outline_width=1)

    # 2. Rating (Below Logo)
    if score:
        rating_text = f"{score/10:.1f}+ Rating"
        draw_text_with_outline(draw, (TEXT_PADDING, 140), rating_text, REG_FONT, TEXT_COLOR, outline_width=1)

    # 3. Title (Large, Below Rating) - with outline for readability
    # Title is already uppercase from line above
    title_lines = wrap_text(title, TITLE_FONT, TITLE_MAX_WIDTH)
    title_y = 180
    title_line_height = 115  # Reduced from 140 to match smaller font
    for i, line in enumerate(title_lines[:2]):  # Max 2 lines
        # Add ellipsis to last displayed line if there are more lines
        if len(title_lines) > 2 and i == 1:
            # Truncate and add ellipsis only if line doesn't already end with ...
            if not line.rstrip().endswith("..."):
                line = line.rstrip()
                if len(line) > 3:
                    line = line[:-3] + "..."
        draw_text_with_outline(draw, (TEXT_PADDING, title_y), line, TITLE_FONT, TEXT_COLOR, 
                               outline_width=TITLE_OUTLINE_WIDTH)
        title_y += title_line_height

    # 4. Genres (Below Title) - with subtle outline
    genre_text = ", ".join(genres).upper()
    draw_text_with_outline(draw, (TEXT_PADDING, title_y + 10), genre_text, GENRE_FONT, GENRE_COLOR, outline_width=1)

    # 5. Description (Below Genres)
    desc_y = title_y + 60
    desc_lines = wrap_text(desc, REG_FONT, 580)
    for line in desc_lines[:4]: # Fewer lines because text is bigger
        draw_text_with_outline(draw, (TEXT_PADDING, desc_y), line, REG_FONT, SUBTEXT_COLOR, outline_width=1)
        desc_y += 42

    # 6. Buttons (Bottom Left)
    btn_y = 620
    btn_width = 210
    btn_height = 65

    # Button 1: DOWNLOAD
    draw.rounded_rectangle((TEXT_PADDING, btn_y, TEXT_PADDING + btn_width, btn_y + btn_height), radius=12, fill=BUTTON_BG)
    text_w = BOLD_FONT.getlength("DOWNLOAD")
    text_x = TEXT_PADDING + (btn_width - text_w) / 2
    draw.text((text_x, btn_y + 12), "DOWNLOAD", font=BOLD_FONT, fill=TEXT_COLOR)

    # Button 2: JOIN NOW
    btn2_x = TEXT_PADDING + btn_width + 40
    draw.rounded_rectangle((btn2_x, btn_y, btn2_x + btn_width, btn_y + btn_height), radius=12, fill=BUTTON_BG)
    text_w = BOLD_FONT.getlength("JOIN NOW")
    text_x = btn2_x + (btn_width - text_w) / 2
    draw.text((text_x, btn_y + 12), "JOIN NOW", font=BOLD_FONT, fill=TEXT_COLOR)


    # 7. Right Side Honeycomb Poster - with fallback for missing poster
    poster = None
    start_x = 550
    width = CANVAS_WIDTH - start_x + 100
    height = CANVAS_HEIGHT
    
    try:
        if poster_url:
            poster_resp = requests.get(poster_url, timeout=10)
            poster_resp.raise_for_status()
            poster = Image.open(BytesIO(poster_resp.content)).convert("RGBA")
    except Exception as e:
        logger.warning(f"Could not load poster from URL '{poster_url}': {e}")
        poster = None
    
    # Use placeholder if poster failed to load
    if poster is None:
        logger.info("Using placeholder image for poster")
        poster = generate_placeholder_image(width, height)

    # Resize poster
    aspect = poster.width / poster.height
    target_aspect = width / height

    if aspect > target_aspect:
        new_height = height
        new_width = int(new_height * aspect)
        poster = poster.resize((new_width, new_height), Image.Resampling.LANCZOS)
        left = (new_width - width) // 2
        poster = poster.crop((left, 0, left + width, new_height))
    else:
        new_width = width
        new_height = int(new_width / aspect)
        poster = poster.resize((new_width, new_height), Image.Resampling.LANCZOS)
        top = (new_height - height) // 2
        poster = poster.crop((0, top, width, top + height))

    # Mask Generation
    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)

    overlay = Image.new("RGBA", (width, height), (0,0,0,0))
    overlay_draw = ImageDraw.Draw(overlay)

    hex_radius = 160
    gap = 8

    dx = math.sqrt(3) * hex_radius
    dy = 1.5 * hex_radius

    cols = int(CANVAS_WIDTH / dx) + 2
    rows = int(CANVAS_HEIGHT / dy) + 2

    for row in range(-1, rows):
        for col in range(-1, cols):
            global_cx = col * dx
            if row % 2 == 1:
                global_cx += dx / 2
            global_cy = row * dy

            local_cx = global_cx - start_x
            local_cy = global_cy

            if global_cx > 650:
                draw_regular_polygon(mask_draw, (local_cx, local_cy), hex_radius - gap, fill=255)
                draw_regular_polygon(overlay_draw, (local_cx, local_cy), hex_radius - gap, outline=HONEYCOMB_OUTLINE_COLOR, width=HONEYCOMB_STROKE)

    poster.putalpha(mask)
    canvas.paste(poster, (start_x, 0), poster)
    canvas.paste(overlay, (start_x, 0), overlay)

    final = BytesIO()
    canvas.convert("RGB").save(final, "PNG")
    final.seek(0)
    return final

@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "Anime ka naam bhej ya /thumb Haikyuu likh\nMain ekdam AnimeFlicker jaisa thumbnail bana dunga")

@bot.message_handler(commands=['thumb'])
def thumb(msg):
    query = msg.text.replace("/thumb", "").strip()
    if not query:
        bot.reply_to(msg, "Bhai anime naam toh likh na!\nExample: /thumb One Piece")
        return
    bot.send_chat_action(msg.chat.id, 'upload_photo')
    try:
        resp = requests.post("https://graphql.anilist.co",
            json={"query": """
            query ($search: String) {
              Media(search: $search, type: ANIME) {
                title { romaji english }
                coverImage { extraLarge }
                averageScore
                genres
                description
              }
            }
            """, "variables": {"search": query}}
        ).json()['data']['Media']
        if not resp:
            bot.reply_to(msg, "Anime nahi mila bhai, sahi spelling likh")
            return
        img = generate_thumbnail(resp)
        title_text = resp['title']['english'] or resp['title']['romaji']
        bot.send_photo(msg.chat.id, img,
                      caption=f"{title_text}\n@YourChannelHere")
    except Exception as e:
        import traceback
        traceback.print_exc()
        bot.reply_to(msg, f"Error: {e}")

if __name__ == "__main__":
    print("Bot chal gaya!")
    bot.infinity_polling()
