"""Fertige Layouts für Thumbnails, Streamer-Kit und Banner. Alles wird lokal mit Pillow gezeichnet."""
from PIL import Image, ImageDraw, ImageEnhance
from services.graphics import (add_glow, cover, darken, draw_headline, frame, glow_text, rgb, stroke_around)

FORMATS = {"yt": ("YouTube 16:9", (1280, 720)), "square": ("Quadrat 1:1", (1080, 1080)), "story": ("Hochkant 9:16", (1080, 1920))}
BANNERS = {  # Größe und sicherer Bereich (x, y, Breite, Höhe) als Anteile; X und LinkedIn lassen links Platz für das Profilbild
    "youtube": ("YouTube-Kanalbanner", (2560, 1440), (507, 508, 1546, 423)),
    "x": ("X/Twitter-Header", (1500, 500), (440, 50, 1000, 400)),
    "discord": ("Discord-Banner", (960, 540), (80, 70, 800, 400)),
    "linkedin": ("LinkedIn-Banner", (1584, 396), (470, 40, 1000, 316)),
}


def make_kit(d: dict, emblem, tex):
    p = d.get("palette") or {}
    pal = {"primary": rgb(p.get("primary"), (124, 58, 237)), "secondary": rgb(p.get("secondary"), (14, 165, 233)),
           "accent": rgb(p.get("accent"), (250, 204, 21)), "dark": rgb(p.get("dark"), (12, 12, 20)), "light": rgb(p.get("light"), (245, 245, 250))}
    return {"name": d["channel_name"], "tagline": d.get("tagline", ""), "pal": pal, "font": d["font_style"], "frame": d["frame_style"],
            "emblem": emblem, "tex": tex}


def _emblem(canvas, kit, cx, cy, h, glow=True):
    e = kit["emblem"]
    if e is None:
        return
    e = e.copy()
    e.thumbnail((int(h * 1.6), int(h)), Image.LANCZOS)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.alpha_composite(e, (int(cx - e.width / 2), int(cy - e.height / 2)))
    if glow:
        add_glow(canvas, layer, kit["pal"]["primary"], max(8, h // 14), 2)
    canvas.alpha_composite(layer)


def _bg(kit, w, h, dim=0.55, tint=110):
    c = ImageEnhance.Brightness(cover(kit["tex"], w, h)).enhance(dim).convert("RGBA")
    c.alpha_composite(Image.new("RGBA", (w, h), tuple(kit["pal"]["dark"]) + (tint,)))
    return c


# ---------------------------------------------------------------- Thumbnails
def _layout(fmt, side, W, H):
    if fmt == "yt":
        if side == "right":
            return (W - int(W * .58), 50, W - 50, H - 50), (0, 0, int(W * .50), H), "left", "right"
        return (50, 50, int(W * .58), H - 50), (int(W * .50), 0, W, H), "left", "left"
    if fmt == "square":
        return (60, 50, W - 60, int(H * .40)), (int(W * .10), int(H * .43), int(W * .90), H), "center", "top"
    return (70, 110, W - 70, int(H * .34)), (0, int(H * .38), W, H), "center", "top"


def thumbnail(bg, char, spec: dict, fmt: str):
    W, H = FORMATS[fmt][1]
    accent, text_col = rgb(spec.get("accent"), (255, 221, 0)), rgb(spec.get("text"), (255, 255, 255))
    c = ImageEnhance.Contrast(ImageEnhance.Color(cover(bg, W, H)).enhance(1.3)).enhance(1.12).convert("RGBA")
    tbox, cbox, align, dark = _layout(fmt, spec.get("text_position", "left"), W, H)
    c = darken(c, dark, 175)
    if char is not None:
        ch = char.crop(char.getchannel("A").getbbox() or (0, 0, char.width, char.height))
        bw, bh = cbox[2] - cbox[0], cbox[3] - cbox[1]
        k = min(bw / ch.width, bh / ch.height)
        ch = ch.resize((max(1, int(ch.width * k)), max(1, int(ch.height * k))), Image.LANCZOS)
        ch = stroke_around(ch, (255, 255, 255), max(6, H // 90))
        layer = Image.new("RGBA", c.size, (0, 0, 0, 0))
        layer.alpha_composite(ch, (cbox[0] + (bw - ch.width) // 2, cbox[3] - ch.height))
        add_glow(c, layer, accent, max(12, H // 28), 2)
        c.alpha_composite(layer)
    x0, y0, x1, y1 = tbox
    sub = str(spec.get("subline") or "").strip()
    if sub:
        sh = int(min(W, H) * (0.10 if fmt == "yt" else 0.075))
        sb = (x0, y1 - sh, x1, y1)
        hb = draw_headline(Image.new("RGBA", c.size), sub, sb, spec["font_style"], (20, 20, 20), max_lines=1, max_size=sh, stroke_ratio=0.0, shadow=False,
                           align=align, valign="top")
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((hb[0] - 18, hb[1] - 6, hb[2] + 18, hb[3] + 8 if hb[3] > hb[1] else hb[1] + sh), radius=14, fill=accent)
        draw_headline(c, sub, sb, spec["font_style"], (20, 20, 20), max_lines=1, max_size=sh, stroke_ratio=0.0, shadow=False, align=align, valign="top")
        tbox = (x0, y0, x1, y1 - sh - 24)
    draw_headline(c, spec["headline"], tbox, spec["font_style"], text_col, accent, spec.get("highlight", ""), align=align, max_lines=3,
                  max_size=int(H * (0.42 if fmt == "yt" else 0.30)), stroke_ratio=0.07)
    return c.convert("RGB")


# ---------------------------------------------------------------- Streamer-Kit
def scene(kit, headline, sub):
    W, H = 1920, 1080
    P = kit["pal"]
    c = _bg(kit, W, H)
    frame(c, (50, 50, W - 50, H - 50), kit["frame"], P["primary"], P["accent"], 8)
    _emblem(c, kit, W // 2, 330, 360)
    glow_text(c, headline, (160, 560, W - 160, 810), kit["font"], P["light"], P["primary"], align="center", max_lines=2, max_size=200)
    draw_headline(c, sub, (300, 850, W - 300, 930), kit["font"], P["accent"], align="center", max_lines=1, max_size=62, stroke_ratio=0.05)
    return c.convert("RGB")


def overlay(kit):
    W, H = 1920, 1080
    P, c = kit["pal"], Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    frame(c, (20, 20, W - 20, H - 20), kit["frame"], P["primary"], P["accent"], 6)
    frame(c, (40, 700, 520, 970), kit["frame"], P["primary"], P["accent"], 6)
    frame(c, (40, 985, 520, 1045), kit["frame"], P["primary"], P["accent"], 4, fill=tuple(P["dark"]) + (235,))
    draw_headline(c, kit["name"], (60, 990, 500, 1040), kit["font"], P["light"], max_lines=1, max_size=44, stroke_ratio=0.03, shadow=False, align="center")
    frame(c, (1480, 60, W - 40, 740), kit["frame"], P["primary"], P["accent"], 6, fill=tuple(P["dark"]) + (110,))
    frame(c, (1480, 60, W - 40, 125), kit["frame"], P["primary"], P["accent"], 4, fill=tuple(P["dark"]) + (235,))
    draw_headline(c, "CHAT", (1500, 62, W - 60, 123), kit["font"], P["light"], max_lines=1, max_size=46, stroke_ratio=0.03, shadow=False, align="center")
    _emblem(c, kit, 110, 110, 120)
    return c


def chat_box(kit):
    W, H, P = 600, 900, kit["pal"]
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    frame(c, (12, 12, W - 12, H - 12), kit["frame"], P["primary"], P["accent"], 6, fill=tuple(P["dark"]) + (120,))
    frame(c, (12, 12, W - 12, 90), kit["frame"], P["primary"], P["accent"], 4, fill=tuple(P["dark"]) + (240,))
    draw_headline(c, "CHAT", (30, 14, W - 30, 88), kit["font"], P["light"], max_lines=1, max_size=56, stroke_ratio=0.03, shadow=False, align="center")
    return c


def panel(kit, title):
    W, H, P = 320, 140, kit["pal"]
    c = _bg(kit, W, H, 0.45, 150)
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, 14, H), fill=tuple(P["accent"]))
    d.rectangle((0, 0, W - 1, H - 1), outline=tuple(P["primary"]), width=4)
    draw_headline(c, title, (30, 14, W - 16, H - 14), kit["font"], P["light"], max_lines=2, max_size=62, stroke_ratio=0.04, align="center")
    return c.convert("RGB")


def alert(kit, text, sub="USERNAME"):
    W, H, P = 900, 320, kit["pal"]
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    frame(c, (12, 12, W - 12, H - 12), kit["frame"], P["primary"], P["accent"], 6, fill=tuple(P["dark"]) + (238,))
    _emblem(c, kit, 150, H // 2, 210)
    draw_headline(c, text, (290, 36, W - 36, 190), kit["font"], P["light"], P["accent"], text.split()[-1], max_lines=2, max_size=120, stroke_ratio=0.04, shadow=False)
    draw_headline(c, sub, (290, 205, W - 36, 285), kit["font"], P["accent"], max_lines=1, max_size=64, stroke_ratio=0.03, shadow=False)
    return c


# ---------------------------------------------------------------- Banner
def banner(kit, key):
    W, H = BANNERS[key][1]
    sx, sy, sw, sh = BANNERS[key][2]
    P = kit["pal"]
    c = darken(_bg(kit, W, H, 0.62, 60), "left", 150)
    d = ImageDraw.Draw(c)
    d.rectangle((0, H - max(8, H // 28), W, H), fill=tuple(P["primary"]))
    d.rectangle((0, H - max(8, H // 28) - max(3, H // 90), W, H - max(8, H // 28)), fill=tuple(P["accent"]))
    ex = 0
    if kit["emblem"] is not None:
        eh = int(sh * 0.92)
        _emblem(c, kit, sx + eh * 0.55, sy + sh / 2, eh)
        ex = int(eh * 1.2) + int(sw * 0.03)
    tx0 = sx + ex
    draw_headline(c, kit["name"], (tx0, sy, sx + sw, sy + int(sh * 0.66)), kit["font"], P["light"], P["accent"], kit["name"].split()[-1], max_lines=2,
                  max_size=int(sh * 0.9), stroke_ratio=0.05, valign="middle")
    if kit["tagline"]:
        draw_headline(c, kit["tagline"], (tx0, sy + int(sh * 0.70), sx + sw, sy + sh), kit["font"], P["accent"], max_lines=1,
                      max_size=int(sh * 0.2), stroke_ratio=0.03, shadow=False, valign="top")
    return c.convert("RGB")
