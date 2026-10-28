import asyncio, base64, io, time, uuid
from pathlib import Path
from PIL import Image
from services.llm_gateway import LLMGateway
from services.image_generator import ASSET_DIR
from services.imaging import cutout, make_zip
from services import content_render as cr
from services.graphics import FONTS
from agents.scout import ScoutAgent
from agents.content import ThumbnailAgent, KitAgent
from agents.designer import DesignerAgent

NEG = "text, letters, watermark, blurry, low quality"
FONT_NAMES = {"impact": "Anton", "clean": "Bebas Neue", "tech": "Russo One", "comic": "Bangers"}


def url(p):
    return f"/static/assets/{p.name}"


def save_png(img, stem):
    p = ASSET_DIR / f"{stem}_{uuid.uuid4().hex[:8]}.png"
    img.save(p)
    return p


def save_jpg(img, stem):
    p = ASSET_DIR / f"{stem}_{uuid.uuid4().hex[:8]}.jpg"
    img.convert("RGB").save(p, quality=90)
    return p


def fallback_texture(kit_pal):
    d, p = kit_pal.get("dark", (12, 12, 20)), kit_pal.get("primary", (124, 58, 237))
    g = Image.linear_gradient("L").resize((1024, 1024))
    return Image.composite(Image.new("RGB", (1024, 1024), tuple(p)), Image.new("RGB", (1024, 1024), tuple(d)), g.point(lambda v: v * 6 // 10))


class ContentPipeline:
    """Content-Studio: Thumbnails, Streamer-Kit und Banner. Text und Layout setzt Pillow, die Bild-KI liefert nur Hintergrund, Charakter und Emblem."""

    def __init__(self, ws):
        self.ws = ws
        gw = LLMGateway()
        self.scout, self.thumb, self.kit = ScoutAgent(gw), ThumbnailAgent(gw), KitAgent(gw)
        self.designer = DesignerAgent()

    async def _status(self, agent, status, message):
        await self.ws.send("AGENT_STATUS", {"agent": agent, "status": status, "message": message})

    def _progress(self, agent):
        return lambda m: self._status(agent, "working", m)

    def _asset(self, ref):
        """Das Bild des Nutzers als Charakter oder Emblem: Hintergrund entfernen, wenn möglich."""
        p = ASSET_DIR / f"asset_{uuid.uuid4().hex[:8]}.png"
        Image.open(io.BytesIO(base64.b64decode(ref["b64"]))).convert("RGB").save(p)
        cutout(p)
        return p

    async def run(self, topic, provider, modules, keys, opts):
        llm_key, model, base_url = keys["llm_key"], keys.get("model") or None, keys.get("base_url") or None
        cfg, ref = keys["image"], keys.get("reference")
        lang, hint, variants = opts["language"], opts["hint"], opts["variants"]
        res = {"id": int(time.time() * 1000), "topic": topic, "vibe": "", "kit": None, "groups": [], "errors": {}, "warnings": []}
        files, kit_cache = [], {}
        try:
            style_text, asset = None, None
            first = "thumb" if "thumbnails" in modules else ("stream" if "streamer" in modules else "banner")
            if ref and ref["mode"] == "style":
                await self._status(first, "working", "Analysiere dein Referenzbild")
                style_text = await self.scout.describe_style(provider, llm_key, ref, model, base_url)
            elif ref and ref["mode"] == "asset":
                asset = await asyncio.to_thread(self._asset, ref)

            async def get_kit(agent):
                """Streamer-Paket und Banner teilen sich einen Look (ein Textmodell-Aufruf, Emblem und Hintergrund nur einmal)."""
                if "k" in kit_cache:
                    return kit_cache["k"]
                await self._status(agent, "working", "Entwerfe Look, Farben und Texte")
                d = await self.kit.run(provider, llm_key, topic, lang, hint, model, base_url, style_text)
                emblem = tex = None
                if asset:
                    emblem = Image.open(asset).convert("RGBA")
                else:
                    try:
                        p = (await self.designer.render([d["emblem_full"]], NEG, cfg, self._progress(agent), ref if ref and ref["mode"] == "direct" else None, "Emblem"))[0]
                        cutout(p)
                        emblem = Image.open(p).convert("RGBA")
                    except Exception as e:
                        res["warnings"].append(f"Emblem konnte nicht erzeugt werden, das Kit entsteht ohne Emblem ({str(e)[:120]})")
                try:
                    p = (await self.designer.render([d["tex_full"]], NEG, cfg, self._progress(agent), ref if ref and ref["mode"] == "direct" else None, "Hintergrund"))[0]
                    tex = Image.open(p).convert("RGB")
                except Exception as e:
                    res["warnings"].append(f"Hintergrundtextur konnte nicht erzeugt werden, es wird ein Farbverlauf genutzt ({str(e)[:120]})")
                kit = cr.make_kit(d, emblem, tex or Image.new("RGB", (8, 8)))
                if tex is None:
                    kit["tex"] = fallback_texture(kit["pal"])
                kit_cache["k"], kit_cache["d"] = kit, d
                res["kit"] = {"name": kit["name"], "tagline": kit["tagline"], "palette": ["#%02X%02X%02X" % kit["pal"][k] for k in ("primary", "secondary", "accent", "dark", "light")],
                              "font": FONT_NAMES[kit["font"]], "frame": kit["frame"]}
                return kit

            if "thumbnails" in modules:
                try:
                    await self._status("thumb", "working", "Analysiere den Vibe und entwerfe Varianten")
                    t = await self.thumb.run(provider, llm_key, topic, variants, lang, hint, model, base_url, style_text)
                    res["vibe"] = t["vibe"]
                    bg_p = (await self.designer.render([t["bg_full"]], NEG, cfg, self._progress("thumb"), ref if ref and ref["mode"] == "direct" else None, "Hintergrund"))[0]
                    bg = Image.open(bg_p).convert("RGB")
                    chars = []
                    if asset:
                        chars = [Image.open(asset).convert("RGBA")] * variants
                    else:
                        try:
                            paths = await self.designer.render(t["char_full"], NEG, cfg, self._progress("thumb"), ref if ref and ref["mode"] == "direct" else None, "Charakter")
                            for p in paths:
                                if not cutout(p):
                                    res["warnings"].append("Beim Charakter konnte der Hintergrund nicht sauber entfernt werden.")
                            chars = [Image.open(paths[min(i, len(paths) - 1)]).convert("RGBA") for i in range(variants)]
                        except Exception as e:
                            res["warnings"].append(f"Charakter konnte nicht erzeugt werden, die Thumbnails entstehen ohne ({str(e)[:120]})")
                    items = []
                    await self._status("thumb", "working", "Setze Text und Layout")
                    for i, v in enumerate(t["variants"]):
                        for fmt in opts["formats"]:
                            spec = {**v, "accent": t["accent"], "text": t["text"], "font_style": t["font_style"], "text_position": t["text_position"]}
                            img = await asyncio.to_thread(cr.thumbnail, bg, chars[i] if chars else None, spec, fmt)
                            p = save_jpg(img, f"thumb_{fmt}")
                            files.append((f"thumbnails/variante{i + 1}_{fmt}.jpg", p))
                            items.append({"label": f"Variante {i + 1}: {v['headline']} ({cr.FORMATS[fmt][0]})", "url": url(p), "w": img.width, "h": img.height, "mini": True})
                    res["groups"].append({"title": "Thumbnails", "items": items})
                    await self._status("thumb", "done", f"{len(items)} Thumbnail(s) fertig")
                except Exception as e:
                    res["errors"]["thumbnails"] = str(e)[:300]
                    await self._status("thumb", "error", str(e)[:300])

            if "streamer" in modules:
                try:
                    kit = await get_kit("stream")
                    d = kit_cache["d"]
                    await self._status("stream", "working", "Zeichne Szenen, Overlay, Panels und Alerts")
                    sub = f'{kit["name"]}  ·  {kit["tagline"]}' if kit["tagline"] else kit["name"]
                    groups = {"Streamer: Szenen": [], "Streamer: Overlay und Chat": [], "Streamer: Panels": [], "Streamer: Alerts": []}

                    def add(group, folder, name, label, img, png=True):
                        p = save_png(img, f"s_{name}") if png else save_jpg(img, f"s_{name}")
                        files.append((f"streamer/{folder}/{name}.png", p))
                        groups[group].append({"label": label, "url": url(p), "w": img.width, "h": img.height})

                    for key, label in (("starting", "Starting Soon"), ("brb", "Be Right Back"), ("offline", "Offline")):
                        add("Streamer: Szenen", "szenen", f"szene_{key}", label, await asyncio.to_thread(cr.scene, kit, d["scenes"][key], sub))
                    add("Streamer: Overlay und Chat", "overlay", "overlay_hauptbild", "Overlay (transparent, 1920x1080)", await asyncio.to_thread(cr.overlay, kit))
                    add("Streamer: Overlay und Chat", "overlay", "chat_box", "Chat-Box (transparent)", await asyncio.to_thread(cr.chat_box, kit))
                    for i, title in enumerate(d["panels"], 1):
                        add("Streamer: Panels", "panels", f"panel_{i}", title, await asyncio.to_thread(cr.panel, kit, title))
                    for key, label in (("follow", "Follower"), ("sub", "Abo"), ("donation", "Spende")):
                        add("Streamer: Alerts", "alerts", f"alert_{key}", f"Alert {label}", await asyncio.to_thread(cr.alert, kit, d["alerts"][key]))
                    res["groups"] += [{"title": k, "items": v} for k, v in groups.items()]
                    await self._status("stream", "done", f"{sum(len(v) for v in groups.values())} Grafiken fertig")
                except Exception as e:
                    res["errors"]["streamer"] = str(e)[:300]
                    await self._status("stream", "error", str(e)[:300])

            if "banners" in modules:
                try:
                    kit = await get_kit("banner")
                    await self._status("banner", "working", "Zeichne Banner im gleichen Look")
                    items = []
                    for key in opts["banners"]:
                        img = await asyncio.to_thread(cr.banner, kit, key)
                        p = save_jpg(img, f"banner_{key}")
                        files.append((f"banner/{key}.jpg", p))
                        items.append({"label": f"{cr.BANNERS[key][0]} ({img.width}x{img.height})", "url": url(p), "w": img.width, "h": img.height})
                    res["groups"].append({"title": "Banner und Header", "items": items})
                    await self._status("banner", "done", f"{len(items)} Banner fertig")
                except Exception as e:
                    res["errors"]["banner"] = str(e)[:300]
                    await self._status("banner", "error", str(e)[:300])

            if not res["groups"]:
                await self.ws.send("RUN_FAILED", {"stage": "content", "error": " | ".join(res["errors"].values()) or "Nichts wurde erzeugt."})
            else:
                fonts = sorted({FONT_NAMES[kit_cache["k"]["font"]]} if "k" in kit_cache else set())
                info = {"topic": topic, "vibe": res["vibe"], "kit": res["kit"], "hinweis": "Schriften: " + (", ".join(fonts) or "siehe Thumbnails") + " (SIL Open Font License)"}
                res["zip_url"] = url(make_zip(files, info))
                await self.ws.send("CONTENT_RESULT", res)
        except Exception as e:
            await self.ws.send("RUN_FAILED", {"stage": "content", "error": str(e)[:300]})
        finally:
            await self.ws.send("RUN_FINISHED", {})
