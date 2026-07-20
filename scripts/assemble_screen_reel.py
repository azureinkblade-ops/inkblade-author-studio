"""
Assemble a Studio reel from a SCREEN-CAPTURE clip you recorded in OBS.

You (David) record the workflow in OBS (Window or Display Capture) and drop the
file in recordings/. This script turns it into a branded 9:16 reel:
  - 0-3s HOOK card (upper-third text, navy/cyan)
  - your screen clip, converted to 9:16 with a BLURRED SIDEBAR (full screen stays
    visible, no hard crop that loses half the window)
  - 3s OUTRO (LAUNCH CTA + brand)
  - generates a MATCHED voiceover from --vo (edge_tts, GPU-free) so audio matches
    the visuals (no more Image-Pack VO over a Promotion-Vault clip)
  - burns lower-third captions (persona-voiced, via PIL, not fragile drawtext)
  - CRF 19, faststart, AAC audio

Usage:
  python assemble_screen_reel.py recordings/your-clip.mp4 \
    --hook "I don't have time to make graphics, here is the fix." \
    --vo "Your hook line. Then walk through the product. End with the CTA." \
    --captions "0:6:line1;6:12:line2" \
    --out site/assets/posts/reel-YYYY-MM-DD.mp4
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920


def render_hook(out_png, text):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (W, H), (7, 17, 31))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H // 2, W, H], fill=(4, 10, 20))
    fbig = ImageFont.truetype("C:/Windows/Fonts/ARIALBD.TTF", 72)
    fsmall = ImageFont.truetype("C:/Windows/Fonts/ARIALBD.TTF", 56)
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur + " " + w) * 36 > W - 160 and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    y = 300
    for i, ln in enumerate(lines):
        d.text((80, y), ln, font=fbig if i == 0 else fsmall,
               fill=(255, 255, 255) if i == 0 else (56, 199, 255))
        y += 86 if i == 0 else 70
    img.save(out_png)


def render_outro(out_png, cta="LAUNCH 20% off, link in bio"):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (W, H), (7, 17, 31))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H // 2 - 200, W, H // 2 + 200], fill=(12, 28, 48))
    f = ImageFont.truetype("C:/Windows/Fonts/ARIALBD.TTF", 64)
    d.text((W // 2 - 360, H // 2 - 120), "INKBLADE", font=f, fill=(255, 255, 255))
    d.text((W // 2 - 300, H // 2 - 40), "AUTHOR STUDIO", font=f, fill=(56, 199, 255))
    d.text((W // 2 - 380, H // 2 + 70), cta, font=ImageFont.truetype(
        "C:/Windows/Fonts/ARIAL.TTF", 40), fill=(220, 220, 220))
    img.save(out_png)


def to_9x16_blurred(clip, out_clip, trim_start=0.0, trim_end=None):
    """Convert screen clip to 9:16. Source is high-res (4K); fill HEIGHT so the
    screen is large and readable, crop the center 1080px of width (modest side
    crop, no tiny postage-stamp-with-bars). Full-bleed, no letterbox/blur bars."""
    trim = ""
    if trim_end:
        trim = f",trim=start={trim_start}:end={trim_end},setpts=PTS-STARTPTS"
    elif trim_start:
        trim = f",trim=start={trim_start},setpts=PTS-STARTPTS"
    vf = (
        f"[0:v]setpts=PTS{trim},scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,setsar=1,fps=30,setdar=9/16"
    )
    subprocess.run([
        "ffmpeg", "-y", "-i", clip, "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-an", out_clip,
    ], check=True)


def burn_captions(clip_in, out_clip, captions):
    """Lower-third captions via PIL frame-by-frame compositing (no ffmpeg
    drawtext, which fails on Windows font paths / '=' in text)."""
    from PIL import Image, ImageDraw, ImageFont
    tmp = os.path.join(ROOT, "_assemble", "capped_frames")
    os.makedirs(tmp, exist_ok=True)

    # Probe frame count + fps.
    meta = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=nb_read_frames,r_frame_rate",
        "-count_frames", "-of", "default=noprint_wrappers=1",
        clip_in]).decode()
    fps = 30.0
    nframes = 999999
    for line in meta.splitlines():
        if "r_frame_rate" in line:
            a, b = line.split("=")[1].split("/")
            fps = float(a) / float(b) if float(b) else 30.0
        if "nb_read_frames" in line:
            nframes = int(line.split("=")[1])

    # Extract frames.
    subprocess.run(["ffmpeg", "-y", "-i", clip_in,
                    os.path.join(tmp, "f%05d.png")], check=True)

    fnt = ImageFont.truetype("C:/Windows/Fonts/ARIALBD.TTF", 46)
    files = sorted(os.listdir(tmp))
    for i, fn in enumerate(files):
        t = i / fps
        txt = next((c[2] for c in captions if c[0] <= t < c[1]), None)
        im = Image.open(os.path.join(tmp, fn)).convert("RGB")
        if txt:
            d = ImageDraw.Draw(im)
            pad = 24
            tw = d.textlength(txt, font=fnt)
            box_w = int(tw) + pad * 2
            box_x = (W - box_w) // 2
            box_y = H - 200
            d.rectangle([box_x, box_y, box_x + box_w, box_y + 90],
                        fill=(7, 17, 31))
            d.text(((W - tw) / 2, box_y + 22), txt, font=fnt, fill=(255, 255, 255))
        im.save(os.path.join(tmp, fn))

    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(fps), "-i", os.path.join(tmp, "f%05d.png"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        out_clip,
    ], check=True)


def gen_vo(text, out_mp3):
    """GPU-free TTS via edge_tts. Matched to the reel, not a reused clip."""
    import asyncio, edge_tts
    async def _run():
        comm = edge_tts.Communicate(text, voice="en-US-ChristopherNeural")
        await comm.save(out_mp3)
    asyncio.run(_run())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--hook", default="I don't have time to make graphics, here is the fix.")
    ap.add_argument("--vo", default="",
                    help="voiceover script; generated via edge_tts (GPU-free), matched to the clip")
    ap.add_argument("--out", required=True)
    ap.add_argument("--trim-start", type=float, default=3.0)
    ap.add_argument("--trim-end", type=float, default=None)
    ap.add_argument("--captions", default="",
                    help="semicolon-separated 'start:end:text' lower-third overlays")
    args = ap.parse_args()

    work = os.path.join(ROOT, "_assemble")
    os.makedirs(work, exist_ok=True)
    hook_png = os.path.join(work, "hook.png")
    outro_png = os.path.join(work, "outro.png")
    clip_9x16 = os.path.join(work, "clip_9x16.mp4")
    clip_capped = os.path.join(work, "clip_capped.mp4")
    vo_mp3 = os.path.join(work, "vo.mp3")
    hook_mp4 = os.path.join(work, "hook.mp4")
    outro_mp4 = os.path.join(work, "outro.mp4")

    render_hook(hook_png, args.hook)
    render_outro(outro_png)
    to_9x16_blurred(args.clip, clip_9x16, trim_start=args.trim_start, trim_end=args.trim_end)

    if args.captions.strip():
        caps = []
        for part in args.captions.split(";"):
            if not part.strip():
                continue
            s, e, txt = part.split(":", 2)
            caps.append((float(s), float(e), txt))
        burn_captions(clip_9x16, clip_capped, caps)
        clip_final = clip_capped
    else:
        clip_final = clip_9x16

    for png, mp4, dur in [(hook_png, hook_mp4, 3), (outro_png, outro_mp4, 3)]:
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", png, "-t", str(dur),
            "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
            "-crf", "19", mp4,
        ], check=True)

    concat_list = os.path.join(work, "concat.txt")
    with open(concat_list, "w") as f:
        for m in [hook_mp4, clip_final, outro_mp4]:
            f.write(f"file '{m}'\n")
    silent = os.path.join(work, "silent.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", silent,
    ], check=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    # Generate a MATCHED voiceover if --vo provided (overrides any stale mp3).
    if args.vo.strip():
        gen_vo(args.vo, vo_mp3)
        duration = float(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", silent]).strip())
        fade_out = max(0, duration - 2)
        filt = (f"[1:a]afade=t=in:st=0:d=0.4,afade=t=out:st={fade_out}:d=2,"
                f"aloop=loop=-1:size=2e9,atrim=0:{duration}[vo]")
        subprocess.run([
            "ffmpeg", "-y", "-i", silent, "-i", vo_mp3,
            "-filter_complex", filt, "-map", "0:v", "-map", "[vo]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", args.out,
        ], check=True)
    else:
        os.replace(silent, args.out)
    print(f"REEL READY: {args.out}")


if __name__ == "__main__":
    main()
