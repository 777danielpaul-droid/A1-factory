from services.image_generator import ImageGeneratorService


class DesignerAgent:
    def __init__(self):
        self.images = ImageGeneratorService()

    async def run(self, scout: dict, image_cfg: dict, progress=None, reference=None) -> dict:
        prompts = scout["image_prompts"]
        style = ", ".join(scout.get("style_keywords", []))
        paths, used = [], []
        for i, base in enumerate(prompts, 1):
            if progress:
                await progress(f"Motiv {i}/{len(prompts)}")
            prompt = f"{base}, {style}, clean isolated clipart, high quality"
            try:
                paths.append(await self.images.generate_asset(image_cfg, prompt, scout.get("negative_prompt", "text, watermark, blurry"), progress, reference))
                used.append(prompt)
            except Exception:
                if not paths:  # schon das erste Bild scheitert: Lauf abbrechen
                    raise
                if progress:
                    await progress(f"Motiv {i} fehlgeschlagen, das Paket wird mit {len(paths)} Bild(ern) fortgesetzt")
                break
        return {"prompts_used": used, "local_paths": paths, "image_urls": [f"/static/assets/{p.name}" for p in paths]}

    async def render(self, prompts: list, negative: str, image_cfg: dict, progress=None, reference=None, label="Bild") -> list:
        """Erzeugt mehrere Bilder nacheinander. Scheitert schon das erste, bricht es ab. Gibt die erfolgreichen Pfade zurück."""
        paths = []
        for i, prompt in enumerate(prompts, 1):
            if progress:
                await progress(f"{label} {i}/{len(prompts)}")
            try:
                paths.append(await self.images.generate_asset(image_cfg, prompt, negative, progress, reference))
            except Exception:
                if not paths:
                    raise
                break
        return paths
