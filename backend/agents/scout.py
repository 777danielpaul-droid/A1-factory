from services.llm_gateway import LLMGateway

SYSTEM = ('Du bist Trend-Analyst für Etsy-Digitalprodukte. Das Produkt ist ein Paket aus genau __N__ Bild(ern). '
          'Antworte NUR mit JSON: {"niche": str, "target_audience": str, "style_keywords": [str], "design_concept": str, '
          '"image_prompts": [genau __N__ Strings, englisch, jeweils ein anderes Motiv im gleichen Stil, ohne Text im Bild], '
          '"negative_prompt": str}')


STYLE_SYSTEM = ('Du bist Art-Director. Beschreibe den visuellen Stil des Referenzbilds so präzise, dass ein Bildgenerator ihn nachbilden kann: '
                'Technik oder Medium, Farbpalette (konkrete Farbnamen), Linienführung, Licht, Komposition, Stimmung, typische Motive. '
                'Maximal 120 Wörter, auf Englisch, als zusammenhängender Text ohne Aufzählung.')


class ScoutAgent:
    def __init__(self, gateway: LLMGateway):
        self.gateway = gateway

    async def describe_style(self, provider, api_key, ref: dict, model=None, base_url=None) -> str:
        text = await self.gateway.generate_text(provider, api_key, STYLE_SYSTEM, "Beschreibe den Stil dieses Bildes.", model, base_url, image=ref)
        if len(text) < 20:
            raise ValueError("Die Stil-Beschreibung des Referenzbilds war leer.")
        return text[:1200]

    async def run(self, provider: str, api_key: str, category: str, model=None, base_url=None, count: int = 1, style_text: str | None = None) -> dict:
        system = SYSTEM.replace("__N__", str(count))
        if style_text:
            system += (" Das Paket muss sich eng an diesem Referenzstil des Nutzers orientieren: " + style_text +
                       " Jeder image_prompt muss diesen Stil ausdrücklich beschreiben (Medium, Farben, Licht, Komposition).")
        data = await self.gateway.generate_json(provider, api_key, system,
                                                f"Finde eine konkrete, verkaufbare Produktidee in: {category}", model, base_url)
        for k in ("niche", "design_concept"):
            if not data.get(k):
                raise ValueError(f"Scout-Antwort unvollständig: '{k}' fehlt")
        prompts = [p.strip() for p in (data.get("image_prompts") or [data.get("image_prompt")]) if isinstance(p, str) and p.strip()]
        if not prompts:
            raise ValueError("Scout-Antwort unvollständig: keine Bild-Prompts")
        while len(prompts) < count:  # Modell hat zu wenige geliefert: Varianten des ersten Prompts
            prompts.append(f"{prompts[0]}, different composition, variation {len(prompts) + 1}")
        data["image_prompts"] = prompts[:count]
        data["style_description"] = style_text
        return data
