import asyncio
import os
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from reel_text_safe import assert_text_fits

W, H = 1080, 1920
FPS = 30
NAVY = (7, 17, 31)
CYAN = (56, 199, 255)
WHITE = (255, 255, 255)
ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT.parent
OUT = ROOT / "assets" / "posts"
BASE_URL = "https://v3b.fal.media/files/b/0aa333c1/GWDks7ssa4B-tu29F6lN1_SkrxWWS6.png"
PRODUCT = STUDIO / "pinterest" / "assets" / "pins" / "cap-01.png"
COVER = OUT / "reel-2026-07-21.png"
VIDEO = OUT / "reel-2026-07-21.mp4"

NARRATION = (
    "Blank caption box again? "
    "Stop rewriting the same book announcement every release day. "
    "The Caption Vault gives fantasy and LitRPG authors three hundred fifty ready lines. "
    "Pick a reader hook, chapter promo, Patreon line, or launch call to action. "
    "Save this before your next promo post."
)

BEATS = [
    (3, "BLANK CAPTION BOX AGAIN?", "A concrete fix for fantasy authors"),
    (5, "STOP REWRITING THE SAME POST", "Release day should not start from zero"),
    (6, "350 READY CAPTION LINES", "Built for fantasy and LitRPG authors"),
    (5, "HOOKS. CHAPTERS. PATREON. LAUNCHES.", "Pick a category, adapt, and post"),
    (5, "SAVE THIS FOR YOUR NEXT PROMO", "FANTASY AUTHOR CAPTION VAULT  |  $12"),
]


def font(size, bold=True):
    paths = [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"] if bold else [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"]
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_centered(draw, text, y, size, color, max_w=920, line_h=None):
    if line_h is None:
        line_h = size + 18
    lines, fnt, actual_size = assert_text_fits(draw, text, size, y, line_h, max_w=max_w)
    for line in lines:
        width = draw.textlength(line, font=fnt)
        draw.text(((W - width) / 2, y), line, font=fnt, fill=color)
        y += line_h
    return y, actual_size


def prepare_background(image, use_product=False):
    if use_product:
        image = image.crop((0, 0, image.width, int(image.height * 0.9)))
    image = ImageOps.fit(image.convert("RGB"), (W, H), method=Image.Resampling.LANCZOS)
    image = ImageEnhance.Contrast(image).enhance(1.05)
    overlay = Image.new("RGB", (W, H), NAVY)
    return Image.blend(image, overlay, 0.38 if use_product else 0.2)


def make_card(background, headline, detail, index):
    canvas = background.copy().convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle((48, 1090, W - 48, 1790), radius=38, fill=NAVY + (242,))
    draw.rectangle((48, 1090, W - 48, 1097), fill=CYAN + (255,))
    draw_centered(draw, "INKBLADE AUTHOR STUDIO", 1160, 42, CYAN + (255,))
    draw_centered(draw, headline, 1280, 88, WHITE + (255,), line_h=106)
    draw_centered(draw, detail, 1580, 42, CYAN + (255,), line_h=58)
    draw_centered(draw, f"0{index + 1}", 1710, 34, CYAN + (255,))
    return Image.alpha_composite(canvas, layer).convert("RGB")


async def make_voice(path):
    voice = edge_tts.Communicate(NARRATION, voice="en-US-ChristopherNeural", rate="-8%")
    await voice.save(str(path))


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    response = requests.get(BASE_URL, timeout=60)
    response.raise_for_status()
    with tempfile.TemporaryDirectory(prefix="studio-2026-07-21-") as temp_name:
        temp = Path(temp_name)
        base_file = temp / "base.png"
        base_file.write_bytes(response.content)
        base = prepare_background(Image.open(base_file))
        product = prepare_background(Image.open(PRODUCT), use_product=True)

        cards = []
        for index, (_, headline, detail) in enumerate(BEATS):
            background = base if index in (0, 4) else product
            card = make_card(background, headline, detail, index)
            card_path = temp / f"card-{index}.png"
            card.save(card_path, optimize=True)
            cards.append(card_path)
            if index == 0:
                card.save(COVER, optimize=True)

        segments = []
        for index, ((seconds, _, _), card_path) in enumerate(zip(BEATS, cards)):
            segment = temp / f"segment-{index}.mp4"
            frames = seconds * FPS
            zoom_step = 0.0012 if index not in (0, 4) else 0.0008
            vf = (
                f"scale=1200:2134,zoompan=z='min(zoom+{zoom_step},1.18)':"
                "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={frames}:s={W}x{H}:fps={FPS},format=yuv420p"
            )
            run([
                "ffmpeg", "-y", "-loop", "1", "-i", str(card_path),
                "-vf", vf, "-frames:v", str(frames), "-an",
                "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                "-pix_fmt", "yuv420p", str(segment),
            ])
            segments.append(segment)

        concat_file = temp / "concat.txt"
        concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
        silent = temp / "silent.mp4"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(silent)])

        voice = temp / "voice.mp3"
        asyncio.run(make_voice(voice))
        run([
            "ffmpeg", "-y", "-i", str(silent), "-i", str(voice),
            "-filter_complex", "[1:a]apad=pad_dur=24,afade=t=out:st=22:d=2[a]",
            "-map", "0:v:0", "-map", "[a]", "-t", "24",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", str(VIDEO),
        ])

    print(f"COVER={COVER}")
    print(f"VIDEO={VIDEO}")


if __name__ == "__main__":
    main()
