# thumbnail_bot.py - Final AnimeFlicker Exact Match Generator
import telebot
import requests
import os
import math
from PIL import Image, ImageDraw, ImageFont
import textwrap
from io import BytesIO

# ⚠️ YAHAN APNA NAYA TOKEN DAALNA (purana wala mat daalna)
API_TOKEN = "7597391690:AAFdUlJBP46IJNvkaM6vIhW6J1fbmUTlkjA"  # ← ABHI KE LIYE RAKH RAHA, PAR NAYA BANA KE CHANGE KAR DENA
bot = telebot.TeleBot(API_TOKEN)

# Fonts (fonts folder bana ke daal do)
FONTS_DIR = "fonts"
try:
    TITLE_FONT = ImageFont.truetype(os.path.join(FONTS_DIR, "BebasNeue-Regular.ttf"), 90)
    BOLD_FONT = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Bold.ttf"), 50)
    MEDIUM_FONT = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Medium.ttf"), 40)
    REG_FONT = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Regular.ttf"), 34)
    GENRE_FONT = ImageFont.truetype(os.path.join(FONTS_DIR, "coolvetica rg.otf"), 40)
except:
    TITLE_FONT = BOLD_FONT = MEDIUM_FONT = REG_FONT = GENRE_FONT = ImageFont.load_default()

BG_PATH = "hex_bg.png"
CANVAS_WIDTH, CANVAS_HEIGHT = 1280, 720

# Colors exact from example
BG_COLOR = (20, 25, 40)
HEX_OUTLINE = (35, 40, 60)  # Darker outline
DEC_HEX_FILL = (112, 124, 140)
TEXT_COLOR = (255, 255, 255)
SUBTEXT_COLOR = (220, 220, 220)
GENRE_COLOR = (170, 170, 255)
RATING_BG = (0, 100, 255)
BUTTON_LEFT = (30, 40, 70)
BUTTON_RIGHT = (0, 110, 255)
LOGO_COLOR = (255, 255, 255)

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

def create_hexagon_mask(size):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    center = (size[0] // 2, size[1] // 2)
    radius = min(size) // 2 - 10
    draw_regular_polygon(draw, center, radius, fill=255)
    return mask

def generate_hex_background():
    if os.path.exists(BG_PATH):
        return Image.open(BG_PATH).convert("RGBA")
    
    img = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Exact hex grid from example
    for x in range(0, 1300, 120):
        for y in range(0, 800, 104):
            center = (x + 60, y + 52)
            draw_regular_polygon(draw, center, 58, outline=HEX_OUTLINE, width=2)
    
    # Exact decorative hex positions and scales from XML (adjusted for 1280x720)
    dec_positions = [
        # From XML: locations and scales
        {"loc": (1509.906494, 1101.221924), "scale": 2.195},
        {"loc": (1315.748169, 761.138306), "scale": 2.195},
        {"loc": (1511.625122, 421.910461), "scale": 2.195},
        {"loc": (1707.117798, 761.138306), "scale": 2.195},
        {"loc": (1118.221436, 421.910461), "scale": 2.195},
        {"loc": (1315.748169, 167.000000), "scale": 1.360},
        {"loc": (1801.112549, 480.854706), "scale": 1.045},
        {"loc": (1014.503906, 710.656128), "scale": 1.141},
        {"loc": (1606.591919, 141.915283), "scale": 1.040}
    ]
    base_radius = 100
    for pos in dec_positions:
        cx, cy = pos["loc"]
        scale = pos["scale"]
        adjusted_cx = (cx / 1920) * CANVAS_WIDTH
        adjusted_cy = (cy / 1080) * CANVAS_HEIGHT
        radius = base_radius * scale * (CANVAS_HEIGHT / 1080)
        if 0 < adjusted_cx < CANVAS_WIDTH and 0 < adjusted_cy < CANVAS_HEIGHT:
            draw_regular_polygon(draw, (adjusted_cx, adjusted_cy), radius * 0.5, fill=DEC_HEX_FILL)  # Scaled down
    
    img.save(BG_PATH)
    return img

def wrap_text(text, font, max_width):
    lines = textwrap.wrap(text, width=max_width // (font.getlength(' ') * 1.5))  # Approximate char width
    return lines

def generate_thumbnail(anime):
    title = anime['title']['english'] or anime['title']['romaji']
    poster_url = anime['coverImage']['extraLarge']
    score = anime['averageScore']
    genres = anime['genres'][:4]
    desc = (anime['description'] or "").replace("<br>", " ").replace("<i>", "").replace("</i>", "")
    desc = " ".join(desc.split()[:65]) + "..."
    
    # Background
    bg = generate_hex_background()
    canvas = bg.copy()
    draw = ImageDraw.Draw(canvas)
    
    # Logo exact
    draw.text((80, 10), "ANIME FLICKER", font=MEDIUM_FONT, fill=LOGO_COLOR)
    
    # Poster hex exact
    poster_resp = requests.get(poster_url)
    poster = Image.open(BytesIO(poster_resp.content)).convert("RGBA")
    poster = poster.resize((440, 620))
    mask = create_hexagon_mask((440, 620))
    hex_poster = Image.new("RGBA", (440, 620), (0,0,0,0))
    hex_poster.paste(poster, (0,0), mask)
    canvas.paste(hex_poster, (780, 50), hex_poster)
    
    # Title exact position and upper
    draw.text((80, 70), title.upper(), font=TITLE_FONT, fill=TEXT_COLOR)
    
    # Rating exact
    if score:
        rating = f"{score/10:.1f}+ Rating"
        draw.rounded_rectangle((80, 190, 340, 250), radius=20, fill=RATING_BG)
        draw.text((100, 200), rating, font=MEDIUM_FONT, fill=TEXT_COLOR)
    
    # Genres exact: " • " join, upper
    genre_text = " • ".join(genres).upper()
    draw.text((80, 290), genre_text, font=REG_FONT, fill=GENRE_COLOR)
    
    # Description exact wrap and position
    lines = wrap_text(desc, REG_FONT, 52)
    y = 360
    for line in lines:
        draw.text((80, y), line, font=REG_FONT, fill=SUBTEXT_COLOR)
        y += 44
    
    # Buttons exact
    draw.rounded_rectangle((80, 580, 320, 660), radius=15, fill=BUTTON_LEFT)
    draw.text((110, 600), "DOWNLOAD", font=BOLD_FONT, fill=TEXT_COLOR)
    draw.rounded_rectangle((350, 580, 590, 660), radius=15, fill=BUTTON_RIGHT)
    draw.text((400, 600), "JOIN NOW", font=BOLD_FONT, fill=TEXT_COLOR)
    
    # Final
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
    bot.reply_to(msg, "Thumbnail ban raha hai... 10 sec ruk")
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
        bot.send_photo(msg.chat.id, img,
                      caption=f"{resp['title']['english'] or resp['title']['romaji']}\n@YourChannelHere")
    except Exception as e:
        bot.reply_to(msg, f"Error: {e}\nBot restart kar ya font daal")

print("Bot chal gaya!")
bot.infinity_polling()