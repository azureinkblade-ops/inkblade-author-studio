"""Build the 2026-07-20 Inkblade Author Studio reel cover + 12s MP4.

Studio brand only (fantasy AUTHORS). DRAFT-mode asset build, no publishing here.
Cover: navy + electric-blue sword-quill base with deterministic PIL hook text.
Reel: Ken Burns zoom + per-beat fade-in captions + edge_tts voiceover (GPU-free).
"""
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

BASE = r"C:\Users\David\Documents\Inkblade Author Studio\site\assets\posts\reel-2026-07-20-base.png"
SITE = r"C:\Users\David\Documents\Inkblade Author Studio\site\assets\posts"
COVER_PNG = os.path.join(SITE, "reel-2026-07-20.png")
MP4 = os.path.join(SITE, "reel-2026-07-20.mp4")
W, H = 1080, 1920
FPS = 30

NAVY = (7, 17, 31)
BLUE = (56, 199, 255)
WHITE = (255, 255, 255)


def load_font(size, bold=True):
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def safe_lines(draw, text, size, max_w=W - 120):
    """Wrap, then shrink font until every line fits max_w. Returns (lines, font)."""
    font = load_font(size)
    lines = wrap_text(draw, text, font, max_w)
    while any(draw.textlength(ln, font=font) > max_w for ln in lines) and size > 24:
        size -= 4
        font = load_font(size)
        lines = wrap_text(draw, text, font, max_w)
    return lines, font


def draw_safe(d, text, cx, y, size, fill, max_w=W - 120, shadow=True):
    """Draw text centered at cx, wrapped + width-clamped so it NEVER clips."""
    lines, font = safe_lines(d, text, size, max_w)
    for ln in lines:
        w = d.textlength(ln, font=font)
        x = cx - w / 2
        if shadow:
            d.text((x + 3, y + 3), ln, font=font, fill=(0, 0, 0, 200))
        d.text((x, y), ln, font=font, fill=fill)
        y += font.size + 12
    return y


def composite_cover(base):
    img = base.resize((W, H)).convert("RGB")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    # headline block: render the original 2 lines, each width-guarded, centered as a block
    lines = ["THREE PROMO TOOLS", "ZERO SYSTEM"]
    size = 150
    fnt = load_font(size)
    # width-guard each line (shrink if needed)
    guarded = []
    for ln in lines:
        while d.textlength(ln, font=fnt) > W - 120 and size > 28:
            size -= 4
            fnt = load_font(size)
        guarded.append(ln)
    line_h = fnt.size + 18
    block_h = line_h * len(guarded)
    # center block in upper-third band (y from 0.14H to 0.55H), clamp inside frame
    y = max(int(H * 0.16), int(H * 0.30) - block_h // 2)
    bar_top = y - 50
    bar_bottom = y + block_h + 20
    d.rectangle([60, bar_top, W - 60, bar_bottom], fill=(7, 17, 31, 175))
    yy = y
    for ln in guarded:
        w = d.textlength(ln, font=fnt)
        x = W // 2 - w / 2
        d.text((x + 3, yy + 3), ln, font=fnt, fill=(0, 0, 0, 200))
        d.text((x, yy), ln, font=fnt, fill=WHITE)
        yy += line_h
    # small brand tag bottom (width-guarded)
    draw_safe(d, "INKBLADE AUTHOR STUDIO", W // 2, H - 90, 40, BLUE)
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")
    return img


def kb_zoom(base, t, total):
    # hook 0-3s: 1.4 -> 1.05 ; beats 3-12s: 1.15 -> 1.7
    if t < 3.0:
        z = 1.4 + (1.05 - 1.4) * (t / 3.0)
    else:
        p = (t - 3.0) / max(0.001, (total - 3.0))
        z = 1.15 + (1.7 - 1.15) * min(1.0, p)
    z = max(1.02, z)
    zw, zh = int(W / z), int(H / z)
    left = (W - zw) // 2
    top = (H - zh) // 2
    return base.crop((left, top, left + zw, top + zh)).resize((W, H))


BEATS = [
    (0.0, 3.0, ["THREE PROMO TOOLS", "ZERO SYSTEM"], 150, True),
    (3.0, 6.0, ["You bought the captions,", "the calendar, the promo kit."], 70, False),
    (6.0, 9.0, ["None connect.", "Every launch starts from zero."], 78, False),
    (9.0, 12.0, ["Complete Author Vault = $30", "all three in one system."], 70, False),
    (12.0, 999.0, ["Save this for your next launch.", "Link in bio."], 80, False),
]


def draw_beats(overlay, t, total):
    d = ImageDraw.Draw(overlay)
    for (s, e, lines, size, big) in BEATS:
        if t < s or t >= e:
            continue
        age = t - s
        alpha = int(min(1.0, age / 0.4) * 255)
        # lower-third readability bar; render each given line, width-guarded
        fnt = load_font(size)
        for ln in lines:
            while d.textlength(ln, font=fnt) > W - 120 and size > 24:
                size -= 4
                fnt = load_font(size)
        line_h = fnt.size + 12
        block_h = line_h * len(lines)
        bar_top = int(H * 0.62)
        bar_bottom = bar_top + block_h + 80
        d.rectangle([50, bar_top - 40, W - 50, bar_bottom], fill=(7, 17, 31, 175))
        yy = bar_top
        for ln in lines:
            w = d.textlength(ln, font=fnt)
            x = W // 2 - w / 2
            d.text((x + 3, yy + 3), ln, font=fnt, fill=(0, 0, 0, int(alpha * 0.6)))
            d.text((x, yy), ln, font=fnt, fill=WHITE)
            yy += line_h
        return


def build_video(base, total):
    frames_dir = tempfile.mkdtemp(prefix="reel20_")
    n = int(total * FPS)
    for i in range(n):
        t = i / FPS
        frame = kb_zoom(base, t, total).convert("RGBA")
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_beats(overlay, t, total)
        frame = Image.alpha_composite(frame, overlay).convert("RGB")
        frame.save(os.path.join(frames_dir, f"{i:05d}.png"))
    silent = os.path.join(frames_dir, "silent.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(frames_dir, "%05d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", silent],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return silent


def make_tts():
    import asyncio
    import edge_tts

    narr = ("You bought the captions, the calendar, and the promo kit. "
            "None of them connect, so every launch starts from zero. "
            "The Complete Author Vault puts all three in one $30 system. "
            "Plan the drop once. Save this for your next launch.")
    mp3 = tempfile.mktemp(suffix=".mp3")
    asyncio.run(edge_tts.Communicate(narr, voice="en-US-ChristopherNeural").save(mp3))
    return mp3


def audio_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def main():
    base = Image.open(BASE).convert("RGB")
    cover = composite_cover(base)
    cover.save(COVER_PNG)
    print("COVER", COVER_PNG, os.path.getsize(COVER_PNG))

    mp3 = make_tts()
    dur = audio_duration(mp3)
    total = max(12.0, dur + 0.2)
    silent = build_video(base, total)
    padded = tempfile.mktemp(suffix=".mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3, "-af", "apad", "-t", f"{total:.2f}", padded],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", silent, "-i", padded, "-c:v", "copy", "-c:a", "aac",
         "-shortest", "-movflags", "+faststart", MP4],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print("MP4", MP4, os.path.getsize(MP4))


if __name__ == "__main__":
    main()
