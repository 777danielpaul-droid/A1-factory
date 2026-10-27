import re
from services.llm_gateway import LLMGateway

SYSTEM = ('Du bist Brand-Designer. Entwirf für die Nische ein Micro-Branding. Nutze die Hex-Farben deiner Palette in den Bild-Prompts als Farbangaben. '
          'Antworte NUR mit JSON: {"brand_name": str, "tagline": str, '
          '"palette": [genau 5 Objekte {"name": str, "hex": "#RRGGBB", "role": "Primary"|"Secondary"|"Accent"|"Background"|"Text"}], '
          '"fonts": [genau 3 Objekte {"role": "Headline"|"Body"|"Accent", "name": str (eine real existierende Google-Fonts-Schrift), "why": str}], '
          '"logo_prompts": [genau __N__ Strings, englisch, unterschiedliche Logo-Varianten wie Symbol allein, Emblem/Badge, Monogramm; flach, vektorartig, ohne Text im Bild], '
          '"pattern_prompt": str (englisch, nahtlos wiederholbares Muster in den Markenfarben), "voice": str (Tonalität in einem Satz), '
          '"bg": "black" oder "white" (Hintergrundfarbe für die Logo-Bilder: heller Look black, dunkler Look white)}')
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class BrandAgent:
    def __init__(self, gateway: LLMGateway):
        self.gateway = gateway

    async def run(self, provider, api_key, niche, variants=2, model=None, base_url=None, style_text=None) -> dict:
        system = SYSTEM.replace("__N__", str(variants))
        if style_text:
            system += " Orientiere Stil und Farben eng an diesem Referenzstil des Nutzers: " + style_text
        d = await self.gateway.generate_json(provider, api_key, system, f"Nische: {niche}", model, base_url)
        pal = [{"name": str(c.get("name", ""))[:30], "hex": str(c["hex"]).upper(), "role": str(c.get("role", ""))[:20]}
               for c in d.get("palette", []) if isinstance(c, dict) and HEX.match(str(c.get("hex", "")))]
        if len(pal) < 3:
            raise ValueError("Die Farbpalette war unbrauchbar (zu wenige gültige Hex-Codes). Probier es nochmal oder nimm ein anderes Modell.")
        fonts = [{"role": str(f.get("role", ""))[:20], "name": str(f["name"])[:40], "why": str(f.get("why", ""))[:200],
                  "url": "https://fonts.google.com/?query=" + str(f["name"]).replace(" ", "+")}
                 for f in d.get("fonts", []) if isinstance(f, dict) and f.get("name")]
        logos = [p.strip() for p in d.get("logo_prompts", []) if isinstance(p, str) and p.strip()]
        if not logos or not str(d.get("pattern_prompt", "")).strip():
            raise ValueError("Brand-Antwort unvollständig: Logo- oder Muster-Prompt fehlt")
        while len(logos) < variants:
            logos.append(f"{logos[0]}, alternative composition {len(logos) + 1}")
        bg = "black" if str(d.get("bg", "")).lower() == "black" else "white"
        tail = f", isolated on a solid pure {bg} background, flat colors, no shadows, centered"
        return {"brand_name": str(d.get("brand_name", niche))[:60], "tagline": str(d.get("tagline", ""))[:120], "palette": pal[:5],
                "fonts": fonts[:3], "voice": str(d.get("voice", ""))[:200], "bg": bg,
                "logo_full": [p + ", logo design, vector style" + tail for p in logos[:variants]],
                "pattern_full": d["pattern_prompt"].strip() + ", seamless repeating pattern, flat design"}
