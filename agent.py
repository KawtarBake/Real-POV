"""
PeakSync — Daily Reel Generator (Nutrition Edition)
--------------------------------------------------
Each run randomly picks:
  - Overlay style: C (bold white + pink accent word) or F (elegant serif quote)
  - Caption hook: style 1 (direct/science), 2 (question), or 3 (short/punchy)

Outputs: video file + caption text file — ready to post manually on Instagram.

Requirements:
    pip install requests python-dotenv

System deps (pre-installed on GitHub Actions ubuntu runners):
    ffmpeg

Environment variables (GitHub Secrets):
    PEXELS_API_KEY
"""

import os
import json
import random
import requests
import subprocess
import datetime
import tempfile
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Config ────────────────────────────────────────────────────────────────────

PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
REEL_DURATION  = 6      # seconds of source to use (becomes ~4.6s after 1.3x speed)
VIDEO_SPEED    = 1.3
OUTPUT_DIR     = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"

# ── Content library ───────────────────────────────────────────────────────────
# Rebuilt to focus entirely on cycle-synced nutrition and feminine biochemistry.
# Use | to mark the ACCENT word(s) for style C. Style F wraps everything in quotes.

CONTENT_LIBRARY = [
    {
        "overlay_text": "POV: You stop fighting\nyour biology and feed\nyour |luteal phase| cravings",
        "hooks": [
            "Your pre-period sugar cravings aren't a lack of willpower. They are simple biology. 🍠",
            "What if feeding your body the right complex carbs before your period could eliminate PMS completely? 🧠",
            "Stop trying to starve your luteal phase. Your metabolism is running at a different speed this week. 🥑",
        ],
        "caption_body": "During the luteal phase, your progesterone peaks, raising your basal body temperature and naturally burning more resting calories. Your body is physically demanding more fuel.\n\nWhen you deny this energy spike, your brain panics and sends emergency signals for fast-burning sugars (cue the chocolate binge). Swapping to slow-burning, complex carbs like sweet potatoes or squash stabilizes blood sugar and stops the cravings before they start.",
        "cta": "👇 Do you struggle more with sugar cravings or mood swings before your period? Let's talk below!",
        "pexels_query": "woman kitchen cozy morning tea",
    },
    {
        "overlay_text": "POV: You stop drinking\niced coffee on an\n|empty stomach| Day 1",
        "hooks": [
            "If you are drinking coffee first thing on your period, you are accidentally spiking your cramps. ☕",
            "Your menstrual phase energy crash isn't just because of your period—it's your morning routine. 🩸",
            "How you fuel the first 60 minutes of your day dictates your entire period experience. 🌿",
        ],
        "caption_body": "On Day 1 of your cycle, estrogen and progesterone hit rock bottom. Pouring caffeine into an empty stomach sends an immediate distress signal to your adrenals, spiking cortisol and inducing systemic inflammation—which directly tightens uterine muscles and worsens cramping.\n\nAlways layer a baseline of protein and warm, mineral-rich fuel (like eggs, avocado, or warm bone broth) before your morning caffeine to protect your hormonal baseline.",
        "cta": "👇 Save this to remember before your next Day 1! 💾",
        "pexels_query": "woman cozy bed morning window light",
    },
    {
        "overlay_text": "POV: You realize your\nheavy periods mean your\n|liver| needs an assist",
        "hooks": [
            "Severe cramping, heavy bleeding, and stubborn breakouts? Your liver might be overwhelmed. 🥦",
            "Estrogen is meant to be used and cleared. Here is what happens when it gets stuck. 🔬",
            "The missing link in your period health isn't in your ovaries—it's in your digestive tract. 🥬",
        ],
        "caption_body": "Around ovulation, estrogen climbs to a massive physiological peak. But once that hormone completes its job, your liver is fully responsible for filtering, breaking down, and excreting the excess safely.\n\nIf your detoxification pathways are sluggish, that used estrogen recirculates, leading to 'estrogen dominance'—the root cause of heavy bleeds and cyclical acne. Cruciferous vegetables contain indole-3-carbinol, which chemically unlocks your liver's filtering efficiency.",
        "cta": "👇 What's your go-to green veggie? Drop it below and let's swap recipes! 👇",
        "pexels_query": "fresh green vegetables prep cooking rustic",
    },
    {
        "overlay_text": "POV: You stop counting\ncalories and start eating\nfor your |hormone| cycle",
        "hooks": [
            "A static 1,200 or 1,800 calorie deficit is designed for a male hormonal blueprint, not yours. 📊",
            "Why your strict diet works beautifully for two weeks, then completely fails you the next two. 🔄",
            "Your metabolism is dynamic, not a fixed daily math equation. 🧠",
        ],
        "caption_body": "A woman's metabolism shifts dramatically across 28 days. In your follicular phase, you are highly insulin-sensitive and process clean fuel with incredible metabolic efficiency. In your luteal phase, your cortisol sensitivity climbs, making aggressive deficits feel like a biological threat.\n\nWhen you sync your fuel layout to these shifts, your body stops storing emergency fat and starts building lean, clear energy.",
        "cta": "👇 Are you still tracking metrics blind, or are you eating with your cycle yet?",
        "pexels_query": "woman prep healthy salad bowl kitchen",
    },
    {
        "overlay_text": "POV: You double your\n|iron absorption| \n during your period \n with one hack",
        "hooks": [
            "Eating all the spinach in the world won't fix your period fatigue if you miss this one step. 🧬",
            "Why your plant-based iron isn't absorbing, and exactly how to fix it instantly. 🍊",
            "The precise biochemical pairing your body needs to survive your bleeding window. 🩸",
        ],
        "caption_body": "The blood loss during your menstrual phase significantly depletes your systemic iron and ferritin levels, leading to that distinct, heavy exhaustion. However, plant-based iron (non-heme iron found in lentils, beans, and leafy greens) has a low biological absorption rate on its own.\n\nBy simply pairing your iron sources with a high-quality Vitamin C catalyst (like citrus fruits, bell peppers, or a squeeze of fresh lemon juice), you chemically alter the iron molecule, making it highly bioavailable for your body to absorb.",
        "cta": "👇 Have you noticed your energy crashing on Day 2? Let me know below!",
        "pexels_query": "aesthetic breakfast layout citrus fruits",
    },
]

APP_TEASER = "App coming soon — follow to be first in. 🌸"
HASHTAGS   = "#PeakSync #CycleSyncing #HormoneHealth #NutritionForWomen #PeriodWellness #BiohackingWomen #EatForYourCycle"


# ── Step 1: Pick content + random style ──────────────────────────────────────

def pick_content() -> dict:
    index   = datetime.date.today().toordinal() % len(CONTENT_LIBRARY)
    topic   = CONTENT_LIBRARY[index]
    hook    = random.choice(topic["hooks"])
    style   = random.choice(["C", "F"])

    caption = f"""{hook}

{topic['caption_body']}

{topic['cta']}

{APP_TEASER}

{HASHTAGS}"""

    print(f"✅ Topic  : {topic['overlay_text'].splitlines()[0]}")
    print(f"✅ Style  : {style}")
    print(f"✅ Hook   : {hook[:60]}...")

    return {
        "overlay_text": topic["overlay_text"],
        "caption":      caption,
        "pexels_query": topic["pexels_query"],
        "style":        style,
    }


# ── Step 2: Fetch Pexels video ────────────────────────────────────────────────

def fetch_pexels_video(query: str) -> str:
    resp = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 10},
        timeout=15,
    )
    resp.raise_for_status()
    videos = resp.json().get("videos", [])
    if not videos:
        raise ValueError(f"No Pexels videos found for: {query}")

    video = random.choice(videos[:5])
    files = sorted(
        [f for f in video["video_files"] if f.get("quality") in ("hd", "sd")],
        key=lambda f: f.get("width", 0), reverse=True,
    ) or video["video_files"]

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False, dir=OUTPUT_DIR)
    with requests.get(files[0]["link"], stream=True, timeout=60) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            tmp.write(chunk)
    tmp.close()
    print(f"✅ Video downloaded")
    return tmp.name


# ── Step 3: Build FFmpeg overlay filters ─────────────────────────────────────

def build_style_F(lines: list[str]) -> list:
    """ Style F: elegant serif quote with semi-transparent line bounding boxes """
    font       = FONT_SERIF
    font_size  = 68
    line_h     = 90
    start_pct  = 0.55
    pad        = 25

    parts = []
    prev_label = "base"

    for i, line in enumerate(lines):
        next_label = f"t{i+1}" if i < len(lines) - 1 else "out"
        y_expr = f"h*{start_pct:.2f}+{i * line_h}"
        clean_line = line.replace("|", "")  # Remove style C tokens if mixed up
        esc = clean_line.replace("\\", "\\\\").replace("'", "\u2019").replace(":", "\\:")
        parts.append(
            f"[{prev_label}]drawtext="
            f"fontfile={font}:"
            f"text='{esc}':"
            f"fontcolor=white:"
            f"fontsize={font_size}:"
            f"x=(w-text_w)/2:"
            f"y={y_expr}:"
            f"box=1:"
            f"boxcolor=black@0.50:"
            f"boxborderw={pad}"
            f"[{next_label}]"
        )
        prev_label = next_label

    return parts


def build_style_C(lines: list[str]) -> list:
    """ Style C: Bold modern layout featuring a pink contrast accent highlight word """
    font       = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if not os.path.exists(font):
        font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        
    font_size  = 72
    line_h     = 100
    start_pct  = 0.50
    
    parts = []
    prev_label = "base"
    
    for i, line in enumerate(lines):
        next_label = f"t{i+1}" if i < len(lines) - 1 else "out"
        y_expr = f"h*{start_pct:.2f}+{i * line_h}"
        
        # Check if line contains a highlighted accent bounded by pipes e.g. |estrogen|
        if "|" in line and line.count("|") == 2:
            before, mid, after = line.split("|")
            esc_mid = mid.replace("\\", "\\\\").replace("'", "\u2019").replace(":", "\\:")
            
            # Draw standard text segment, then append pink highlighted segment inline
            # For simplicity across dynamic lines, style C tints the entire line text pink if flagged
            font_color = "0xFFB6C1" # Light Pink accent
            clean_text = mid
        else:
            font_color = "white"
            clean_text = line.replace("|", "")
            
        esc = clean_text.replace("\\", "\\\\").replace("'", "\u2019").replace(":", "\\:")
        parts.append(
            f"[{prev_label}]drawtext="
            f"fontfile={font}:"
            f"text='{esc}':"
            f"fontcolor={font_color}:"
            f"fontsize={font_size}:"
            f"x=(w-text_w)/2:"
            f"y={y_expr}:"
            f"shadowcolor=black@0.40:"
            f"shadowx=4:shadowy=4"
            f"[{next_label}]"
        )
        prev_label = next_label
        
    return parts


# ── Step 4: Create reel with FFmpeg ──────────────────────────────────────────

def create_reel(input_path: str, overlay_text: str, style: str) -> str:
    date_str    = datetime.date.today().isoformat()
    output_path = str(OUTPUT_DIR / f"reel_{date_str}_{style}.mp4")

    raw_lines = overlay_text.strip().splitlines()

    # Base processing: speed up + scale to 9:16
    base_filter = (
        f"[0:v]setpts=PTS/{VIDEO_SPEED},"
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920"
        f"[base]"
    )

    # Dynamic styling route switch
    if style == "C":
        text_parts = build_style_C(raw_lines)
    else:
        text_parts = build_style_F(raw_lines)

    # Full filter_complex configuration payload
    filter_complex = base_filter + ";" + ";".join(text_parts)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-t", str(REEL_DURATION),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "0:a?",
        "-af", f"atempo={VIDEO_SPEED}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg error:\n", result.stderr[-1000:])
        raise RuntimeError("FFmpeg failed")

    os.unlink(input_path)
    print(f"✅ Reel created ({style} style, {VIDEO_SPEED}x speed): {output_path}")
    return output_path


# ── Step 5: Save caption ──────────────────────────────────────────────────────

def save_caption(caption: str, style: str) -> str:
    date_str     = datetime.date.today().isoformat()
    path         = str(OUTPUT_DIR / f"caption_{date_str}_{style}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(caption)
    print(f"✅ Caption saved: {path}")
    return path


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print(f"\n🌸 PeakSync Reel Generator — {datetime.date.today()}\n{'─'*45}")

    content = pick_content()
    raw_video = fetch_pexels_video(content["pexels_query"])
    reel_path = create_reel(raw_video, content["overlay_text"], content["style"])
    caption_path = save_caption(content["caption"], content["style"])

    print(f"""
┌──────────────────────────────────────────────────┐
│  ✅ Ready to post manually on Instagram          │
│                                                  │
│  📹  {Path(reel_path).name:<44}│
│  📝  {Path(caption_path).name:<44}│
│                                                  │
│  → Download from GitHub Actions → Artifacts      │
└──────────────────────────────────────────────────┘""")

    with open(OUTPUT_DIR / "log.jsonl", "a") as f:
        f.write(json.dumps({
            "date":    str(datetime.date.today()),
            "style":   content["style"],
            "overlay": content["overlay_text"].splitlines()[0],
        }) + "\n")


if __name__ == "__main__":
    run()
