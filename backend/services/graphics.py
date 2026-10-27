"""Zeichen-Bausteine: Schrift mit Kontur, Glow, Rahmen, Verläufe. Der Text kommt nie von der Bild-KI, sondern wird hier gesetzt."""
import math, re
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONTS = {"impact": "Anton-Regular.ttf", "clean": "BebasNeue-Regular.ttf", "tech": "RussoOne-Regular.ttf", "comic": "Bangers-Regular.ttf"}
FONT_STYLES = list(FONTS)
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def rgb(h, default):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) if isinstance(h, str) and _HEX.match(h) else default


def font(style, size):
    size = max(8, int(size))
    try:
        return ImageFont.truetype(str(FONT_DIR / FONTS.get(style, FONTS["impact"])), size)
    except OSError:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


def cover(img, w, h):
    return ImageOps.fit(img.convert("RGB"), (int(w), int(h)), Image.LANCZOS)


def darken(img, side, strength=170):
    """Dunkler Verlauf von einer Seite aus ('left', 'right', 'top', 'bottom'), damit Text lesbar bleibt."""
    W, H = img.size
    g = Image.linear_gradient("L")  # oben schwarz, unten weiß
    if side in ("left", "right"):
        g = g.rotate(90, expand=True)  # links schwarz, rechts weiß
    g = g.resize((W, H))
    if side in ("left", "top"):
        g = ImageOps.invert(g)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.putalpha(g.point(lambda v: int(strength * (v / 255) ** 1.5)))
    return Image.alpha_composite(img.convert("RGBA"), layer)


def silhouette(layer, color, scale=255):
    s = Image.new("RGBA", layer.size, tuple(color) + (0,))
    a = layer.getchannel("A")
    s.putalpha(a.point(lambda v: v * scale // 255) if scale < 255 else a)
    return s


def add_glow(canvas, layer, color, radius, times=2):
    g = silhouette(layer, color).filter(ImageFilter.GaussianBlur(radius))
    for _ in range(times):
        canvas.alpha_composite(g)


def stroke_around(obj, color, width):
    """Konturlinie um ein freigestelltes Motiv (Versatz in 16 Richtungen)."""
    pad = width + 2
    big = Image.new("RGBA", (obj.width + 2 * pad, obj.height + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(obj, (pad, pad))
    sil = silhouette(big, color)
    out = Image.new("RGBA", big.size, (0, 0, 0, 0))
    for i in range(16):
        a = 2 * math.pi * i / 16
        out.alpha_composite(ImageChops.offset(sil, round(width * math.cos(a)), round(width * math.sin(a))))
    out.alpha_composite(big)
    return out


def _wrap(d, words, f, st, max_w):
    lines, cur = [], []
    for w in words:
        if cur and d.textlength(" ".join(cur + [w]), font=f) + 2 * st > max_w:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    return lines + ([cur] if cur else [])


def fit_text(text, style, box_w, box_h, max_lines=3, max_size=400, stroke_ratio=0.07):
    """Größte Schriftgröße, bei der der Text (mit Umbruch) in die Box passt."""
    d = ImageDraw.Draw(Image.new("L", (8, 8)))
    words = str(text).split() or [" "]
    lo, hi, best = 12, max_size, None
    for _ in range(14):
        mid = (lo + hi) // 2
        f, st = font(style, mid), int(mid * stroke_ratio)
        lines = _wrap(d, words, f, st, box_w)
        width = max(d.textlength(" ".join(l), font=f) for l in lines) + 2 * st
        lh = int(mid * 1.02)
        if len(lines) <= max_lines and width <= box_w and len(lines) * lh <= box_h:
            best, lo = (f, mid, st, lines, lh, width), mid + 1
        else:
            hi = mid - 1
    if best is None:
        f, st = font(style, 12), 1
        lines = _wrap(d, words, f, st, box_w)
        best = (f, 12, st, lines, 12, box_w)
    return dict(zip(("font", "size", "stroke", "lines", "lh", "width"), best))


def draw_headline(canvas, text, box, style, fill, accent=None, highlight="", align="left", stroke_color=(0, 0, 0),
                  max_lines=3, max_size=400, stroke_ratio=0.07, shadow=True, valign="middle"):
    """Zeichnet Text mit Kontur in die Box. Ein Schlüsselwort kann in der Akzentfarbe erscheinen. Gibt (x0, y0, x1, y1) des Textblocks zurück."""
    x0, y0, x1, y1 = [int(v) for v in box]
    m = fit_text(text, style, x1 - x0, y1 - y0, max_lines, max_size, stroke_ratio)
    f, st, lines, lh = m["font"], m["stroke"], m["lines"], m["lh"]
    block_h = len(lines) * lh
    y = y0 + ((y1 - y0 - block_h) // 2 if valign == "middle" else 0)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    hl = str(highlight or "").strip().lower()
    space = d.textlength(" ", font=f)
    top, left, right = y, x1, x0
    for line in lines:
        total = d.textlength(" ".join(line), font=f)
        x = x0 + (x1 - x0 - total) / 2 if align == "center" else (x1 - total - st if align == "right" else x0 + st)
        left, right = min(left, x), max(right, x + total)
        for w in line:
            col = accent if accent and hl and w.lower().strip(".,!?:;") == hl else fill
            d.text((x, y), w, font=f, fill=tuple(col), stroke_width=st, stroke_fill=tuple(stroke_color))
            x += d.textlength(w, font=f) + space
        y += lh
    if shadow:
        off = max(3, st)
        sh = silhouette(layer, (0, 0, 0), 150)
        canvas.alpha_composite(ImageChops.offset(sh, off, off).filter(ImageFilter.GaussianBlur(off)))
    canvas.alpha_composite(layer)
    return int(left), top, int(right), y


def glow_text(canvas, text, box, style, fill, glow, **kw):
    """Text mit leuchtendem Schein, für Overlays und Offline-Bilder."""
    tmp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw_headline(tmp, text, box, style, glow, shadow=False, stroke_color=glow, **kw)
    add_glow(canvas, tmp, glow, 18, 2)
    return draw_headline(canvas, text, box, style, fill, shadow=False, stroke_color=(0, 0, 0), **kw)


def chamfer(box, c):
    x0, y0, x1, y1 = box
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def frame(canvas, box, style, color, accent, width=6, fill=None, glow=14):
    """Rahmen im Stil 'neon' (Glow), 'angular' (abgeschrägte Ecken) oder 'rounded'."""
    x0, y0, x1, y1 = [int(v) for v in box]
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    fill = tuple(fill) if fill else None
    if style == "rounded":
        d.rounded_rectangle((x0, y0, x1, y1), radius=max(10, min(44, (y1 - y0) // 4)), fill=fill, outline=tuple(color), width=width)
    elif style == "angular":
        pts = chamfer((x0, y0, x1, y1), max(8, min(40, (y1 - y0) // 4)))
        if fill:
            d.polygon(pts, fill=fill)
        d.line(pts + [pts[0]], fill=tuple(color), width=width, joint="curve")
    else:
        d.rectangle((x0, y0, x1, y1), fill=fill, outline=tuple(color), width=width)
    if style == "neon":
        add_glow(canvas, layer, color, glow, 2)
    canvas.alpha_composite(layer)
    L, w2 = max(18, (y1 - y0) // 6), width + 2
    d = ImageDraw.Draw(canvas)
    d.line([(x0, y0 + L), (x0, y0), (x0 + L, y0)], fill=tuple(accent), width=w2)
    d.line([(x1, y1 - L), (x1, y1), (x1 - L, y1)], fill=tuple(accent), width=w2)
