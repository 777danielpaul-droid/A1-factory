import re
from services.llm_gateway import LLMGateway
from services.graphics import FONT_STYLES, _HEX

HEXC = _HEX
THUMB_SYSTEM = ('Du bist Thumbnail-Designer für YouTube und Social Media (hohe Klickrate). Analysiere den Vibe des Themas und entwirf: '
                'eine Hintergrundszene ohne Personen und ohne Text mit kräftigen, gesättigten Farben und hohem Kontrast; pro Variante einen knackigen Schriftzug '
                '(maximal 4 Wörter, GROSSBUCHSTABEN, neugierig machend oder emotional, Sprache: __LANG__), ein Schlüsselwort daraus zum Hervorheben, '
                'optional eine kurze Unterzeile (maximal 3 Wörter) und ein ausdrucksstarkes Charakter-Element (übertriebene Mimik, Nahaufnahme Oberkörper). '
                'Alle Bild-Prompts auf Englisch. Antworte NUR mit JSON: {"vibe": str, "palette": {"accent": "#RRGGBB" (leuchtende Akzentfarbe passend zum Hintergrund), '
                '"text": "#RRGGBB"}, "font_style": "impact"|"clean"|"tech"|"comic" (impact = Standard mit maximaler Wirkung, tech = Gaming/Technik, '
                'comic = lustig/Kids, clean = seriös/Business), "text_position": "left"|"right", "background_prompt": str, '
                '"variants": [genau __N__ Objekte {"headline": str, "highlight": str, "subline": str, "character_prompt": str}]}')
KIT_SYSTEM = ('Du bist Brand- und Stream-Designer. Entwirf für das Thema einen einheitlichen Look für Streamer-Paket und Banner. Texte in der Sprache: __LANG__. '
              'Antworte NUR mit JSON: {"channel_name": str (max 24 Zeichen, GROSSBUCHSTABEN), "tagline": str (max 50 Zeichen), '
              '"palette": {"primary": "#RRGGBB", "secondary": "#RRGGBB", "accent": "#RRGGBB" (leuchtend), "dark": "#RRGGBB" (sehr dunkel), "light": "#RRGGBB" (fast weiß)}, '
              '"font_style": "impact"|"clean"|"tech"|"comic", "frame_style": "neon"|"angular"|"rounded", "bg": "black"|"white" (Hintergrund für das Emblem-Bild: helles Emblem black, dunkles white), '
              '"emblem_prompt": str (englisch, ein einzelnes Symbol oder Maskottchen als Logo, flach, kräftig, ohne Text), '
              '"background_prompt": str (englisch, abstrakte dunkle Hintergrundtextur im Stil des Themas, ohne Personen, ohne Text, ohne Logos), '
              '"panel_titles": [genau 5 kurze Strings, z. B. ABOUT, SCHEDULE, RULES, SOCIALS, DONATE in der Sprache], '
              '"scene_texts": {"starting": str, "brb": str, "offline": str}, "alert_texts": {"follow": str, "sub": str, "donation": str}} (kurze, großgeschriebene Texte)')
DEF_PANELS = {"Deutsch": ["ÜBER MICH", "PLAN", "REGELN", "SOCIALS", "SPENDEN"], "Englisch": ["ABOUT ME", "SCHEDULE", "RULES", "SOCIALS", "DONATE"]}
DEF_SCENES = {"Deutsch": {"starting": "GLEICH GEHT'S LOS", "brb": "BIN GLEICH ZURÜCK", "offline": "STREAM BEENDET"},
              "Englisch": {"starting": "STARTING SOON", "brb": "BE RIGHT BACK", "offline": "STREAM OFFLINE"}}
DEF_ALERTS = {"Deutsch": {"follow": "NEUER FOLLOWER", "sub": "NEUES ABO", "donation": "NEUE SPENDE"},
              "Englisch": {"follow": "NEW FOLLOWER", "sub": "NEW SUBSCRIBER", "donation": "NEW DONATION"}}


def _user(topic, hint):
    return f"Thema: {topic}" + (f"\nWunsch oder Vibe des Nutzers: {hint}" if hint else "")


def _hex(v, default):
    return v if isinstance(v, str) and HEXC.match(v) else default


def _style(v, default):
    return v if v in FONT_STYLES else default


class ThumbnailAgent:
    def __init__(self, gw: LLMGateway):
        self.gw = gw

    async def run(self, provider, api_key, topic, variants, language, hint="", model=None, base_url=None, style_text=None) -> dict:
        system = THUMB_SYSTEM.replace("__LANG__", language).replace("__N__", str(variants))
        if style_text:
            system += " Orientiere Farben und Stil eng an diesem Referenzstil des Nutzers: " + style_text
        d = await self.gw.generate_json(provider, api_key, system, _user(topic, hint), model, base_url)
        if not str(d.get("background_prompt", "")).strip():
            raise ValueError("Thumbnail-Antwort unvollständig: Hintergrund-Prompt fehlt")
        out = []
        for v in d.get("variants", []):
            if not isinstance(v, dict) or not str(v.get("headline", "")).strip():
                continue
            words = str(v["headline"]).upper().split()[:5]
            hl = str(v.get("highlight", "")).upper().strip(".,!?:;")
            out.append({"headline": " ".join(words), "highlight": hl if hl in [w.strip(".,!?:;") for w in words] else words[-1].strip(".,!?:;"),
                        "subline": " ".join(str(v.get("subline", "")).upper().split()[:4]),
                        "character_prompt": str(v.get("character_prompt", "surprised person")).strip() or "surprised person"})
        if not out:
            raise ValueError("Thumbnail-Antwort unvollständig: keine Varianten")
        while len(out) < variants:
            out.append({**out[0], "character_prompt": out[0]["character_prompt"] + ", different expression"})
        pal = d.get("palette") or {}
        return {"vibe": str(d.get("vibe", ""))[:200], "accent": _hex(pal.get("accent"), "#FFDD00"), "text": _hex(pal.get("text"), "#FFFFFF"),
                "font_style": _style(d.get("font_style"), "impact"), "text_position": "right" if d.get("text_position") == "right" else "left",
                "variants": out[:variants],
                "bg_full": d["background_prompt"].strip() + ", vibrant saturated colors, high contrast, cinematic lighting, no text, no letters, no people, no logos, wide composition",
                "char_full": [v["character_prompt"] + ", exaggerated expressive facial expression, close-up of head and upper body, bold clean outline, sticker style, "
                              "isolated on a solid pure bright green background, no text" for v in out[:variants]]}


class KitAgent:
    def __init__(self, gw: LLMGateway):
        self.gw = gw

    async def run(self, provider, api_key, topic, language, hint="", model=None, base_url=None, style_text=None) -> dict:
        system = KIT_SYSTEM.replace("__LANG__", language)
        if style_text:
            system += " Orientiere Stil und Farben eng an diesem Referenzstil des Nutzers: " + style_text
        d = await self.gw.generate_json(provider, api_key, system, _user(topic, hint), model, base_url)
        if not str(d.get("emblem_prompt", "")).strip() or not str(d.get("background_prompt", "")).strip():
            raise ValueError("Kit-Antwort unvollständig: Emblem- oder Hintergrund-Prompt fehlt")
        pal = d.get("palette") if isinstance(d.get("palette"), dict) else {}
        panels = [str(x).upper()[:18] for x in d.get("panel_titles", []) if str(x).strip()][:5]
        panels += DEF_PANELS[language][len(panels):]
        sc, al = d.get("scene_texts") or {}, d.get("alert_texts") or {}
        bg = "black" if str(d.get("bg", "")).lower() == "black" else "white"
        return {"channel_name": str(d.get("channel_name") or topic).upper()[:24], "tagline": str(d.get("tagline", ""))[:60],
                "palette": {k: pal.get(k) for k in ("primary", "secondary", "accent", "dark", "light")},
                "font_style": _style(d.get("font_style"), "tech"), "frame_style": d.get("frame_style") if d.get("frame_style") in ("neon", "angular", "rounded") else "neon",
                "panels": panels,
                "scenes": {k: str(sc.get(k) or DEF_SCENES[language][k]).upper()[:28] for k in DEF_SCENES[language]},
                "alerts": {k: str(al.get(k) or DEF_ALERTS[language][k]).upper()[:24] for k in DEF_ALERTS[language]},
                "emblem_full": d["emblem_prompt"].strip() + f", logo, flat vector style, bold shapes, isolated on a solid pure {bg} background, centered, no text",
                "tex_full": d["background_prompt"].strip() + ", abstract dark background texture, seamless feel, no text, no people, no logos"}
