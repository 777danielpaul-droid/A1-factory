"""Einfache, selbst gezeichnete Produkt-Mockups (T-Shirt, Tasse, Handyhülle, Poster, Handy-Display).
Eigene Mockup-Vorlagen: backend/mockup_templates/<art>.png + <art>.json mit {"box": [x, y, breite, höhe]}."""
import json, uuid
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps
from services.image_generator import ASSET_DIR

S, K = 1600, 2  # Zielgröße und Supersampling für glatte Kanten
TEMPLATES = Path(__file__).resolve().parent.parent / "mockup_templates"
LABELS = {"tee_front": "T-Shirt vorne", "tee_back": "T-Shirt hinten", "mug": "Tasse", "phone_case": "Handyhülle",
          "poster": "Poster", "phone_screen": "Handy-Display"}


def _lum(img: Image.Image) -> float:
    px = [p for p in img.convert("RGBA").resize((64, 64)).getdata() if p[3] > 128]
    return sum(0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in px) / len(px) if px else 128


def _has_alpha(img: Image.Image) -> bool:
    return img.mode == "RGBA" and img.getchannel("A").getextrema()[0] < 250


def _canvas(bg):
    return Image.new("RGBA", (S * K, S * K), tuple(bg) + (255,))


def _sc(pts):
    return [(x * K, y * K) for x, y in pts]


def _box(b):
    return [v * K for v in b]


def _shadow(c, draw_fn, blur=26, alpha=95):
    layer = Image.new("RGBA", c.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer), (0, 0, 0, alpha))
    c.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur * K)))


def _place(c, design, cx, cy, w, h):
    d = design.convert("RGBA")
    d.thumbnail((w * K, h * K), Image.LANCZOS)
    c.alpha_composite(d, (cx * K - d.width // 2, cy * K - d.height // 2))


def _finish(c):
    return c.resize((S, S), Image.LANCZOS).convert("RGB")


def _tee(design, back=False):
    dark = _lum(design) > 100  # helle oder neonfarbene Designs auf dunklem Shirt
    shirt, edge, bg = ((34, 37, 42), (12, 14, 17), (232, 230, 225)) if dark else ((245, 245, 242), (200, 200, 195), (232, 230, 225))
    c = _canvas(bg)
    poly = [(620, 210), (330, 300), (150, 540), (300, 640), (390, 560), (390, 1350), (1210, 1350), (1210, 560),
            (1300, 640), (1450, 540), (1270, 300), (980, 210)]
    _shadow(c, lambda d, f: d.polygon(_sc([(x, y + 34) for x, y in poly]), fill=f), 30)
    d = ImageDraw.Draw(c)
    d.polygon(_sc(poly), fill=shirt)
    d.line(_sc(poly + [poly[0]]), fill=edge, width=3 * K)
    for a, b in (((390, 560), (345, 330)), ((1210, 560), (1255, 330))):  # Ärmelnähte
        d.line(_sc([a, b]), fill=edge, width=2 * K)
    nh = 60 if back else 95
    d.ellipse(_box((640, 150, 960, 150 + nh * 2)), fill=bg)
    d.arc(_box((640, 150, 960, 150 + nh * 2)), 0, 180, fill=edge, width=5 * K)
    ov = Image.new("RGBA", c.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for x0, x1 in ((395, 520), (1090, 1205)):  # dezente Schatten für Stofffalten
        od.rectangle(_box((x0, 580, x1, 1345)), fill=(0, 0, 0, 14))
    c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(30 * K)))
    _place(c, design, 800, 790 if back else 520, 700 if back else 330, 760 if back else 380)
    return _finish(c)


def _mug(design):
    c = _canvas((233, 231, 226))
    _shadow(c, lambda d, f: d.ellipse(_box((420, 1150, 1090, 1260)), fill=f), 28)
    d = ImageDraw.Draw(c)
    d.arc(_box((960, 560, 1300, 1040)), -90, 90, fill=(205, 205, 200), width=80 * K)
    bx, by, bw, bh = 430, 420, 640, 760
    d.rounded_rectangle(_box((bx, by, bx + bw, by + bh)), radius=60 * K, fill=(247, 247, 245))
    g = Image.linear_gradient("L").rotate(90).resize((bw * K, bh * K))
    edge = ImageChops.difference(g, Image.new("L", g.size, 128)).point(lambda v: min(55, v * 55 // 128))
    m = Image.new("L", g.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, g.size[0] - 1, g.size[1] - 1], radius=60 * K, fill=255)
    shade = Image.new("RGBA", g.size, (0, 0, 0, 0))
    shade.putalpha(ImageChops.multiply(edge, m))
    c.alpha_composite(shade, (bx * K, by * K))
    _place(c, design, bx + bw // 2, by + bh // 2, 380, 420)
    return _finish(c)


def _phone_case(design):
    dark = _lum(design) > 100
    body = (30, 32, 36) if dark else (246, 246, 243)
    c = _canvas((228, 226, 236))
    rect = (540, 200, 1060, 1400)
    _shadow(c, lambda d, f: d.rounded_rectangle(_box((540, 236, 1060, 1436)), radius=96 * K, fill=f), 30)
    d = ImageDraw.Draw(c)
    d.rounded_rectangle(_box(rect), radius=96 * K, fill=body, outline=(120, 120, 120) if not dark else (70, 72, 78), width=4 * K)
    _place(c, design, 800, 860, 400, 560)
    d.rounded_rectangle(_box((580, 240, 790, 450)), radius=48 * K, fill=(24, 24, 27), outline=(60, 60, 64), width=3 * K)
    for cx, cy in ((642, 302), (730, 302), (686, 392)):
        d.ellipse(_box((cx - 30, cy - 30, cx + 30, cy + 30)), fill=(10, 10, 14), outline=(90, 90, 98), width=4 * K)
    return _finish(c)


def _phone_screen(design):
    c = _canvas((228, 226, 238))
    _shadow(c, lambda d, f: d.rounded_rectangle(_box((540, 214, 1060, 1454)), radius=110 * K, fill=f), 32)
    d = ImageDraw.Draw(c)
    d.rounded_rectangle(_box((540, 180, 1060, 1420)), radius=110 * K, fill=(14, 14, 16))
    sw, sh = 476 * K, 1196 * K
    scr = ImageOps.fit(design.convert("RGB"), (sw, sh), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=90 * K, fill=255)
    scr.putalpha(mask)
    c.alpha_composite(scr, (562 * K, 202 * K))
    d.rounded_rectangle(_box((735, 226, 865, 264)), radius=19 * K, fill=(0, 0, 0))
    return _finish(c)


def _poster(design):
    c = _canvas((236, 232, 226))
    _shadow(c, lambda d, f: d.rectangle(_box((425, 235, 1205, 1215)), fill=f), 30)
    d = ImageDraw.Draw(c)
    d.rectangle(_box((410, 200, 1190, 1180)), fill=(28, 28, 30))
    d.rectangle(_box((436, 226, 1164, 1154)), fill=(250, 250, 248))
    ax, ay, aw, ah = 510, 300, 580, 780
    if _has_alpha(design):
        panel = (24, 24, 28) if _lum(design) > 100 else (255, 255, 255)
        d.rectangle(_box((ax, ay, ax + aw, ay + ah)), fill=panel)
        _place(c, design, ax + aw // 2, ay + ah // 2, aw - 40, ah - 40)
    else:
        c.alpha_composite(ImageOps.fit(design.convert("RGB"), (aw * K, ah * K), Image.LANCZOS).convert("RGBA"), (ax * K, ay * K))
    return _finish(c)


def _template(kind, design):
    png, cfg = TEMPLATES / f"{kind}.png", TEMPLATES / f"{kind}.json"
    if not (png.exists() and cfg.exists()):
        return None
    try:
        x, y, w, h = json.loads(cfg.read_text())["box"]
        base = Image.open(png).convert("RGBA")
        d = design.convert("RGBA")
        d.thumbnail((w, h), Image.LANCZOS)
        base.alpha_composite(d, (x + (w - d.width) // 2, y + (h - d.height) // 2))
        return base.convert("RGB")
    except Exception:
        return None  # kaputte Vorlage: auf das eingebaute Mockup zurückfallen


class MockupService:
    DRAW = {"tee_front": lambda d: _tee(d, False), "tee_back": lambda d: _tee(d, True), "mug": _mug,
            "phone_case": _phone_case, "poster": _poster, "phone_screen": _phone_screen}

    def render(self, kind: str, design_path: Path) -> Path:
        design = Image.open(design_path).convert("RGBA")
        img = _template(kind, design) or self.DRAW[kind](design)
        path = ASSET_DIR / f"mockup_{kind}_{uuid.uuid4().hex[:8]}.png"
        img.save(path)
        return path
