#!/usr/bin/env python3
"""Render the news-image poster for Sunday 22 November 2026.

Reads stories.json (date, one lead story, four smaller stories, sources)
and draws a 1024x1024 newspaper-style poster, "The World in One Day",
as a JPEG. Deterministic: no clock, no randomness, no network — the
output depends only on stories.json, so re-runs are byte-identical
apart from the JPEG encoder's own deterministic output.

Usage:
    python3 render_poster.py stories.json entry.png
    python3 render_poster.py stories.json test-poster.jpg   # layout test
"""
import json
import math
import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
PAPER = (247, 242, 231)
INK = (20, 20, 20)
RULE = (176, 30, 36)
PANEL = (255, 253, 246)
MUTED = (90, 86, 76)

SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_w):
    """Greedy word wrap; returns a list of lines that fit max_w."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_lines(draw, lines, x, y, fnt, fill, leading):
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += leading
    return y


def letter_spaced(draw, text, x, y, fnt, fill, spacing=4):
    """Draw text with extra tracking, centred on x (x = centre)."""
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    cx = x - total / 2
    for ch, w in zip(text, widths):
        draw.text((cx, y), ch, font=fnt, fill=fill)
        cx += w + spacing


# ---- simple bold icons, drawn with shapes only -------------------------

def icon(draw, kind, box, bg):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=14, fill=bg)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    w, h = x1 - x0, y1 - y0
    fg = (255, 255, 255)
    dk = (20, 20, 20)
    if kind == "globe":
        r = min(w, h) * 0.32
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=fg, width=5)
        draw.ellipse([cx - r * 0.45, cy - r, cx + r * 0.45, cy + r],
                     outline=fg, width=3)
        draw.line([cx - r, cy, cx + r, cy], fill=fg, width=3)
        draw.arc([cx - r, cy - r * 0.55, cx + r, cy + r * 0.55],
                 0, 360, fill=fg, width=3)
    elif kind == "flags":
        for i, off in enumerate((-34, 0, 34)):
            draw.line([cx + off, cy + 44, cx + off, cy - 44], fill=fg, width=5)
            col = [(176, 30, 36), (255, 255, 255), (255, 214, 64)][i]
            draw.polygon([(cx + off, cy - 44), (cx + off + 34, cy - 32),
                          (cx + off, cy - 20)], fill=col)
    elif kind == "chart":
        base = cy + 40
        draw.line([cx - 52, base, cx + 52, base], fill=fg, width=5)
        for i, bh in enumerate((26, 48, 36, 62)):
            bx = cx - 48 + i * 26
            draw.rectangle([bx, base - bh, bx + 16, base], fill=fg)
    elif kind == "storm":
        draw.ellipse([cx - 48, cy - 18, cx - 2, cy + 22], fill=fg)
        draw.ellipse([cx - 16, cy - 34, cx + 44, cy + 14], fill=fg)
        draw.polygon([(cx - 6, cy + 12), (cx - 22, cy + 52), (cx - 4, cy + 52),
                      (cx - 14, cy + 78), (cx + 16, cy + 28), (cx + 0, cy + 28)],
                     fill=(255, 214, 64))
    elif kind == "rocket":
        draw.polygon([(cx, cy - 52), (cx + 22, cy + 10), (cx, cy + 34),
                      (cx - 22, cy + 10)], fill=fg)
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=bg)
        draw.polygon([(cx - 22, cy + 14), (cx - 38, cy + 44), (cx - 14, cy + 34)],
                     fill=fg)
        draw.polygon([(cx + 22, cy + 14), (cx + 38, cy + 44), (cx + 14, cy + 34)],
                     fill=fg)
        draw.polygon([(cx - 8, cy + 34), (cx + 8, cy + 34), (cx, cy + 62)],
                     fill=(255, 150, 40))
    elif kind == "scales":
        draw.line([cx, cy - 42, cx, cy + 44], fill=fg, width=5)
        draw.line([cx - 44, cy - 30, cx + 44, cy - 30], fill=fg, width=5)
        for s in (-1, 1):
            draw.line([cx + s * 44, cy - 30, cx + s * 44, cy - 6], fill=fg, width=3)
            draw.arc([cx + s * 44 - 16, cy - 8, cx + s * 44 + 16, cy + 24],
                     0, 180, fill=fg, width=4)
    elif kind == "ship":
        draw.polygon([(cx - 52, cy + 8), (cx + 52, cy + 8), (cx + 34, cy + 40),
                      (cx - 34, cy + 40)], fill=fg)
        draw.line([cx, cy + 8, cx, cy - 44], fill=fg, width=5)
        draw.polygon([(cx, cy - 44), (cx + 34, cy - 18), (cx, cy - 18)],
                     fill=(176, 30, 36))
        for k in range(3):
            draw.arc([cx - 56 + k * 36, cy + 48, cx - 20 + k * 36, cy + 66],
                     0, 180, fill=fg, width=3)
    elif kind == "trophy":
        draw.polygon([(cx - 26, cy - 40), (cx + 26, cy - 40), (cx + 16, cy + 6),
                      (cx - 16, cy + 6)], fill=fg)
        draw.arc([cx - 44, cy - 40, cx - 14, cy - 8], 90, 270, fill=fg, width=5)
        draw.arc([cx + 14, cy - 40, cx + 44, cy - 8], 270, 90, fill=fg, width=5)
        draw.rectangle([cx - 6, cy + 6, cx + 6, cy + 26], fill=fg)
        draw.rectangle([cx - 22, cy + 26, cx + 22, cy + 36], fill=fg)
    elif kind == "leaf":
        draw.ellipse([cx - 40, cy - 44, cx + 40, cy + 36], fill=fg)
        draw.line([cx - 30, cy + 26, cx + 30, cy - 34], fill=bg, width=4)
        draw.line([cx + 34, cy + 44, cx + 44, cy + 58], fill=fg, width=6)
    elif kind == "chip":
        draw.rectangle([cx - 30, cy - 30, cx + 30, cy + 30], fill=fg)
        draw.rectangle([cx - 14, cy - 14, cx + 14, cy + 14], fill=bg)
        for i in range(3):
            for s in (-1, 1):
                draw.line([cx - 18 + i * 18, cy + s * 30, cx - 18 + i * 18,
                           cy + s * 46], fill=fg, width=4)
                draw.line([cx + s * 30, cy - 18 + i * 18, cx + s * 46,
                           cy - 18 + i * 18], fill=fg, width=4)
    else:  # "star" fallback
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            r = 46 if i % 2 == 0 else 19
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        draw.polygon(pts, fill=fg)


TAG_COLORS = ["#b01e24", "#1d4e89", "#0f6b4a", "#7a4a12", "#5b2d8e", "#8c1d5e"]


def render(data, out_path):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    mx = 28  # margin

    # ---- masthead ------------------------------------------------------
    d.rectangle([mx, 22, W - mx, 26], fill=RULE)
    title_f = font(SERIF_B, 62)
    d.text((W // 2, 34), "THE WORLD IN ONE DAY", font=title_f, fill=INK,
           anchor="ma")
    date_f = font(SANS_B, 30)
    letter_spaced(d, data["date"].upper(), W // 2, 112, date_f, RULE, spacing=5)
    d.rectangle([mx, 152, W - mx, 156], fill=INK)
    sub_f = font(SANS, 21)
    d.text((W // 2, 166), data["subtitle"], font=sub_f, fill=MUTED, anchor="ma")

    # ---- lead story ----------------------------------------------------
    ly0, ly1 = 200, 528
    d.rounded_rectangle([mx, ly0, W - mx, ly1], radius=10, fill=PANEL,
                        outline=INK, width=2)
    lead = data["lead"]
    icon(d, lead["icon"], (mx + 18, ly0 + 18, mx + 298, ly0 + 298),
         TAG_COLORS[0])
    tx = mx + 322
    tag_f = font(SANS_B, 22)
    d.text((tx, ly0 + 22), lead["tag"].upper(), font=tag_f, fill=RULE)
    head_f = font(SERIF_B, 40)
    lines = wrap(d, lead["headline"], head_f, W - mx - tx - 18)
    y = draw_lines(d, lines[:3], tx, ly0 + 56, head_f, INK, 48)
    sum_f = font(SANS, 23)
    slines = wrap(d, lead["summary"], sum_f, W - mx - tx - 18)
    draw_lines(d, slines[:4], tx, y + 10, sum_f, (50, 48, 44), 31)

    # ---- four smaller stories, 2x2 ------------------------------------
    gy0 = 546
    cw = (W - 2 * mx - 16) // 2
    ch = 208
    for i, s in enumerate(data["stories"][:4]):
        gx = mx + (i % 2) * (cw + 16)
        gy = gy0 + (i // 2) * (ch + 14)
        d.rounded_rectangle([gx, gy, gx + cw, gy + ch], radius=10, fill=PANEL,
                            outline=INK, width=2)
        icon(d, s["icon"], (gx + 14, gy + 14, gx + 130, gy + 130),
             TAG_COLORS[(i + 1) % len(TAG_COLORS)])
        sx = gx + 146
        d.text((sx, gy + 14), s["tag"].upper(), font=font(SANS_B, 18),
               fill=RULE)
        hf = font(SERIF_B, 25)
        hl = wrap(d, s["headline"], hf, gx + cw - sx - 14)
        y = draw_lines(d, hl[:2], sx, gy + 40, hf, INK, 30)
        sf = font(SANS, 19)
        sl = wrap(d, s["summary"], sf, gx + cw - sx - 14)
        draw_lines(d, sl[:3], sx, y + 4, sf, (50, 48, 44), 25)

    # ---- footer --------------------------------------------------------
    d.rectangle([mx, 982, W - mx, 984], fill=INK)
    ff = font(SANS, 16)
    d.text((W // 2, 990), data["sources"], font=ff, fill=MUTED, anchor="ma")

    img.save(out_path, "JPEG", quality=88, optimize=True)
    return out_path


def main():
    if len(sys.argv) != 3:
        print("usage: render_poster.py stories.json out.jpg")
        return 2
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    render(data, sys.argv[2])
    import os
    print(f"wrote {sys.argv[2]} ({os.path.getsize(sys.argv[2])} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
