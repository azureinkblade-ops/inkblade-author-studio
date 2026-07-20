"""
Reel text safety check (shared by build_reel_assets.py and build_reel_2026-07-20.py).

Guarantees no on-screen text clips the 1080px frame. Call assert_text_fits() for
every string you draw; it raises if the text cannot fit within SAFE_W even after
shrinking to the minimum font size. This makes the daily-cron build FAIL (not ship)
a reel with clipped text.
"""
W = 1080
H = 1920
SAFE_W = W - 120          # 960px usable width, 60px margin each side
SAFE_TOP = 80             # keep text >= 80px from top
SAFE_BOTTOM = H - 80      # keep text <= 80px from bottom
MIN_SIZE = 26             # smallest allowable font; below this = refuse


def _font(size, bold=True):
    from PIL import ImageFont
    if bold:
        for p in (r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"):
            if __import__("os").path.exists(p):
                return ImageFont.truetype(p, size)
    else:
        for p in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
            if __import__("os").path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def assert_text_fits(draw, text, size, y, line_h, max_w=SAFE_W, min_size=MIN_SIZE):
    """Raise RuntimeError if `text` cannot fit within max_w (shrunk to min_size)
    or if the block [y .. y + n*line_h] leaves the [SAFE_TOP, SAFE_BOTTOM] band.
    Call BEFORE drawing so a bad reel aborts the build instead of shipping clipped."""
    s = size
    fnt = _font(s)
    lines = _wrap(draw, text, fnt, max_w)
    while (any(draw.textlength(ln, font=fnt) > max_w for ln in lines)) and s > min_size:
        s -= 4
        fnt = _font(s)
        lines = _wrap(draw, text, fnt, max_w)
    if any(draw.textlength(ln, font=fnt) > max_w for ln in lines):
        raise RuntimeError(
            f"TEXT CLIP RISK: '{text[:40]}...' still exceeds {max_w}px at min size {min_size}")
    block_bottom = y + line_h * len(lines)
    if y < SAFE_TOP or block_bottom > SAFE_BOTTOM:
        raise RuntimeError(
            f"TEXT CLIP RISK: block y={y}..{block_bottom} outside safe band "
            f"[{SAFE_TOP}, {SAFE_BOTTOM}] for '{text[:40]}...'")
    return lines, fnt, s
