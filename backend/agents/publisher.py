from services.llm_gateway import LLMGateway
from services.etsy_api import EtsyApiService

SYSTEM = ('Du bist Etsy-SEO-Experte. Antworte NUR mit JSON: {"title": str (max 140 Zeichen), '
          '"description": str, "tags": [genau 13 Strings, je max 20 Zeichen], "suggested_price": number (EUR)}. Schreibe auf Englisch. '
          'Das Download-Paket enthält genau __N__ Bild(er). Nenne diese Zahl korrekt und erfinde keine anderen Mengen.')


class PublisherAgent:
    def __init__(self, gateway: LLMGateway):
        self.gateway = gateway

    async def write_listing(self, provider: str, api_key: str, scout: dict, model=None, base_url=None, image_count: int = 1) -> dict:
        d = await self.gateway.generate_json(
            provider, api_key, SYSTEM.replace("__N__", str(image_count)),
            f"Nische: {scout['niche']}\nZielgruppe: {scout.get('target_audience','')}\nKonzept: {scout['design_concept']}\nAnzahl Bilder im Paket: {image_count}",
            model, base_url)
        for k in ("title", "description", "tags", "suggested_price"):
            if k not in d:
                raise ValueError(f"Listing-Antwort unvollständig: '{k}' fehlt")
        d["tags"] = EtsyApiService.clean_tags(d["tags"])
        return d
