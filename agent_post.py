"""
PeakSync — Daily Image Carousel Generator
---------------------------------
Each run:
  - Fetches a portrait-oriented background photo from Pexels
  - Generates multiple static image slides (.png) with text overlays
  - Outputs a text file with the matching caption for manual posting

Requirements:
    pip install requests python-dotenv pillow
"""

import os
import json
import random
import requests
import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Config ────────────────────────────────────────────────────────────────────

PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
OUTPUT_DIR     = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Standard font path on Ubuntu runners (Change locally if testing on Mac/Windows)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = "Arial.ttf"  # Fallback for local testing environments

# ── Content library ───────────────────────────────────────────────────────────
# Each entry now splits the overlay text into a list of strings.
# Each string in the list represents an individual slide in the carousel sequence.
CONTENT_LIBRARY = [
    {
        "slides": [
            "MYTH:\nTrain at maximum\nintensity every day.",
            "FACT:\nYour luteal phase\ndemands deep rest."
        ],
        "hooks": [
            "Most women push hardest when they feel like it. Smart women push hardest when their hormones say go. 🧠",
            "Did you know your muscles are literally stronger this week? Here's why… 🧬",
            "Follicular phase = your body's performance window. Use it. 💪",
        ],
        "caption_body": "During your follicular phase, estrogen boosts muscle repair, pain tolerance, and recovery speed.\nThat's your window. Every week it comes around — most women never know it exists.",
        "cta": "👇 Are you already training with your cycle? Drop a 💪 if yes",
        "pexels_query": "abstract texture minimalist"
    },
    {
        "slides": [
            "MYTH:\nPMS cravings are\na failure of discipline.",
            "FACT:\nYour dropping serotonin\nis demanding fuel."
        ],
        "hooks": [
            "You don't lack discipline. You lack information. 🍫",
            "Why do you crave sugar and carbs before your period? The answer is hormonal — not personal. 🔬",
            "PMS cravings aren't weakness. They're biology. Here's proof. 🧪",
        ],
        "caption_body": "The week before your period, serotonin drops and your body demands more fuel.\nThat craving isn't a character flaw — it's your body asking for help in the only language it knows.",
        "cta": "👇 What's your go-to craving before your period? Drop it below",
        "pexels_query": "calm organic background textures"
    },
    {
        "slides": [
            "MYTH:\nLow energy during your\ncycle means laziness.",
            "FACT:\nEstrogen and iron crash.\nIt's biological data."
        ],
        "hooks": [
            "Your body is not broken. It's just in a different phase. 🔄",
            "Ever feel exhausted during your period and wonder why? Here's the real reason… 😴",
            "Period fatigue is real. And it has nothing to do with motivation. 💙",
        ],
        "caption_body": "Estrogen and progesterone both crash during menstruation. Iron dips. Energy follows.\nThis isn't the week to go hard — it's the week to go smart and come back stronger.",
        "cta": "👇 Do you rest during your period or push through? Be honest 👇",
        "pexels_query": "moody dark abstract wall"
    }
]

APP_TEASER = "App coming soon — follow to be first in. 🌸"
HASHTAGS   = "#PeakSync #CycleSyncing #BodyLiteracy #KnowYourBody #CycleAwareness #HormoneHealth #WomensHealth #TrainSmart"


# ── Step 1: Pick Content ──────────────────────────────────────────────────────

def pick_content() -> dict:
    index = datetime.date.today().toordinal() % len(CONTENT_LIBRARY)
    topic = CONTENT_LIBRARY[index]
    hook  = random.choice(topic["hooks"])

    caption = f"""{hook}\n\n{topic['caption_body']}\n\n{topic['cta']}\n\n{APP_TEASER}\n\n{HASHTAGS}"""

    print(f"✅ Picked Topic: {topic['slides'][0].splitlines()[0]}")
    return {
        "slides": topic["slides"],
        "caption": caption,
        "pexels_query": topic["pexels_query"]
    }


# ── Step 2: Fetch Pexels Image ────────────────────────────────────────────────

def fetch_pexels_image(query: str) -> str:
    """ Fetches a high-quality portrait image from Pexels API """
    resp = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "orientation": "portrait", "per_page": 10},
        timeout=15,
    )
    resp.raise_for_status()
    photos = resp.json().get("photos", [])
    if not photos:
        raise ValueError(f"No Pexels images found for query: {query}")
    
    # Pick randomly from top entries to ensure variety across runs
    photo = random.choice(photos[:5])
    # Fetch the large/portrait-sized version URL
    image_url = photo["src"]["large2x"]
    
    # Download directly into memory
    img_data = requests.get(image_url, timeout=30).content
    print(f"✅ Background texture selected from Pexels")
    return img_data


# ── Step 3: Draw Typography & Content Text overlays ─────────────────────────

def generate_carousel_slides(image_bytes: bytes, slides_text: list[str]) -> list[str]:
    """ Overlays text onto the fetched image and cuts them out as clean slides """
    date_str = datetime.date.today().isoformat()
    generated_paths = []

    # Target social canvas size (Standard 1080x1920 Instagram Stories/Reels aspect)
    target_w, target_h = 1080, 1920
    
    # Load base image safely from the downloaded bytes data stream
    import io
    base_img = Image.open(io.BytesIO(image_bytes))
    
    # Resize and crop to center background perfectly at 1080x1920
    base_img = base_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    for idx, text in enumerate(slides_text):
        # Create a clean copy of the base background asset for each separate slide frame
        slide_img = base_img.copy()
        draw = ImageDraw.Draw(slide_img, "RGBA")
        
        # Initialize text styling fonts
        try:
            font = ImageFont.truetype(FONT_PATH, size=64)
        except IOError:
            font = ImageFont.load_default()

        # Add a subtle transparent overlay layer across the entire image to step up legibility
        draw.rectangle([0, 0, target_w, target_h], fill=(0, 0, 0, 80))

        # Calculate bounding box positions to center multi-line text blocks manually
        lines = text.splitlines()
        total_text_height = sum([draw.textbbox((0, 0), line, font=font)[3] for line in lines]) + (len(lines) * 20)
        
        current_y = (target_h - total_text_height) // 2
        
        for line in lines:
            # Measure specific line widths to guarantee horizontal alignment
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1]
            
            x_pos = (target_w - line_w) // 2
            
            # Write text drop shadow line for better reading contrast on textured photos
            draw.text((x_pos + 3, current_y + 3), line, font=font, fill=(0, 0, 0, 180))
            # Main font text write
            draw.text((x_pos, current_y), line, font=font, fill=(255, 255, 255, 255))
            
            current_y += line_h + 35 # Row padding height modifier

        # Export completed frame directly to local directory path
        slide_filename = OUTPUT_DIR / f"slide_{date_str}_{idx + 1}.png"
        slide_img.save(slide_filename, "PNG")
        generated_paths.append(str(slide_filename))
        print(f"   ↳ Slide {idx + 1} generated successfully: {slide_filename.name}")

    return generated_paths


# ── Step 4: Output Context Script ─────────────────────────────────────────────

def save_caption(caption: str) -> str:
    date_str = datetime.date.today().isoformat()
    path = OUTPUT_DIR / f"caption_{date_str}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(caption)
    return str(path)


def run():
    print(f"\n🌸 PeakSync Content Engine — {datetime.date.today()}\n{'─'*45}")
    
    content = pick_content()
    image_raw_bytes = fetch_pexels_image(content["pexels_query"])
    slide_files = generate_carousel_slides(image_raw_bytes, content["slides"])
    caption_path = save_caption(content["caption"])

    print(f"\n┌──────────────────────────────────────────────────┐")
    print(f"│  ✅ Carousel Assets Export Complete               │")
    print(f"├──────────────────────────────────────────────────┤")
    for s_file in slide_files:
        print(f"│  📷 {Path(s_file).name:<44} │")
    print(f"│  📝 {Path(caption_path).name:<44} │")
    print(f"└──────────────────────────────────────────────────┘\n")


if __name__ == "__main__":
    run()