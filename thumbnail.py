#!/usr/bin/env python3
"""
Anime Mayhem Style Thumbnail Generator Bot
- Auto-detects fonts from ./fonts directory (Bold/Regular/Light)
- Uses AniList GraphQL to fetch anime data (or local fallback image)
- Produces a PNG thumbnail (1280x720) styled after provided reference
- Built for reliability: sensible timeouts, fallbacks, detailed logging
"""

import os
import sys
import logging
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import textwrap
import re
import math
import glob

# Optional: telegram bot (pyTelegramBotAPI / telebot)
try:
    import telebot
except Exception:
    telebot = None

# ---------- Configuration ----------
CANVAS_WIDTH, CANVAS_HEIGHT = 1280, 720

# Colors (tweak if needed)
BG_DARK = (30, 35, 40)
CARD_BG = (26, 30, 34)            # base card dark (will be used with alpha)
CARD_ALPHA = 80  # Made lighter transparent
TEXT_WHITE = (245, 245, 245)
TEXT_GREY = (190, 195, 200)
ACCENT_ORANGE = (255, 140, 60)
GENRE_BG = (245, 245, 245)
GENRE_TEXT = (20, 20, 20)
PLACEHOLDER_BG = (40, 45, 55)

# Fonts directory
FONTS_DIR = os.getenv("FONTS_DIR", "fonts")

# TeleBot token (env) - replace with your token or set env BOT_TOKEN
API_TOKEN = os.getenv("BOT_TOKEN", "8388209429:AAGSHFmVDpZqryMYJur4FGYZAjUxWEe8VIk")
# If you don't want to run bot and only want the generator, set NO_BOT=1
NO_BOT = bool(os.getenv("NO_BOT", ""))

# Local test background (the uploaded file path in the container)
LOCAL_TEST_BG = "/mnt/data/6152203217874390055.jpg"

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("anime-mayhem-gen")

# ---------- Font Manager ----------
class FontManager:
    def __init__(self, fonts_dir=FONTS_DIR):
        self.fonts_dir = fonts_dir
        self.fonts = self._scan_fonts()
        logger.info(f"Found {sum(len(v) for v in self.fonts.values())} fonts in {self.fonts_dir}")

    def _scan_fonts(self):
        """
        Scans fonts directory and classifies them roughly into 'bold', 'regular', 'light', 'other'
        based on filename heuristics.
        Returns dict: {'bold': [...], 'regular': [...], 'light': [...], 'all':[...]}
        """
        data = {"bold": [], "regular": [], "light": [], "all": []}
        if not os.path.isdir(self.fonts_dir):
            logger.warning(f"Fonts dir '{self.fonts_dir}' not found. Using default PIL font.")
            return data

        exts = ("*.ttf", "*.otf")
        for ext in exts:
            for path in glob.glob(os.path.join(self.fonts_dir, ext)):
                name = os.path.basename(path).lower()
                data["all"].append(path)
                if any(k in name for k in ("bold", "black", "heavy", "demi", "semibold")):
                    data["bold"].append(path)
                elif any(k in name for k in ("light", "thin", "hairline")):
                    data["light"].append(path)
                else:
                    data["regular"].append(path)
        # fallback: if classes empty, distribute
        if not data["regular"] and data["all"]:
            data["regular"] = data["all"][:]
        return data

    def pick_font(self, style="regular", size=32):
        """
        Returns ImageFont instance. style in ('bold','regular','light').
        Falls back gracefully to other categories or default font.
        """
        style = style if style in ("bold","regular","light") else "regular"
        cand = self.fonts.get(style, []) or self.fonts.get("regular", []) or self.fonts.get("all", [])
        if cand:
            path = cand[0]
            try:
                return ImageFont.truetype(path, size)
            except Exception as e:
                logger.warning(f"Failed to load font {path} size {size}: {e}")
        # fallback default
        logger.warning("Using default PIL font as fallback.")
        return ImageFont.load_default()

# Instantiate font manager
font_manager = FontManager()

# Predefine sizes (you can tweak these)
LOGO_SIZE = 46
TITLE_SIZE = 100  # Made smaller
SUBTITLE_SIZE = 80
INFO_LABEL_SIZE = 24  # Made smaller and equal
INFO_VALUE_SIZE = 24  # Made smaller and equal
CHAR_NAME_SIZE = 40
CHAR_DESC_SIZE = 22
GENRE_SIZE = 22  # Made smaller for genre pills
OVERVIEW_TITLE_SIZE = 28  # New smaller size for "SYNOPSIS"

# Load fonts (try to pick best available)
LOGO_FONT = font_manager.pick_font("bold", LOGO_SIZE)
TITLE_FONT = font_manager.pick_font("bold", TITLE_SIZE)
SUBTITLE_FONT = font_manager.pick_font("bold", SUBTITLE_SIZE)
INFO_LABEL_FONT = font_manager.pick_font("bold", INFO_LABEL_SIZE)
INFO_VALUE_FONT = font_manager.pick_font("regular", INFO_VALUE_SIZE)
CHAR_NAME_FONT = font_manager.pick_font("bold", CHAR_NAME_SIZE)
CHAR_DESC_FONT = font_manager.pick_font("light", CHAR_DESC_SIZE)
GENRE_FONT = font_manager.pick_font("bold", GENRE_SIZE)
OVERVIEW_TITLE_FONT = font_manager.pick_font("bold", OVERVIEW_TITLE_SIZE)  # New font for synopsis title

# ---------- Utility functions ----------
def text_size(draw, text, font):
    """
    Wrapper to get text size using textbbox where available for accuracy.
    """
    try:
        bbox = draw.textbbox((0,0), text, font=font)
        return bbox[2]-bbox[0], bbox[3]-bbox[1]
    except Exception:
        try:
            return draw.textsize(text, font=font)
        except Exception:
            # rough fallback
            return len(text) * (font.size if hasattr(font,'size') else 10), font.size if hasattr(font,'size') else 10

def wrap_text_to_width(text, font, max_width, draw):
    """
    Wraps text into multiple lines so each line width <= max_width
    Uses a word-based greedy algorithm.
    """
    words = text.split()
    if not words:
        return []
    lines = []
    cur = words[0]
    for w in words[1:]:
        wcur = cur + " " + w
        wwidth, _ = text_size(draw, wcur, font)
        if wwidth <= max_width:
            cur = wcur
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines

def download_image(url, timeout=10):
    try:
        headers = {"User-Agent":"Mozilla/5.0 (compatible)"}
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return Image.open(BytesIO(r.content))
    except Exception as e:
        logger.warning(f"Failed to download image {url}: {e}")
        return None

def resize_cover_to_fill(img, target_w, target_h):
    """
    Resize and crop to cover target (similar to CSS cover)
    """
    if img is None:
        return None
    img = img.convert("RGBA")
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    tgt_ratio = target_w / target_h
    if src_ratio > tgt_ratio:
        # source wider -> match height
        new_h = target_h
        new_w = int(new_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / src_ratio)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))

def rounded_rectangle_mask(size, radius):
    w, h = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0,0,w,h), radius=radius, fill=255)
    return mask

# ---------- Thumbnail generator ----------
def generate_thumbnail(anime: dict, prefer_local_bg=False):
    """
    anime: dict with keys similar to AniList GraphQL result:
      - title: {'romaji':..., 'english':...}
      - coverImage: {'extraLarge':...}
      - averageScore
      - genres
      - description
      - status, season, seasonYear
      - studios: {'nodes':[{'name':...}]}
      - characters: {'nodes':[{'name':{'full':...}, 'description':..., 'image':{'large':...}}]}
    Returns BytesIO PNG
    """
    # Extract fields safely
    title_raw = (anime.get("title", {}) or {}).get("english") or (anime.get("title", {}) or {}).get("romaji") or "UNKNOWN"
    title = str(title_raw).upper()
    poster_url = (anime.get("coverImage") or {}).get("extraLarge")
    score = anime.get("averageScore", 0) or 0
    genres = anime.get("genres", []) or []
    status = (anime.get("status") or "UNKNOWN")
    studios = (anime.get("studios", {}) or {}).get("nodes", []) or []
    studio_name = studios[0]["name"] if studios else "Unknown Studio"
    desc = anime.get("description") or "No description available"
    # strip basic html tags that AniList uses
    desc = re.sub(r"<[^>]+>", "", desc)
    desc = " ".join(desc.split())
    # Keep a shorter excerpt
    desc_excerpt = " ".join(desc.split()[:60])
    if len(desc.split()) > 60:
        desc_excerpt += "..."

    # Character extraction
    characters = (anime.get("characters", {}) or {}).get("nodes", []) or []
    if characters:
        char = characters[0]
        char_name = (char.get("name", {}) or {}).get("full", "MAIN CHARACTER").upper()
        char_desc_raw = char.get("description", "No character description available")
        char_desc_raw = re.sub(r"<[^>]+>", "", char_desc_raw)
        char_desc_raw = " ".join(char_desc_raw.split())
        char_desc_excerpt = " ".join(char_desc_raw.split()[:40])
        if len(char_desc_raw.split()) > 40:
            char_desc_excerpt += "..."
        char_img_url = (char.get("image", {}) or {}).get("large")
    else:
        char_name = "MAIN CHARACTER"
        char_desc_excerpt = "No character info available."
        char_img_url = None

    # Background: try poster_url first unless prefer_local_bg True
    bg_img = None
    if poster_url and not prefer_local_bg:
        bg_img = download_image(poster_url)
    if bg_img is None:
        # try local test
        if os.path.isfile(LOCAL_TEST_BG):
            try:
                bg_img = Image.open(LOCAL_TEST_BG)
            except Exception:
                bg_img = None
    if bg_img is None:
        bg_img = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_DARK)
    # Resize + overlay
    bg_img = resize_cover_to_fill(bg_img, CANVAS_WIDTH, CANVAS_HEIGHT).convert("RGBA")
    overlay = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0,0,0,120))
    canvas = Image.alpha_composite(bg_img, overlay)

    draw = ImageDraw.Draw(canvas)

    # --- Logo top-left ---
    logo_x = 40
    logo_y = 28
    draw.text((logo_x, logo_y), "ANIMWORLDZONE", font=LOGO_FONT, fill=TEXT_WHITE)  # Fixed and replaced

    # --- Team text top-right ---
    team_text = "TEAM"
    team_name = "Animworldzone"  # Updated to match
    t_w, t_h = text_size(draw, team_text, INFO_LABEL_FONT)
    draw.text((CANVAS_WIDTH - 260, 30), team_text, font=INFO_LABEL_FONT, fill=TEXT_GREY)
    draw.text((CANVAS_WIDTH - 260 + t_w + 8, 26), team_name, font=CHAR_NAME_FONT, fill=ACCENT_ORANGE)

    # --- Genre pills ---
    genre_start_x = 50
    genre_start_y = 120
    pill_gap = 14
    pill_height = 36  # Made smaller
    max_genres = 5
    for g in (genres or [])[:max_genres]:
        text_g = str(g).upper()
        tw, th = text_size(draw, text_g, GENRE_FONT)
        pill_w = tw + 36
        # pill box
        pill_bbox = (genre_start_x, genre_start_y, genre_start_x + pill_w, genre_start_y + pill_height)
        draw.rounded_rectangle(pill_bbox, radius=pill_height//2, fill=GENRE_BG)
        draw.text((genre_start_x + 18, genre_start_y + (pill_height - th)//2), text_g, font=GENRE_FONT, fill=GENRE_TEXT)
        genre_start_x += pill_w + pill_gap

    # --- Main left card (transparent) ---
    card_x = 50
    card_y = 190
    card_w = 750
    card_h = 420
    # semi-transparent card
    card_layer = Image.new("RGBA", (card_w, card_h), (CARD_BG[0], CARD_BG[1], CARD_BG[2], CARD_ALPHA))
    # rounded mask
    mask = rounded_rectangle_mask((card_w, card_h), radius=28)
    canvas.paste(card_layer, (card_x, card_y), mask)

    # Title inside card (big, but smaller now)
    inner_draw = ImageDraw.Draw(canvas)
    title_x = card_x + 36
    title_y = card_y + 36
    # Wrap the title to max 2 lines
    max_title_w = card_w - 72
    title_lines = wrap_text_to_width(title, TITLE_FONT, max_title_w, draw)
    # If more than 2 lines, combine/trim
    if len(title_lines) > 2:
        # join until fits 2 lines
        joined = " ".join(title_lines)
        title_lines = wrap_text_to_width(joined, TITLE_FONT, max_title_w, draw)[:2]
    for i, line in enumerate(title_lines[:2]):
        # reduce y-gap a bit for more compact look
        y_off = title_y + i * int(TITLE_FONT.size * 0.75)
        inner_draw.text((title_x, y_off), line, font=TITLE_FONT, fill=TEXT_WHITE)

    # Subtitle: season/year or "SEASON X"
    subtitle_y = title_y + (TITLE_FONT.size if len(title_lines)==1 else int(TITLE_FONT.size * 0.75)*len(title_lines)) + 10
    season = anime.get("season") or ""
    seasonYear = anime.get("seasonYear") or ""
    if season and seasonYear:
        subtitle_text = f"{season.upper()} {seasonYear}"
        inner_draw.text((title_x, subtitle_y), subtitle_text, font=SUBTITLE_FONT, fill=TEXT_WHITE)

    # --- Separate small transparent box for information ---
    info_box_x = card_x + 36
    info_box_y = subtitle_y + 110
    info_box_w = 400
    info_box_h = 100  # Slightly smaller
    info_layer = Image.new("RGBA", (info_box_w, info_box_h), (CARD_BG[0], CARD_BG[1], CARD_BG[2], CARD_ALPHA))
    info_mask = rounded_rectangle_mask((info_box_w, info_box_h), radius=12)
    canvas.paste(info_layer, (info_box_x, info_box_y), info_mask)

    # Information lines inside the info box (smaller equal sizes)
    info_inner_y = info_box_y + 10
    label_gap = 8
    def draw_info(label, value, at_y):
        inner_draw.text((info_box_x + 10, at_y), label, font=INFO_LABEL_FONT, fill=TEXT_WHITE)
        try:
            lw = inner_draw.textlength(label, font=INFO_LABEL_FONT)
        except Exception:
            lw = text_size(inner_draw, label, INFO_LABEL_FONT)[0]
        inner_draw.text((info_box_x + 10 + lw + label_gap, at_y), value, font=INFO_VALUE_FONT, fill=TEXT_WHITE)

    draw_info("STUDIO : ", (studio_name or "UNKNOWN").upper(), info_inner_y)
    draw_info("STATUS : ", (status or "UNKNOWN").upper(), info_inner_y + 32)  # Adjusted spacing for smaller font
    rating_display = f"{(score/10):.1f}/10" if score else "N/A"
    draw_info("RATING : ", rating_display, info_inner_y + 64)

    # --- Right character card (transparent, landscape, with bio) ---
    char_card_x = 850  # Slightly adjusted position
    char_card_y = 100
    char_card_w = 380  # Wider for landscape
    char_card_h = 220
    char_card_layer = Image.new("RGBA", (char_card_w, char_card_h), (CARD_BG[0], CARD_BG[1], CARD_BG[2], CARD_ALPHA))
    char_mask = rounded_rectangle_mask((char_card_w, char_card_h), radius=18)
    canvas.paste(char_card_layer, (char_card_x, char_card_y), char_mask)

    # Character image box inside char card (landscape crop)
    char_img_w = 360
    char_img_h = 120
    char_img_x = char_card_x + 10
    char_img_y = char_card_y + 10
    char_img = None
    # Try char_img_url first, then poster_url
    urls_to_try = [char_img_url, poster_url]
    for url in urls_to_try:
        if url:
            raw = download_image(url)
            if raw:
                char_img = resize_cover_to_fill(raw, char_img_w, char_img_h)
                break
    if char_img is None:
        # placeholder fill
        char_img = Image.new("RGBA", (char_img_w, char_img_h), PLACEHOLDER_BG)
        dd = ImageDraw.Draw(char_img)
        s = "NO IMAGE"
        tw, th = text_size(dd, s, CHAR_NAME_FONT)
        dd.text(((char_img_w-tw)//2, (char_img_h-th)//2), s, font=CHAR_NAME_FONT, fill=TEXT_WHITE)

    # Paste char image
    canvas.paste(char_img, (char_img_x, char_img_y), char_img if char_img.mode=="RGBA" else None)

    # Character name below image
    char_name_y = char_img_y + char_img_h + 10
    inner_draw.text((char_card_x + 20, char_name_y), char_name, font=CHAR_NAME_FONT, fill=TEXT_WHITE)

    # Character bio below name
    char_bio_y = char_name_y + 40
    char_bio_max_w = char_card_w - 40
    char_desc_lines = wrap_text_to_width(char_desc_excerpt, CHAR_DESC_FONT, char_bio_max_w, inner_draw)
    line_h = CHAR_DESC_FONT.size + 2
    for idx, ln in enumerate(char_desc_lines[:3]):  # Limit lines
        inner_draw.text((char_card_x + 20, char_bio_y + idx * line_h), ln, font=CHAR_DESC_FONT, fill=TEXT_GREY)

    # --- Synopsis card (bottom-right, transparent) ---
    syn_x = 850
    syn_y = 340  # Adjusted to below char card
    syn_w = 380
    syn_h = 300  # Slightly taller for more text
    syn_layer = Image.new("RGBA", (syn_w, syn_h), (CARD_BG[0], CARD_BG[1], CARD_BG[2], CARD_ALPHA))
    syn_mask = rounded_rectangle_mask((syn_w, syn_h), radius=18)
    canvas.paste(syn_layer, (syn_x, syn_y), syn_mask)
    # Title "SYNOPSIS"
    inner_draw.text((syn_x + 18, syn_y + 18), "SYNOPSIS", font=OVERVIEW_TITLE_FONT, fill=TEXT_WHITE)
    # Description wrap
    desc_max_w = syn_w - 36
    desc_lines = wrap_text_to_width(desc_excerpt, CHAR_DESC_FONT, desc_max_w, inner_draw)
    desc_start_y = syn_y + 60  # Adjusted
    line_h = CHAR_DESC_FONT.size + 4 if hasattr(CHAR_DESC_FONT, "size") else 20
    for idx, ln in enumerate(desc_lines[:8]):  # More lines
        inner_draw.text((syn_x + 18, desc_start_y + idx * (line_h)), ln, font=CHAR_DESC_FONT, fill=TEXT_GREY)

    # Finalize: convert to RGB PNG BytesIO
    output = BytesIO()
    canvas.convert("RGB").save(output, format="PNG", quality=95)
    output.seek(0)
    return output

# ---------- AniList helper ----------
ANILIST_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    title { romaji english }
    coverImage { extraLarge large medium color }
    averageScore
    genres
    description
    status
    season
    seasonYear
    studios(isMain: true) { nodes { name } }
    characters {
      nodes {
        name { full }
        description
        image { large }
      }
    }
  }
}
"""

def fetch_anime_from_anilist(name, timeout=15):
    try:
        r = requests.post("https://graphql.anilist.co", json={"query":ANILIST_QUERY, "variables":{"search":name}}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("data", {}).get("Media")
    except Exception as e:
        logger.warning(f"AniList fetch failed for '{name}': {e}")
        return None

# ---------- Telegram Bot ----------
def run_telegram_bot():
    if telebot is None:
        logger.error("telebot package not installed. Install pyTelegramBotAPI or set NO_BOT=1")
        return

    bot = telebot.TeleBot(API_TOKEN, parse_mode=None)

    @bot.message_handler(commands=['start'])
    def cmd_start(m):
        bot.reply_to(m, "🎬 Anime Mayhem Thumbnail Generator\nSend `/thumb <anime name>` or just type anime name.")

    @bot.message_handler(commands=['thumb'])
    def cmd_thumb(m):
        text = m.text or ""
        query = text.replace("/thumb", "").strip()
        if not query:
            bot.reply_to(m, "❌ Usage: /thumb Spy x Family")
            return
        # Inform user
        try:
            bot.send_chat_action(m.chat.id, "upload_photo")
        except Exception:
            pass

        # fetch AniList
        anime = fetch_anime_from_anilist(query)
        if not anime:
            bot.reply_to(m, f"❌ Couldn't find anime: {query}\nTrying with local sample image.")
            # fallback generate with minimal info
            anime = {"title":{"english":query},"coverImage":{"extraLarge":None},"averageScore":None,"genres":[],"description":"No description available","status":"UNKNOWN"}
            img_buf = generate_thumbnail(anime, prefer_local_bg=True)
        else:
            img_buf = generate_thumbnail(anime)

        # send
        try:
            bot.send_photo(m.chat.id, img_buf, caption=f"🎬 {anime.get('title',{}).get('english') or anime.get('title',{}).get('romaji')}", timeout=120)
        except Exception as e:
            logger.exception("Failed to send photo: %s", e)
            bot.reply_to(m, "❌ Failed to send generated image. Try again later.")

    @bot.message_handler(func=lambda message: True)
    def catch_all(m):
        # treat plain text as a request
        text = m.text.strip() if m.text else ""
        if len(text) > 2:
            # reuse cmd handler
            m.text = f"/thumb {text}"
            cmd_thumb(m)
        else:
            bot.reply_to(m, "Send `/thumb <anime name>`")

    logger.info("Starting Telegram Bot polling (CTRL+C to stop)...")
    bot.infinity_polling()


# ---------- CLI quick test ----------
def cli_test():
    print("CLI test: generate thumbnail for 'SPY x FAMILY' using local background if available.")
    sample = fetch_anime_from_anilist("Spy x Family") or {
        "title": {"english":"Spy x Family", "romaji":"Spy x Family"},
        "coverImage": {"extraLarge": None},
        "averageScore": 85,
        "genres": ["Action","Comedy","Slice of Life"],
        "description":"A spy, an assassin and a telepath — a found family that must pretend to be normal.",
        "status":"FINISHED",
        "season":"SPRING",
        "seasonYear":2022,
        "studios":{"nodes":[{"name":"WIT STUDIO"}]},
        "characters": {"nodes": [{"name": {"full": "Anya Forger"}, "description": "Anya is a young girl who can read people's thoughts and is the only one who escaped from an experimental human test subject dubbed '007'. She likes spy missions and thinks anything involving 'secrets' and 'missions' are exciting.", "image": {"large": None}}]}
    }
    buf = generate_thumbnail(sample, prefer_local_bg=True)
    out_path = "anime_mayhem_thumb_test.png"
    with open(out_path, "wb") as f:
        f.write(buf.getbuffer())
    print(f"Saved test thumbnail to {out_path}. Open it to inspect. Fonts folder used: {FONTS_DIR}")

# ---------- Main ----------
if __name__ == "__main__":
    # If first arg is "test", run cli_test()
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("test","local"):
        cli_test()
        sys.exit(0)

    # If NO_BOT env or telebot not installed, offer CLI test
    if NO_BOT or telebot is None:
        logger.info("NO_BOT set or telebot missing. Running CLI test instead.")
        cli_test()
        sys.exit(0)

    # Run telegram bot
    run_telegram_bot()
