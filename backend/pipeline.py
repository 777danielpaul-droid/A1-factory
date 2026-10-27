import time
from services.llm_gateway import LLMGateway
from services.etsy_api import EtsyApiService
from services.mockups import MockupService
from services.shopify_api import ShopifyService
from agents.scout import ScoutAgent
from agents.designer import DesignerAgent
from agents.publisher import PublisherAgent


class AgentFactoryPipeline:
    """`ws` sendet nur an den Nutzer, der den Lauf gestartet hat. Keys leben nur für die Dauer des Laufs."""

    def __init__(self, ws):
        self.ws = ws
        gw = LLMGateway()
        self.scout, self.designer, self.publisher = ScoutAgent(gw), DesignerAgent(), PublisherAgent(gw)

    async def _status(self, agent, status, message):
        await self.ws.send("AGENT_STATUS", {"agent": agent, "status": status, "message": message})

    async def run(self, category, provider, publish, keys: dict, count: int = 1):
        stage = "scout"
        llm_key, model, base_url = keys["llm_key"], keys.get("model") or None, keys.get("base_url") or None
        try:
            ref = keys.get("reference")
            style_text = None
            if ref and ref["mode"] == "style":
                await self._status("scout", "working", "Analysiere dein Referenzbild")
                style_text = await self.scout.describe_style(provider, llm_key, ref, model, base_url)
            await self._status("scout", "working", f"Analysiere „{category}“ mit {provider}")
            scout = await self.scout.run(provider, llm_key, category, model, base_url, count, style_text)
            await self._status("scout", "done", f"Idee: {scout['niche']}")

            stage = "designer"
            await self._status("designer", "working", f"Generiere {count} Motiv(e)")
            design = await self.designer.run(scout, keys["image"],
                                              lambda m: self._status("designer", "working", m),
                                              ref if ref and ref["mode"] == "direct" else None)
            n = len(design["local_paths"])
            mockup_paths = []
            if keys.get("mockups"):
                await self._status("designer", "working", "Rendere Mockups (Poster, Handy)")
                try:
                    mk = MockupService()
                    for path in design["local_paths"][:2]:
                        mockup_paths += [mk.render("poster", path), mk.render("phone_screen", path)]
                except Exception as e:
                    await self._status("designer", "working", f"Mockups übersprungen: {e}")
            await self._status("designer", "done", f"{n} Bild(er) fertig")

            stage = "publisher"
            await self._status("publisher", "working", "Schreibe Listing")
            listing = await self.publisher.write_listing(provider, llm_key, scout, model, base_url, n)
            etsy, etsy_error = None, None
            if publish:
                await self._status("publisher", "working", "Lege Etsy-Entwurf an")
                svc = EtsyApiService(keys["etsy"])
                try:
                    etsy = await svc.create_draft_listing(listing, design["local_paths"], mockup_paths)
                except Exception as e:  # Listing bleibt nutzbar, auch wenn Etsy scheitert
                    etsy_error = str(e)
                if svc.rotated:  # Etsy rotiert Refresh-Tokens: neue Werte zurück an den Browser
                    await self.ws.send("ETSY_TOKENS", {"access_token": svc.access_token, "refresh_token": svc.refresh_token})
            shop, shop_error = None, None
            if keys.get("shopify_on"):
                await self._status("publisher", "working", "Lege Shopify-Entwurf an")
                try:
                    shop = await ShopifyService(keys["shopify"]).create_draft(
                        listing["title"], listing["description"], listing["tags"], listing["suggested_price"],
                        mockup_paths + design["local_paths"], "Digital Download", digital=True)
                except Exception as e:
                    shop_error = str(e)
            msg = "Entwurf bei Etsy angelegt" if etsy else (f"Etsy-Fehler: {etsy_error}" if etsy_error else "Listing erstellt (ohne Etsy)")
            if shop:
                msg += " · Shopify-Entwurf angelegt" + (f" ({shop['warning']})" if shop["warning"] else "")
            if shop_error:
                msg += f" · Shopify-Fehler: {shop_error}"
            await self._status("publisher", "error" if (etsy_error or shop_error) else "done", msg)

            await self.ws.send("PRODUCT_CREATED", {
                "id": int(time.time() * 1000), "provider": provider, "niche": scout["niche"],
                "title": listing["title"], "description": listing["description"], "tags": listing["tags"],
                "price": listing["suggested_price"], "image_url": design["image_urls"][0], "image_urls": design["image_urls"], "mockup_urls": [f"/static/assets/{p.name}" for p in mockup_paths], "style_description": scout.get("style_description"),
                "etsy_url": etsy["url"] if etsy else None, "etsy_error": etsy_error,
                "shopify_url": shop["url"] if shop else None, "shopify_error": shop_error})
        except Exception as e:
            await self._status(stage, "error", str(e)[:300])
            await self.ws.send("RUN_FAILED", {"stage": stage, "error": str(e)[:300]})
        finally:
            await self.ws.send("RUN_FINISHED", {})
