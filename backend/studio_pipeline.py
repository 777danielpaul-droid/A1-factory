import time
from services.llm_gateway import LLMGateway
from services.imaging import cutout, brand_board, make_zip
from services.mockups import MockupService, LABELS
from services.shopify_api import ShopifyService
from agents.scout import ScoutAgent
from agents.merch import MerchAgent
from agents.brand import BrandAgent
from agents.designer import DesignerAgent

NEG = "text, letters, watermark, blurry, low quality, photo background"


def url(p):
    return f"/static/assets/{p.name}"


class StudioPipeline:
    """Marketing-Studio: Merch-Designs, Brand-Kit und Mockups. Jedes Modul läuft für sich, ein Fehler stoppt die anderen nicht."""

    def __init__(self, ws):
        self.ws = ws
        gw = LLMGateway()
        self.scout, self.merch, self.brand = ScoutAgent(gw), MerchAgent(gw), BrandAgent(gw)
        self.designer, self.mock = DesignerAgent(), MockupService()

    async def _status(self, agent, status, message):
        await self.ws.send("AGENT_STATUS", {"agent": agent, "status": status, "message": message})

    def _progress(self, agent):
        return lambda m: self._status(agent, "working", m)

    async def run(self, niche, provider, modules, keys, variants=2):
        llm_key, model, base_url = keys["llm_key"], keys.get("model") or None, keys.get("base_url") or None
        cfg, ref = keys["image"], keys.get("reference")
        direct = ref if ref and ref["mode"] == "direct" else None
        res = {"id": int(time.time() * 1000), "niche": niche, "provider": provider, "merch": None, "brand": None, "mockups": [], "errors": {}}
        files, designs, mock_paths = [], {}, {}
        try:
            style_text = None
            if ref and ref["mode"] == "style":
                await self._status("merch" if "merch" in modules else "brand", "working", "Analysiere dein Referenzbild")
                style_text = await self.scout.describe_style(provider, llm_key, ref, model, base_url)

            if "merch" in modules:
                try:
                    await self._status("merch", "working", "Entwerfe Front-Logo und Backprint")
                    m = await self.merch.run(provider, llm_key, niche, model, base_url, style_text)
                    paths = await self.designer.render([m["front_full"], m["back_full"]], NEG, cfg, self._progress("merch"), direct, "Merch-Motiv")
                    warn = None
                    for p in paths:
                        if not cutout(p):
                            warn = "Der Hintergrund konnte nicht sauber entfernt werden. Das Bild hat noch einen Hintergrund."
                    designs["front"], designs["back"] = paths[0], paths[1] if len(paths) > 1 else None
                    files += [("merch/front_logo.png", paths[0])] + ([("merch/backprint.png", paths[1])] if len(paths) > 1 else [])
                    res["merch"] = {k: m.get(k) for k in ("concept", "style", "slogan", "print_notes")}
                    res["merch"].update(front_url=url(paths[0]), back_url=url(paths[1]) if len(paths) > 1 else None, warning=warn)
                    await self._status("merch", "done", "Front-Logo und Backprint fertig" if len(paths) > 1 else "Nur das Front-Logo wurde fertig")
                except Exception as e:
                    res["errors"]["merch"] = str(e)[:300]
                    await self._status("merch", "error", str(e)[:300])

            if "brand" in modules:
                try:
                    await self._status("brand", "working", "Entwerfe Marke, Farben und Schriften")
                    b = await self.brand.run(provider, llm_key, niche, variants, model, base_url, style_text)
                    logos = await self.designer.render(b["logo_full"], NEG, cfg, self._progress("brand"), direct, "Logo")
                    for p in logos:
                        cutout(p)
                    pattern = None
                    try:
                        pattern = (await self.designer.render([b["pattern_full"]], NEG, cfg, self._progress("brand"), direct, "Muster"))[0]
                    except Exception as e:
                        res["errors"]["pattern"] = str(e)[:200]
                    board = brand_board(b, logos[0], pattern)
                    files += [(f"brand/logo_{i + 1}.png", p) for i, p in enumerate(logos)] + [("brand/brand_board.png", board)]
                    if pattern:
                        files.append(("brand/pattern.png", pattern))
                    designs["logo"], designs["pattern"] = logos[0], pattern
                    res["brand"] = {"brand_name": b["brand_name"], "tagline": b["tagline"], "palette": b["palette"], "fonts": b["fonts"],
                                    "voice": b["voice"], "logo_urls": [url(p) for p in logos],
                                    "pattern_url": url(pattern) if pattern else None, "board_url": url(board)}
                    await self._status("brand", "done", f"{b['brand_name']}: {len(logos)} Logo(s), {len(b['palette'])} Farben")
                except Exception as e:
                    res["errors"]["brand"] = str(e)[:300]
                    await self._status("brand", "error", str(e)[:300])

            if "mockups" in modules:
                try:
                    await self._status("mockup", "working", "Lege Designs auf Produkte")
                    front, back = designs.get("front") or designs.get("logo"), designs.get("back") or designs.get("pattern") or designs.get("logo")
                    plan = [(k, d) for k, d in (("tee_front", front), ("tee_back", back), ("mug", front), ("phone_case", back), ("poster", back)) if d]
                    if not plan:
                        raise ValueError("Für Mockups braucht es Merch- oder Brand-Ergebnisse. Aktiviere eines der beiden Module.")
                    for kind, d in plan:
                        mp = self.mock.render(kind, d)
                        mock_paths[kind] = mp
                        files.append((f"mockups/{kind}.png", mp))
                        res["mockups"].append({"kind": kind, "label": LABELS[kind], "url": url(mp)})
                    await self._status("mockup", "done", f"{len(plan)} Mockups fertig")
                except Exception as e:
                    res["errors"]["mockups"] = str(e)[:300]
                    await self._status("mockup", "error", str(e)[:300])

            res["shopify"] = []
            if keys.get("shopify_on") and (res["merch"] or res["brand"] or res["mockups"]):
                await self._status("mockup" if "mockups" in modules else ("merch" if "merch" in modules else "brand"), "working", "Lege Shopify-Entwürfe an")
                concept = (res["merch"] or {}).get("concept") or (res["brand"] or {}).get("brand_name") or niche
                vendor = (res["brand"] or {}).get("brand_name", "")
                text = "\n\n".join(x for x in [(res["merch"] or {}).get("concept"), (res["merch"] or {}).get("slogan") and f'„{res["merch"]["slogan"]}“', (res["brand"] or {}).get("tagline")] if x) or niche
                tags = [t for t in dict.fromkeys([niche, concept, (res["merch"] or {}).get("style") or ""] ) if t]
                shop_plan = [("T-Shirt", 24.90, [mock_paths.get("tee_front"), mock_paths.get("tee_back"), designs.get("front"), designs.get("back")]),
                             ("Tasse", 14.90, [mock_paths.get("mug"), designs.get("front")]),
                             ("Handyhülle", 19.90, [mock_paths.get("phone_case")]),
                             ("Poster", 12.90, [mock_paths.get("poster")])]
                svc = ShopifyService(keys["shopify"])
                for name, price, imgs in shop_plan:
                    imgs = [i for i in imgs if i]
                    if not imgs or (name != "T-Shirt" and not mock_paths):
                        continue
                    title = f"{concept} {name}"[:120]
                    try:
                        r = await svc.create_draft(title, text, tags + [name, "Merch"], price, imgs, name, vendor=vendor)
                        res["shopify"].append({"title": title, "url": r["url"], "error": r["warning"]})
                    except Exception as e:
                        res["shopify"].append({"title": title, "url": None, "error": str(e)[:300]})
                        if "abgelehnt" in str(e) or "Anmeldung" in str(e):
                            break  # gleiche Ursache bei allen weiteren Produkten

            if not (res["merch"] or res["brand"] or res["mockups"]):
                await self.ws.send("RUN_FAILED", {"stage": "studio", "error": " | ".join(res["errors"].values()) or "Nichts wurde erzeugt."})
            else:
                info = {"niche": niche, "merch": res["merch"] and {k: v for k, v in res["merch"].items() if not k.endswith("_url")},
                        "brand": res["brand"] and {k: res["brand"][k] for k in ("brand_name", "tagline", "palette", "fonts", "voice")}}
                res["zip_url"] = url(make_zip(files, info))
                await self.ws.send("STUDIO_RESULT", res)
        except Exception as e:
            await self.ws.send("RUN_FAILED", {"stage": "studio", "error": str(e)[:300]})
        finally:
            await self.ws.send("RUN_FINISHED", {})
