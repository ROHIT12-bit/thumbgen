# thumbnail_bot.py - Final AnimeFlicker Exact Match Generator
import telebot
import requests
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
from io import BytesIO

# ⚠️ YAHAN APNA NAYA TOKEN DAALNA (purana wala mat daalna)
API_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(API_TOKEN)

# Fonts
FONTS_DIR = "fonts"
try:
    # Increased sizes again per user request
    TITLE_FONT = ImageFont.truetype(os.path.join(FONTS_DIR, "BebasNeue-Regular.ttf"), 160)
    BOLD_FONT = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Bold.ttf"), 42)
    MEDIUM_FONT = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Medium.ttf"), 36)
    REG_FONT = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Regular.ttf"), 30)
    GENRE_FONT = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Bold.ttf"), 38)
except:
    TITLE_FONT = ImageFont.load_default()
    BOLD_FONT = ImageFont.load_default()
    MEDIUM_FONT = ImageFont.load_default()
    REG_FONT = ImageFont.load_default()
    GENRE_FONT = ImageFont.load_default()

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

    # Background
    bg = generate_hex_background()
    canvas = bg.copy()
    draw = ImageDraw.Draw(canvas)

    # 1. Logo (Top Left)
    icon_x, icon_y = 50, 40
    sz = 18
    draw.polygon([(icon_x, icon_y+sz), (icon_x+sz, icon_y), (icon_x+2*sz, icon_y+sz), (icon_x+sz, icon_y+2*sz)], outline=LOGO_COLOR, width=3)
    draw.polygon([(icon_x+10, icon_y+sz), (icon_x+sz+10, icon_y), (icon_x+2*sz+10, icon_y+sz), (icon_x+sz+10, icon_y+2*sz)], outline=LOGO_COLOR, width=3)
    draw.text((icon_x + 65, icon_y + 2), "ANIME FLICKER", font=LOGO_FONT, fill=LOGO_COLOR)

    # 2. Rating (Below Logo)
    if score:
        rating_text = f"{score/10:.1f}+ Rating"
        draw.text((50, 140), rating_text, font=REG_FONT, fill=TEXT_COLOR)

    # 3. Title (Large, Below Rating)
    title_lines = wrap_text(title.upper(), TITLE_FONT, 700)
    title_y = 180
    for line in title_lines[:2]:
        draw.text((50, title_y), line, font=TITLE_FONT, fill=TEXT_COLOR)
        title_y += 140 # Height

    # 4. Genres (Below Title)
    genre_text = ", ".join(genres).upper()
    draw.text((50, title_y + 10), genre_text, font=GENRE_FONT, fill=GENRE_COLOR)

    # 5. Description (Below Genres)
    desc_y = title_y + 60
    desc_lines = wrap_text(desc, REG_FONT, 580)
    for line in desc_lines[:4]: # Fewer lines because text is bigger
        draw.text((50, desc_y), line, font=REG_FONT, fill=SUBTEXT_COLOR)
        desc_y += 42

    # 6. Buttons (Bottom Left)
    btn_y = 620
    btn_width = 210
    btn_height = 65

    # Button 1: DOWNLOAD
    draw.rounded_rectangle((50, btn_y, 50 + btn_width, btn_y + btn_height), radius=12, fill=BUTTON_BG)
    text_w = BOLD_FONT.getlength("DOWNLOAD")
    text_x = 50 + (btn_width - text_w) / 2
    draw.text((text_x, btn_y + 12), "DOWNLOAD", font=BOLD_FONT, fill=TEXT_COLOR)

    # Button 2: JOIN NOW
    btn2_x = 50 + btn_width + 40
    draw.rounded_rectangle((btn2_x, btn_y, btn2_x + btn_width, btn_y + btn_height), radius=12, fill=BUTTON_BG)
    text_w = BOLD_FONT.getlength("JOIN NOW")
    text_x = btn2_x + (btn_width - text_w) / 2
    draw.text((text_x, btn_y + 12), "JOIN NOW", font=BOLD_FONT, fill=TEXT_COLOR)


    # 7. Right Side Honeycomb Poster
    poster_resp = requests.get(poster_url)
    poster = Image.open(BytesIO(poster_resp.content)).convert("RGBA")

    start_x = 550
    width = CANVAS_WIDTH - start_x + 100
    height = CANVAS_HEIGHT

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
