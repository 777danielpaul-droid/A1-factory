"""Viele Bildanbieter hinter einer Funktion. Jeder Anbieter liefert Bytes, am Ende wird alles zu PNG."""
import asyncio, base64, hashlib, io, re, urllib.parse, uuid
from pathlib import Path
import httpx
from PIL import Image, ImageDraw, ImageFont

ASSET_DIR = Path(__file__).resolve().parent.parent / "output" / "assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)

# Pflichtfelder pro Anbieter (die Oberfläche zeigt dieselben Felder)
REQUIRED = {"placeholder": [], "pollinations": [], "huggingface": ["key"], "cloudflare": ["account_id", "key"],
            "gemini": ["key"], "together": ["key"], "openai": ["key"], "stability": ["key"], "local": ["base_url"]}
IMAGE_PROVIDERS = list(REQUIRED)
IMG2IMG = ["gemini", "openai", "local"]  # Anbieter, die ein Referenzbild direkt verarbeiten
OPENAI_EDIT_URL = "https://api.openai.com/v1/images/edits"

POLLINATIONS_URL = "https://image.pollinations.ai/prompt"
HF_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"
CF_URL = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/@cf/black-forest-labs/flux-1-schnell"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TOGETHER_URL = "https://api.together.xyz/v1/images/generations"
OPENAI_URL = "https://api.openai.com/v1/images/generations"
STABILITY_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"


def _fail(name: str, r: httpx.Response):
    if r.status_code in (401, 403):
        raise RuntimeError(f"{name}: Zugang wurde abgelehnt. Prüfe Key und Berechtigungen.")
    if r.status_code in (402, 429):
        raise RuntimeError(f"{name}: Limit oder Guthaben erreicht (HTTP {r.status_code}). {r.text[:200]}")
    raise RuntimeError(f"{name} HTTP {r.status_code}: {r.text[:300]}")


class ImageGeneratorService:
    async def generate_asset(self, cfg: dict, prompt: str, negative_prompt: str = "", on_wait=None, reference=None) -> Path:
        provider = cfg.get("provider", "pollinations")
        fn = {"placeholder": self._placeholder, "pollinations": self._pollinations, "huggingface": self._huggingface,
              "cloudflare": self._cloudflare, "gemini": self._gemini, "together": self._together,
              "openai": self._openai, "stability": self._stability, "local": self._local}.get(provider)
        if not fn:
            raise RuntimeError(f"Unbekannter Bildanbieter: {provider}")
        data = await fn(cfg, prompt, negative_prompt, on_wait, reference)
        try:  # alles zu PNG vereinheitlichen (Anbieter liefern JPEG, WebP oder PNG)
            img = Image.open(io.BytesIO(data))
            img.load()
            buf = io.BytesIO()
            img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB").save(buf, format="PNG")
            data = buf.getvalue()
        except Exception as e:
            raise RuntimeError(f"{provider}: Antwort war kein lesbares Bild ({e})") from e
        path = ASSET_DIR / f"asset_{uuid.uuid4().hex[:12]}.png"
        path.write_bytes(data)
        return path

    # --- Testmodus ---------------------------------------------------------------------------
    async def _placeholder(self, cfg, prompt, neg, on_wait, ref=None) -> bytes:
        h = hashlib.sha256(prompt.encode()).digest()
        c1, c2 = tuple(40 + h[i] % 120 for i in range(3)), tuple(100 + h[i + 3] % 150 for i in range(3))
        img = Image.new("RGB", (1024, 1024))
        d = ImageDraw.Draw(img)
        for y in range(1024):
            t = y / 1023
            d.line([(0, y), (1024, y)], fill=tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3)))
        for x in range(0, 1024, 64):
            d.line([(x, 0), (x, 1024)], fill=(255, 255, 255), width=1)
        try:
            big, small = ImageFont.load_default(size=64), ImageFont.load_default(size=28)
        except TypeError:
            big = small = ImageFont.load_default()
        d.text((60, 70), "TESTBILD", fill=(255, 255, 255), font=big)
        words, line, y = prompt.split(), "", 190
        for w in words:
            if len(line) + len(w) > 38:
                d.text((60, y), line, fill=(255, 255, 255), font=small); y += 40; line = ""
                if y > 900: break
            line += w + " "
        if line and y <= 900:
            d.text((60, y), line, fill=(255, 255, 255), font=small)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return buf.getvalue()

    # --- Kostenlos / ohne Key ------------------------------------------------------------------
    async def _pollinations(self, cfg, prompt, neg, on_wait, ref=None) -> bytes:
        api_key = cfg.get("key", "")
        url = f"{POLLINATIONS_URL}/{urllib.parse.quote(prompt[:900])}"
        params = {"width": 1024, "height": 1024, "model": "flux", "nologo": "true", "seed": uuid.uuid4().int % 10**6}
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        last = ""
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as c:
            for attempt in range(5):
                r = await c.get(url, params=params, headers=headers)
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
                    return r.content
                last = f"HTTP {r.status_code}: {r.text[:160]}"
                limited = r.status_code == 402 and "FREE_LIMIT" in r.text  # z. B. "1 image every 45 seconds"
                if r.status_code not in (429, 502, 503, 504) and not limited:
                    break
                m = re.search(r"[Rr]etry after (\d+)\s*s", r.text) or re.search(r"every (\d+) second", r.text)
                wait = min(int(m.group(1)) + 3 if m else 16, 60)
                if on_wait:
                    await on_wait(f"Pollinations ist gedrosselt, neuer Versuch in {wait} s ({attempt + 1}/5)")
                await asyncio.sleep(wait)
        raise RuntimeError("Pollinations ist gerade überlastet oder gedrosselt. Warte kurz, trag einen Pollinations-Key ein "
                           f"oder nimm einen anderen Bildanbieter. Letzte Antwort: {last}")

    async def _cloudflare(self, cfg, prompt, neg, on_wait, ref=None) -> bytes:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(CF_URL.format(account=cfg["account_id"]), headers={"Authorization": f"Bearer {cfg['key']}"},
                             json={"prompt": prompt[:2000], "steps": 4})
        if r.status_code != 200:
            _fail("Cloudflare", r)
        b64 = (r.json().get("result") or {}).get("image")
        if not b64:
            raise RuntimeError(f"Cloudflare: kein Bild in der Antwort: {r.text[:200]}")
        return base64.b64decode(b64)

    async def _huggingface(self, cfg, prompt, neg, on_wait, ref=None) -> bytes:
        from huggingface_hub import AsyncInferenceClient  # wählt selbst einen Anbieter (provider="auto")
        try:
            img = await AsyncInferenceClient(api_key=cfg["key"], timeout=120).text_to_image(prompt, model=cfg.get("model") or HF_IMAGE_MODEL)
        except Exception as e:
            msg = str(e)
            if "401" in msg or "403" in msg:
                raise RuntimeError("Hugging Face: Key abgelehnt. Der Token braucht die Berechtigung für Inference Providers.") from e
            if "402" in msg:
                raise RuntimeError("Hugging Face: Gratis-Guthaben aufgebraucht oder keins vorhanden (huggingface.co/settings/billing).") from e
            raise RuntimeError(f"Hugging Face: {msg[:300]}") from e
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return buf.getvalue()

    # --- Mit Gratis-Kontingent oder kostenpflichtig --------------------------------------------
    async def _gemini(self, cfg, prompt, neg, on_wait, ref=None) -> bytes:
        model = cfg.get("model") or "gemini-2.5-flash-image"
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(GEMINI_URL.format(model=model), headers={"x-goog-api-key": cfg["key"]},
                             json={"contents": [{"parts": [{"text": ("Use the attached image as the style and composition reference. " + prompt) if ref else prompt}] + ([{"inlineData": {"mimeType": ref["mime"], "data": ref["b64"]}}] if ref else [])}], "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}})
        if r.status_code != 200:
            _fail("Gemini", r)
        for cand in r.json().get("candidates", []):
            for part in (cand.get("content") or {}).get("parts", []):
                blob = part.get("inlineData") or part.get("inline_data")
                if blob and blob.get("data"):
                    return base64.b64decode(blob["data"])
        raise RuntimeError(f"Gemini: kein Bild in der Antwort (Inhaltsfilter?): {r.text[:200]}")

    async def _together(self, cfg, prompt, neg, on_wait, ref=None) -> bytes:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(TOGETHER_URL, headers={"Authorization": f"Bearer {cfg['key']}"},
                             json={"model": cfg.get("model") or "black-forest-labs/FLUX.1-schnell", "prompt": prompt, "steps": 4,
                                   "n": 1, "width": 1024, "height": 1024, "response_format": "b64_json"})
        if r.status_code != 200:
            _fail("Together", r)
        return base64.b64decode(r.json()["data"][0]["b64_json"])

    async def _openai(self, cfg, prompt, neg, on_wait, ref=None) -> bytes:
        model = cfg.get("model") or "gpt-image-1"
        body = {"model": model, "prompt": prompt[:3900], "size": "1024x1024", "n": 1}
        if model.startswith("dall-e"):
            body["response_format"] = "b64_json"
        async with httpx.AsyncClient(timeout=180) as c:
            if ref:  # Bild-zu-Bild über den Edit-Endpunkt
                ext = {"image/png": "png", "image/webp": "webp"}.get(ref["mime"], "jpg")
                r = await c.post(OPENAI_EDIT_URL, headers={"Authorization": f"Bearer {cfg['key']}"},
                                 data={"model": model, "prompt": prompt[:3900], "size": "1024x1024"},
                                 files={"image": (f"reference.{ext}", base64.b64decode(ref["b64"]), ref["mime"])})
            else:
                r = await c.post(OPENAI_URL, headers={"Authorization": f"Bearer {cfg['key']}"}, json=body)
        if r.status_code != 200:
            _fail("OpenAI Bilder", r)
        return base64.b64decode(r.json()["data"][0]["b64_json"])

    async def _stability(self, cfg, prompt, neg, on_wait, ref=None) -> bytes:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(STABILITY_URL, headers={"authorization": f"Bearer {cfg['key']}", "accept": "image/*"}, files={"none": ""},
                             data={"prompt": prompt, "negative_prompt": neg, "output_format": "png", "aspect_ratio": "1:1"})
        if r.status_code != 200:
            _fail("Stability", r)
        return r.content

    # --- Lokal -------------------------------------------------------------------------------------
    async def _local(self, cfg, prompt, neg, on_wait, ref=None) -> bytes:
        base = cfg["base_url"].rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=600) as c:
                if ref:
                    r = await c.post(f"{base}/sdapi/v1/img2img", json={"init_images": [ref["b64"]], "denoising_strength": 0.6, "prompt": prompt,
                                                                      "negative_prompt": neg, "width": 768, "height": 768, "steps": 20})
                else:
                    r = await c.post(f"{base}/sdapi/v1/txt2img", json={"prompt": prompt, "negative_prompt": neg, "width": 768, "height": 768, "steps": 20})
        except httpx.ConnectError as e:
            raise RuntimeError(f"Lokale Stable Diffusion WebUI unter {base} nicht erreichbar. Läuft sie mit der Option --api?") from e
        if r.status_code != 200:
            _fail("Lokale WebUI", r)
        return base64.b64decode(r.json()["images"][0])
