"""Bildhilfen ohne externe Dienste: Hintergrund entfernen, Brand-Board zeichnen, ZIP-Paket schnüren."""
import json, uuid, zipfile
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont
from services.image_generator import ASSET_DIR


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # ältere Pillow-Version
        return ImageFont.load_default()


def cutout(path: Path) -> bool:
    """Entfernt einen einfarbigen Hintergrund (Farbe aus den Ecken). Gibt False zurück, wenn er nicht einfarbig genug ist."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    cols = [img.getpixel(p) for p in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3))]
    if max(abs(a[i] - b[i]) for a in cols for b in cols for i in range(3)) > 40:
        return False
    bg = tuple(sum(c[i] for c in cols) // 4 for i in range(3))
    r, g, b = ImageChops.difference(img, Image.new("RGB", img.size, bg)).split()
    alpha = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: max(0, min(255, (v - 25) * 255 // 60)))
    if alpha.getbbox() is None:
        return False
    out = img.convert("RGBA")
    out.putalpha(alpha)
    out.save(path, format="PNG")
    return True


def _lum(hex_: str) -> float:
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b


def brand_board(brand: dict, logo: Path | None, pattern: Path | None) -> Path:
    """Einseitiges Marken-Blatt: Name, Logo, Farben mit Hex-Codes, Schriften, Muster."""
    W, H = 1600, 1100
    img = Image.new("RGB", (W, H), (245, 244, 240))
    d = ImageDraw.Draw(img)
    d.text((70, 60), str(brand.get("brand_name", ""))[:40], fill=(25, 27, 31), font=font(78))
    d.text((72, 160), str(brand.get("tagline", ""))[:90], fill=(90, 92, 98), font=font(32))
    if logo and logo.exists():
        lg = Image.open(logo).convert("RGBA"); lg.thumbnail((380, 380))
        img.paste(lg, (W - 70 - lg.width, 50), lg)
    pal = brand.get("palette", [])[:5]
    for i, c in enumerate(pal):
        x = 70 + i * 300
        d.rectangle([x, 450, x + 270, 640], fill=c["hex"], outline=(200, 200, 196))
        d.text((x, 655), c["hex"], fill=(25, 27, 31), font=font(30))
        d.text((x, 695), f'{c.get("name", "")[:20]} ({c.get("role", "")[:14]})', fill=(90, 92, 98), font=font(22))
    d.text((70, 380), "Farben", fill=(25, 27, 31), font=font(34))
    d.text((70, 780), "Schriften", fill=(25, 27, 31), font=font(34))
    for i, f in enumerate(brand.get("fonts", [])[:3]):
        d.text((70, 835 + i * 55), f'{f.get("role", "")}: {f.get("name", "")}', fill=(25, 27, 31), font=font(30))
    if pattern and pattern.exists():
        pt = Image.open(pattern).convert("RGB").resize((330, 330))
        img.paste(pt, (W - 70 - 330, 740))
        d.text((W - 70 - 330, 705), "Muster", fill=(25, 27, 31), font=font(26))
    path = ASSET_DIR / f"brandboard_{uuid.uuid4().hex[:10]}.png"
    img.save(path)
    return path


def make_zip(files: list, info: dict) -> Path:
    """files = [(Name im ZIP, Pfad)]. info landet als brand_kit.json im Paket."""
    path = ASSET_DIR / f"studio_{uuid.uuid4().hex[:10]}.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, p in files:
            if Path(p).exists():
                z.write(p, name)
        z.writestr("brand_kit.json", json.dumps(info, ensure_ascii=False, indent=2))
    return path
