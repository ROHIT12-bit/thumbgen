"""
Enhanced Anime Thumbnail Generator Bot
Generates high-quality thumbnails matching AnimeFlicker style
"""
import telebot
import requests
import os
import math
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
from io import BytesIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot Configuration
API_TOKEN = os.getenv("BOT_TOKEN", "7597391690:AAFdUlJBP46IJNvkaM6vIhW6J1fbmUTlkjA")
bot = telebot.TeleBot(API_TOKEN)

# Canvas dimensions
CANVAS_WIDTH, CANVAS_HEIGHT = 1280, 720

# Color scheme - matching Haikyu reference
BG_COLOR = (15, 25, 45)  # Deep blue-black
HEX_OUTLINE = (35, 50, 80)  # Subtle hex outlines
TEXT_COLOR = (255, 255, 255)
SUBTEXT_COLOR = (200, 210, 220)
GENRE_COLOR = (150, 160, 180)
BUTTON_BG = (35, 55, 95)
LOGO_COLOR = (255, 255, 255)
HONEYCOMB_OUTLINE = (255, 255, 255)

# Font configuration
FONTS_DIR = "fonts"
FONT_SCALE = 1.0

# Font sizes (optimized for readability)
TITLE_FONT_SIZE = 110
BOLD_FONT_SIZE = 40
MEDIUM_FONT_SIZE = 34
REG_FONT_SIZE = 28
GENRE_FONT_SIZE = 36
LOGO_FONT_SIZE = 32

# Layout constants
TEXT_PADDING = 50
TITLE_MAX_CHARS = 45
TITLE_MAX_WIDTH = 600
TEXT_OUTLINE_WIDTH = 3
POSTER_START_X = 580

# Placeholder settings
PLACEHOLDER_BG = (25, 35, 60)
PLACEHOLDER_TEXT = "NO IMAGE"


class FontManager:
    """Manages font loading with fallback support"""
    
    def __init__(self):
        self._loaded_fonts = {}
        self._warnings_logged = set()
    
    def load_font(self, font_paths, size, name="font"):
        """Load font from list of paths with fallbacks"""
        cache_key = (tuple(font_paths), size)
        if cache_key in self._loaded_fonts:
            return self._loaded_fonts[cache_key]
        
        scaled_size = int(size * FONT_SCALE)
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, scaled_size)
                    self._loaded_fonts[cache_key] = font
                    return font
                except Exception as e:
                    if path not in self._warnings_logged:
                        logger.warning(f"Failed to load {name} font '{path}': {e}")
                        self._warnings_logged.add(path)
        
        # Fallback to default
        if name not in self._warnings_logged:
            logger.warning(f"Using default font for {name}")
            self._warnings_logged.add(name)
        
        default_font = ImageFont.load_default()
        self._loaded_fonts[cache_key] = default_font
        return default_font


# Initialize font manager
font_manager = FontManager()

# Font paths with fallbacks
TITLE_FONT_PATHS = [
    "BebasNeue-Regular.ttf",
    os.path.join(FONTS_DIR, "BebasNeue-Regular.ttf"),
    os.path.join(FONTS_DIR, "Roboto-Bold.ttf"),
]

BOLD_FONT_PATHS = [
    os.path.join(FONTS_DIR, "Roboto-Bold.ttf"),
    os.path.join(FONTS_DIR, "Roboto-SemiBold.ttf"),
]

MEDIUM_FONT_PATHS = [
    os.path.join(FONTS_DIR, "Roboto-Medium.ttf"),
    os.path.join(FONTS_DIR, "Roboto-Regular.ttf"),
]

REG_FONT_PATHS = [
    os.path.join(FONTS_DIR, "Roboto-Regular.ttf"),
    os.path.join(FONTS_DIR, "Roboto-Light.ttf"),
]

# Load fonts
TITLE_FONT = font_manager.load_font(TITLE_FONT_PATHS, TITLE_FONT_SIZE, "title")
BOLD_FONT = font_manager.load_font(BOLD_FONT_PATHS, BOLD_FONT_SIZE, "bold")
MEDIUM_FONT = font_manager.load_font(MEDIUM_FONT_PATHS, MEDIUM_FONT_SIZE, "medium")
REG_FONT = font_manager.load_font(REG_FONT_PATHS, REG_FONT_SIZE, "regular")
GENRE_FONT = font_manager.load_font(BOLD_FONT_PATHS, GENRE_FONT_SIZE, "genre")
LOGO_FONT = font_manager.load_font(MEDIUM_FONT_PATHS, LOGO_FONT_SIZE, "logo")


def draw_text_with_outline(draw, pos, text, font, fill, outline_color=(0, 0, 0), outline_width=2):
    """Draw text with outline for better readability"""
    x, y = pos
    # Draw outline
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    # Draw main text
    draw.text((x, y), text, font=font, fill=fill)


def truncate_text(text, max_chars):
    """Truncate text with ellipsis"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3].rstrip() + "..."


def draw_hexagon(draw, center, radius, fill=None, outline=None, width=1):
    """Draw a hexagon"""
    points = []
    for i in range(6):
        angle = math.radians(30 + 60 * i)
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        points.append((x, y))
    
    if fill:
        draw.polygon(points, fill=fill)
    if outline:
        draw.polygon(points, outline=outline, width=width)


def generate_hex_background():
    """Generate honeycomb background pattern"""
    # Try to load pre-made background
    hex_bg_path = os.path.join(FONTS_DIR, "hex_bg.png")
    if os.path.exists(hex_bg_path):
        try:
            return Image.open(hex_bg_path).convert("RGBA")
        except Exception as e:
            logger.warning(f"Could not load hex_bg.png: {e}")
    
    # Generate programmatically
    img = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    hex_radius = 55
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
            
            draw_hexagon(draw, (cx, cy), hex_radius, outline=HEX_OUTLINE, width=2)
    
    return img


def generate_placeholder(width, height):
    """Generate placeholder when poster is unavailable"""
    img = Image.new("RGBA", (width, height), PLACEHOLDER_BG)
    draw = ImageDraw.Draw(img)
    
    # Draw text
    try:
        bbox = draw.textbbox((0, 0), PLACEHOLDER_TEXT, font=BOLD_FONT)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        draw_text_with_outline(draw, (x, y), PLACEHOLDER_TEXT, BOLD_FONT, TEXT_COLOR)
    except:
        pass
    
    # Border
    draw.rectangle([4, 4, width-5, height-5], outline=(70, 90, 130), width=4)
    
    return img


def wrap_text(text, font, max_width):
    """Wrap text to fit within max_width"""
    try:
        avg_char_width = font.getlength('x')
    except:
        avg_char_width = 10
    
    chars_per_line = max(1, int(max_width / avg_char_width))
    wrapped = textwrap.fill(text, width=chars_per_line)
    return wrapped.split('\n')


def load_poster(url, width, height):
    """Load and resize poster with fallback"""
    poster = None
    
    try:
        if url:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            poster = Image.open(BytesIO(resp.content)).convert("RGBA")
    except Exception as e:
        logger.warning(f"Failed to load poster: {e}")
    
    if poster is None:
        return generate_placeholder(width, height)
    
    # Resize to cover area
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
        poster = poster.crop((0, top, new_width, top + height))
    
    return poster


def generate_thumbnail(anime):
    """Generate complete thumbnail"""
    # Extract data
    title = (anime['title']['english'] or anime['title']['romaji']).upper()
    title = truncate_text(title, TITLE_MAX_CHARS)
    poster_url = anime['coverImage']['extraLarge']
    score = anime.get('averageScore')
    genres = anime.get('genres', [])[:3]
    desc = (anime.get('description') or "").replace("<br>", " ").replace("<i>", "").replace("</i>", "")
    desc = " ".join(desc.split()[:35]) + "..."
    
    # Create background
    canvas = generate_hex_background()
    draw = ImageDraw.Draw(canvas)
    
    # 1. Logo (top-left)
    icon_x, icon_y = TEXT_PADDING, 40
    sz = 16
    # Diamond shapes for logo
    draw.polygon(
        [(icon_x, icon_y+sz), (icon_x+sz, icon_y), (icon_x+2*sz, icon_y+sz), (icon_x+sz, icon_y+2*sz)],
        outline=LOGO_COLOR, width=3
    )
    draw.polygon(
        [(icon_x+10, icon_y+sz), (icon_x+sz+10, icon_y), (icon_x+2*sz+10, icon_y+sz), (icon_x+sz+10, icon_y+2*sz)],
        outline=LOGO_COLOR, width=3
    )
    draw_text_with_outline(draw, (icon_x + 60, icon_y), "ANIME FLICKER", LOGO_FONT, LOGO_COLOR, outline_width=2)
    
    # 2. Rating
    if score:
        rating_text = f"{score/10:.1f}+ Rating"
        draw_text_with_outline(draw, (TEXT_PADDING, 120), rating_text, REG_FONT, SUBTEXT_COLOR, outline_width=2)
    
    # 3. Title (large, bold)
    title_lines = wrap_text(title, TITLE_FONT, TITLE_MAX_WIDTH)
    title_y = 170
    for i, line in enumerate(title_lines[:2]):
        if i == 1 and len(title_lines) > 2:
            line = truncate_text(line, 30)
        draw_text_with_outline(draw, (TEXT_PADDING, title_y), line, TITLE_FONT, TEXT_COLOR, outline_width=3)
        title_y += 100
    
    # 4. Genres
    if genres:
        genre_text = ", ".join(g.upper() for g in genres)
        draw_text_with_outline(draw, (TEXT_PADDING, title_y + 10), genre_text, GENRE_FONT, GENRE_COLOR, outline_width=2)
    
    # 5. Description
    desc_y = title_y + 65
    desc_lines = wrap_text(desc, REG_FONT, 550)
    for line in desc_lines[:4]:
        draw_text_with_outline(draw, (TEXT_PADDING, desc_y), line, REG_FONT, SUBTEXT_COLOR, outline_width=2)
        desc_y += 38
    
    # 6. Buttons
    btn_y = 610
    btn_width = 200
    btn_height = 60
    
    # Download button
    draw.rounded_rectangle(
        (TEXT_PADDING, btn_y, TEXT_PADDING + btn_width, btn_y + btn_height),
        radius=10, fill=BUTTON_BG
    )
    try:
        text_w = BOLD_FONT.getlength("DOWNLOAD")
        text_x = TEXT_PADDING + (btn_width - text_w) / 2
    except:
        text_x = TEXT_PADDING + 50
    draw.text((text_x, btn_y + 10), "DOWNLOAD", font=BOLD_FONT, fill=TEXT_COLOR)
    
    # Join button
    btn2_x = TEXT_PADDING + btn_width + 30
    draw.rounded_rectangle(
        (btn2_x, btn_y, btn2_x + btn_width, btn_y + btn_height),
        radius=10, fill=BUTTON_BG
    )
    try:
        text_w = BOLD_FONT.getlength("JOIN NOW")
        text_x = btn2_x + (btn_width - text_w) / 2
    except:
        text_x = btn2_x + 50
    draw.text((text_x, btn_y + 10), "JOIN NOW", font=BOLD_FONT, fill=TEXT_COLOR)
    
    # 7. Honeycomb poster (right side)
    poster_width = CANVAS_WIDTH - POSTER_START_X + 100
    poster_height = CANVAS_HEIGHT
    
    poster = load_poster(poster_url, poster_width, poster_height)
    
    # Create honeycomb mask
    mask = Image.new("L", (poster_width, poster_height), 0)
    mask_draw = ImageDraw.Draw(mask)
    
    overlay = Image.new("RGBA", (poster_width, poster_height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    hex_radius = 160
    gap = 8
    dx = math.sqrt(3) * hex_radius
    dy = 1.5 * hex_radius
    
    cols = int(CANVAS_WIDTH / dx) + 3
    rows = int(CANVAS_HEIGHT / dy) + 3
    
    for row in range(-1, rows):
        for col in range(-1, cols):
            global_cx = col * dx
            if row % 2 == 1:
                global_cx += dx / 2
            global_cy = row * dy
            
            local_cx = global_cx - POSTER_START_X
            local_cy = global_cy
            
            # Only draw hexagons on the right side
            if global_cx > 650:
                draw_hexagon(mask_draw, (local_cx, local_cy), hex_radius - gap, fill=255)
                draw_hexagon(overlay_draw, (local_cx, local_cy), hex_radius - gap, 
                           outline=HONEYCOMB_OUTLINE, width=6)
    
    # Apply mask and paste
    poster.putalpha(mask)
    canvas.paste(poster, (POSTER_START_X, 0), poster)
    canvas.paste(overlay, (POSTER_START_X, 0), overlay)
    
    # Convert and return
    output = BytesIO()
    canvas.convert("RGB").save(output, "PNG", quality=95)
    output.seek(0)
    return output


@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(
        msg,
        "🎬 *AnimeFlicker Thumbnail Generator*\n\n"
        "Send anime name or use:\n"
        "`/thumb Haikyu`\n\n"
        "I'll create a professional thumbnail!",
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['thumb'])
def thumb(msg):
    query = msg.text.replace("/thumb", "").strip()
    if not query:
        bot.reply_to(msg, "❌ Please provide an anime name!\nExample: `/thumb One Piece`", parse_mode='Markdown')
        return
    
    bot.send_chat_action(msg.chat.id, 'upload_photo')
    
    try:
        # Query AniList API
        response = requests.post(
            "https://graphql.anilist.co",
            json={
                "query": """
                query ($search: String) {
                  Media(search: $search, type: ANIME) {
                    title { romaji english }
                    coverImage { extraLarge }
                    averageScore
                    genres
                    description
                  }
                }
                """,
                "variables": {"search": query}
            },
            timeout=15
        )
        
        data = response.json()
        anime = data.get('data', {}).get('Media')
        
        if not anime:
            bot.reply_to(msg, f"❌ Anime not found: `{query}`\nPlease check the spelling!", parse_mode='Markdown')
            return
        
        # Generate thumbnail
        img = generate_thumbnail(anime)
        title_text = anime['title']['english'] or anime['title']['romaji']
        
        bot.send_photo(
            msg.chat.id,
            img,
            caption=f"🎬 *{title_text}*\n\n@AnimeFlicker",
            parse_mode='Markdown'
        )
        
    except requests.exceptions.Timeout:
        bot.reply_to(msg, "⏰ Request timed out. Please try again!")
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}", exc_info=True)
        bot.reply_to(msg, f"❌ Error: {str(e)}\n\nPlease try again later.")


@bot.message_handler(func=lambda m: True)
def handle_text(msg):
    """Handle plain text anime names"""
    query = msg.text.strip()
    if len(query) > 2:
        # Treat as anime search
        msg.text = f"/thumb {query}"
        thumb(msg)


if __name__ == "__main__":
    logger.info("🚀 AnimeFlicker Bot starting...")
    logger.info(f"Bot token: {'*' * 20}{API_TOKEN[-10:]}")
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
