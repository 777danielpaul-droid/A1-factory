from services.llm_gateway import LLMGateway

SYSTEM = ('Du bist Merch-Designer für Print-on-Demand (T-Shirts, Hoodies). Entwirf aus der Nische ein zentrales Motiv in zwei Fassungen. '
          '1) front_prompt: sauberer, minimalistischer Front-Logo-Entwurf (kleines Brustlogo, wenige Farben, klare Formen, hoher Kontrast, mittig). '
          '2) back_prompt: detailreiches Backprint (große Komposition für den Rücken, gleicher Stil und gleiche Farben, viele Details). '
          'Wähle einen passenden Stil, zum Beispiel feine Line-Art oder Cyberpunk mit Neon-Akzenten, je nach Nische. Kein Text im Bild. '
          'Prompts auf Englisch. Antworte NUR mit JSON: {"concept": str, "style": str, "bg": "black" oder "white" '
          '(heller oder Neon-Look: black, dunkler Look: white), "slogan": str (kurz, nur für Texte), "front_prompt": str, '
          '"back_prompt": str, "print_notes": str (Hinweise zu Druckplatzierung und Farben)}')


class MerchAgent:
    def __init__(self, gateway: LLMGateway):
        self.gateway = gateway

    async def run(self, provider, api_key, niche, model=None, base_url=None, style_text=None) -> dict:
        system = SYSTEM
        if style_text:
            system += " Orientiere dich eng an diesem Referenzstil des Nutzers: " + style_text
        d = await self.gateway.generate_json(provider, api_key, system, f"Nische: {niche}", model, base_url)
        for k in ("front_prompt", "back_prompt"):
            if not str(d.get(k, "")).strip():
                raise ValueError(f"Merch-Antwort unvollständig: '{k}' fehlt")
        bg = "black" if str(d.get("bg", "")).lower() == "black" else "white"
        tail = f", isolated on a solid pure {bg} background, flat colors, no shadows, no gradient or texture in the background, centered"
        d["bg"] = bg
        d["front_full"] = d["front_prompt"].strip() + ", minimal clean logo, vector style" + tail
        d["back_full"] = d["back_prompt"].strip() + ", highly detailed large print illustration, vector style" + tail
        return d
