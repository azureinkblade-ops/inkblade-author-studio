"""
Studio ASSET-BASED reel builder (full-quality product PNGs, no screen capture).

Uses the real product art we already own (pinterest/assets/pins/*.png) so the reel
shows exactly what the products look like, full-bleed and readable. Hook-first,
>=60s, persona-voiced, with a freshly generated matched voiceover (edge_tts, GPU-free).

Hook (persona voice, from inkblade-studio-social-personas):
  "I don't have time to make graphics, here is the fix."

Run:
  python build_reel_assets.py --out site/assets/posts/reel-assets-YYYY-MM-DD.mp4
"""
import argparse
import os
import asyncio
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ROOT)  # site/scripts -> site; site -> Studio root
# pins live in the Studio root (parent of site/), not in the deployed site/
PINS = os.path.join(STUDIO, "..", "pinterest", "assets", "pins")
PINS = os.path.abspath(PINS)
OUT = os.path.join(ROOT, "..", "assets", "posts")  # site/scripts/../assets/posts
OUT = os.path.abspath(OUT)
HOOK_TEXT = "I don't have time to make graphics, here is the fix."
VO_TEXT = (
    "I don't have time to make graphics. Here is the fix. "
    "The Inkblade Author Studio is a toolkit built for fantasy and LitRPG authors. "
    "The Caption Vault gives you three hundred fifty captions you can paste today, "
    "chapter posts, Patreon promos, reader hooks. "
    "The Author Promotion Vault turns one release into a full week of content, "
    "with promo layouts and launch checklists. "
    "The Release Calendar keeps every drop on schedule. "
    "The Fantasy Image Pack hands you a hundred ready-to-post fantasy images. "
    "Or grab the Complete Author Vault, all five tools in one bundle. "
    "LAUNCH is on, twenty percent off, link in bio."
)

W, H = 1080, 1920
FPS = 30
NAVY = (7, 17, 31)
BLUE = (56, 199, 255)
WHITE = (255, 255, 255)
GRAY = (216, 222, 232)

# (asset, kicker, headline, detail, vo continues from VO_TEXT order)
BEATS = [
    ("cap-01.png", "CAPTION VAULT", "350 captions you paste today",
     "Chapter posts, Patreon promos, reader hooks.", None),
    ("promo-01.png", "PROMOTION VAULT", "One release, a full week of content",
     "Promo layouts and launch checklists.", None),
    ("cal-01.png", "RELEASE CALENDAR", "Never miss a launch date",
     "Plan every drop, checklist built in.", None),
    ("img-01.png", "FANTASY IMAGE PACK", "100 images, ready to post",
     "Elves, knights, dragons, magic, castles.", None),
    ("bundle-01.png", "COMPLETE AUTHOR VAULT", "All five tools, one bundle",
     "Save twelve dollars versus buying separate.", None),
]
HOOK_SEC = 3.0
BEAT_SEC = (62.0 - HOOK_SEC) / len(BEATS)


def font(size):
    for p in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def wrap(text, draw, fnt, max_width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        c = w if not cur else cur + " " + w
        if draw.textlength(c, font=fnt) <= max_width:
            cur = c
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def centered(draw, text, y, size, color, max_width=940, spacing=16):
    f = font(size)
    for line in wrap(text, draw, f, max_width):
        w = draw.textlength(line, font=f)
        draw.text(((W - w) / 2, y), line, font=f, fill=color)
        y += size + spacing
    return y


def load_asset(name):
    img = Image.open(os.path.join(PINS, name)).convert("RGB")
    w, h = img.size
    img = img.crop((0, 0, w, int(h * 0.90)))  # strip baked footer
    return ImageOps.fit(img, (W, H), method=Image.Resampling.LANCZOS)


def kb(img, t, zoom_from=1.0, zoom_to=1.7):
    bw, bh = img.size
    scale = zoom_from + (zoom_to - zoom_from) * t
    cw, ch = int(W * scale), int(H * scale)
    x = (bw - cw) // 2
    y = (bh - ch) // 2
    return img.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.LANCZOS)


def card(draw, spec, alpha):
    a = int(alpha)
    draw.rounded_rectangle((70, 255, 1010, 1430), radius=40,
                           fill=(7, 17, 31, int(200 * a / 255)),
                           outline=BLUE + (a,), width=4)
    centered(draw, spec[1], 380, 42, BLUE + (a,))
    centered(draw, spec[2], 520, 78, WHITE + (a,))
    centered(draw, spec[3], 1130, 40, GRAY + (a,))
    centered(draw, "INKBLADE AUTHOR STUDIO", 1695, 34, BLUE + (a,))


def gen_vo(text, out_mp3):
    import edge_tts
    async def _run():
        comm = edge_tts.Communicate(text, voice="en-US-ChristopherNeural")
        await comm.save(out_mp3)
    asyncio.run(_run())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(OUT, "reel-assets-2026-07-19.mp4"))
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    vo_mp3 = os.path.join(ROOT, "_assemble", "assets_vo.mp3")
    os.makedirs(os.path.dirname(vo_mp3), exist_ok=True)
    gen_vo(VO_TEXT, vo_mp3)

    with tempfile.TemporaryDirectory(prefix="studio-assets-reel-") as tmp:
        hook_asset = load_asset(BEATS[0][0])
        idx = 0
        # HOOK
        hook_frames = int(HOOK_SEC * FPS)
        for f in range(hook_frames):
            t = f / hook_frames
            base = kb(hook_asset, t, zoom_from=1.4, zoom_to=1.05)
            base = Image.blend(base, Image.new("RGB", (W, H), NAVY), 0.45)
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            td = ImageDraw.Draw(layer)
            alpha = 255 if f > 4 else int(255 * f / 4)
            shift = max(0, 30 - f * 6)
            y = 240 - shift
            for line in wrap("I don't have time", td, font(86), 940):
                w = td.textlength(line, font=font(86))
                td.text(((W - w) / 2, y), line, font=font(86), fill=WHITE + (alpha,))
                y += 100
            y = 430 - shift
            for line in wrap("to make graphics, here is the fix.", td, font(64), 940):
                w = td.textlength(line, font=font(64))
                td.text(((W - w) / 2, y), line, font=font(64), fill=BLUE + (alpha,))
                y += 78
            centered(td, "INKBLADE AUTHOR STUDIO", 1695, 34, BLUE + (alpha,))
            frame = Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")
            frame.save(os.path.join(tmp, f"f{idx:04d}.png"))
            idx += 1

        # PRODUCT BEATS
        for asset, spec in [(load_asset(b[0]), b) for b in BEATS]:
            n = int(BEAT_SEC * FPS)
            fade = int(FPS * 0.35)
            for f in range(n):
                t = f / n
                base = kb(asset, t, zoom_from=1.15, zoom_to=1.7)
                base = Image.blend(base, Image.new("RGB", (W, H), NAVY), 0.30)
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                td = ImageDraw.Draw(layer)
                alpha = 255 if f >= fade else int(255 * f / fade)
                card(td, spec, alpha)
                frame = Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")
                frame.save(os.path.join(tmp, f"f{idx:04d}.png"))
                idx += 1

        silent = os.path.join(tmp, "silent.mp4")
        cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-i",
               os.path.join(tmp, "f%04d.png"),
               "-c:v", "libx264", "-preset", "medium", "-crf", "19",
               "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart", silent]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(r.stderr[-2000:])

        dur = 62.0
        fade_out = dur - 2
        filt = (f"[1:a]afade=t=in:st=0:d=0.4,afade=t=out:st={fade_out}:d=2,"
                f"aloop=loop=-1:size=2e9,atrim=0:{dur}[vo]")
        cmd = ["ffmpeg", "-y", "-i", silent, "-i", vo_mp3,
               "-filter_complex", filt, "-map", "0:v", "-map", "[vo]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
               "-movflags", "+faststart", args.out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(r.stderr[-2000:])
    print(f"REEL READY: {args.out}")


if __name__ == "__main__":
    main()
