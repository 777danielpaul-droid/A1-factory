"""Ein Gateway für alle LLM-Anbieter (BYOK: der Key kommt bei jedem Aufruf vom Nutzer)."""
import asyncio, json, re
import httpx

# OpenAI-kompatible Anbieter: (URL, Default-Modell)
COMPAT = {
    "openai": ("https://api.openai.com/v1/chat/completions", "gpt-4o"),
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
    "grok": ("https://api.x.ai/v1/chat/completions", "grok-4"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "anthropic/claude-sonnet-4.5"),
    "zai": ("https://api.z.ai/api/paas/v4/chat/completions", "glm-4.6"),
    "huggingface": ("https://router.huggingface.co/v1/chat/completions", "meta-llama/Llama-3.3-70B-Instruct"),
}
ANTHROPIC_DEFAULT = "claude-sonnet-5-5"
PROVIDERS = [*COMPAT, "anthropic", "custom"]  # custom = beliebiger OpenAI-kompatibler Dienst (Base-URL vom Nutzer)


NON_CHAT = re.compile(r"embed|whisper|tts|dall-e|moderation|guard|transcri|audio|rerank|realtime", re.I)


class LLMError(Exception):
    pass


def extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise LLMError(f"Keine JSON-Antwort: {text[:200]}")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise LLMError(f"Ungültiges JSON: {e}") from e


class LLMGateway:
    async def generate_json(self, provider: str, api_key: str, system: str, user: str,
                            model: str | None = None, base_url: str | None = None, retries: int = 2) -> dict:
        provider = provider.lower()
        if provider not in PROVIDERS:
            raise LLMError(f"Unbekannter Provider: {provider}")
        last = None
        for attempt in range(retries + 1):
            try:
                return extract_json(await self._complete(provider, api_key, system, user, model, base_url))
            except LLMError as e:
                last = e
                if "HTTP 401" in str(e) or "HTTP 403" in str(e):
                    raise LLMError(f"{provider}: Key wurde abgelehnt. Prüfe den eingegebenen Key.") from e
            except httpx.HTTPError as e:
                last = e
            await asyncio.sleep(1.5 * (attempt + 1))
        raise LLMError(f"{provider} fehlgeschlagen: {last}")

    async def _complete(self, provider, api_key, system, user, model, base_url=None, image=None, json_mode=True) -> str:
        async with httpx.AsyncClient(timeout=60) as c:
            if provider == "anthropic":
                r = await c.post("https://api.anthropic.com/v1/messages",
                                 headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                                 json={"model": model or ANTHROPIC_DEFAULT, "max_tokens": 2000, "system": system,
                                       "messages": [{"role": "user", "content": self._content(provider, user, image)}]})
                self._check(r)
                return "".join(b.get("text", "") for b in r.json()["content"])
            if provider == "custom":
                if not (base_url and base_url.startswith(("http://", "https://"))) or not model:
                    raise LLMError("Eigener Anbieter: Base-URL (http/https) und Modellname sind nötig.")
                url, default = base_url.rstrip("/"), model
                if not url.endswith("/chat/completions"):
                    url += "/chat/completions"
            else:
                url, default = COMPAT[provider]
            body = {"model": model or default, "max_tokens": 2000,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": self._content(provider, user, image)}]}
            if provider == "openai" and json_mode:
                body["response_format"] = {"type": "json_object"}
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            r = await c.post(url, headers=headers, json=body)
            self._check(r)
            return r.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _content(provider: str, text: str, image: dict | None):
        """image = {"b64": ..., "mime": ...}. Ohne Bild bleibt es ein normaler Text."""
        if not image:
            return text
        if provider == "anthropic":
            return [{"type": "image", "source": {"type": "base64", "media_type": image["mime"], "data": image["b64"]}},
                    {"type": "text", "text": text}]
        return [{"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": f"data:{image['mime']};base64,{image['b64']}"}}]

    async def generate_text(self, provider: str, api_key: str, system: str, user: str, model=None, base_url=None, image=None) -> str:
        """Freitext-Antwort, optional mit Bild. Gibt eine verständliche Meldung, wenn das Modell keine Bilder lesen kann."""
        last = None
        for attempt in range(2):
            try:
                return (await self._complete(provider, api_key, system, user, model, base_url, image, json_mode=False)).strip()
            except LLMError as e:
                last = e
                msg = str(e)
                if "HTTP 401" in msg or "HTTP 403" in msg:
                    raise LLMError(f"{provider}: Key wurde abgelehnt. Prüfe den eingegebenen Key.") from e
                if image and ("HTTP 400" in msg or "HTTP 404" in msg or "HTTP 422" in msg):
                    raise LLMError(f"{provider}: Das Modell kann vermutlich keine Bilder lesen. Wähl ein Modell mit Bildverständnis (Vision). Antwort: {msg[:160]}") from e
            except httpx.HTTPError as e:
                last = e
            await asyncio.sleep(1.5)
        raise LLMError(f"{provider} fehlgeschlagen: {last}")

    async def list_models(self, provider: str, api_key: str, base_url: str | None = None) -> list:
        """Holt die Modellliste direkt beim Anbieter. `free` ist nur bei OpenRouter zuverlässig bekannt."""
        if provider not in PROVIDERS:
            raise LLMError(f"Unbekannter Provider: {provider}")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        async with httpx.AsyncClient(timeout=30) as c:
            if provider == "anthropic":
                if not api_key:
                    raise LLMError("Trag zuerst deinen Key ein.")
                r = await c.get("https://api.anthropic.com/v1/models", params={"limit": 100},
                                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"})
            else:
                if provider == "custom":
                    if not (base_url and base_url.startswith(("http://", "https://"))):
                        raise LLMError("Trag zuerst die Base-URL ein.")
                    base = base_url.rstrip("/")
                else:
                    base = COMPAT[provider][0]
                url = base.removesuffix("/chat/completions") + "/models"
                if provider not in ("openrouter", "custom") and not api_key:
                    raise LLMError("Trag zuerst deinen Key ein.")
                r = await c.get(url, headers=headers)
        self._check(r)
        j = r.json()
        items = j if isinstance(j, list) else j.get("data", [])
        out = []
        for m in items:
            mid = m.get("id") or m.get("name")
            if not mid or NON_CHAT.search(mid):
                continue
            pr = m.get("pricing") or {}
            free = provider == "openrouter" and (mid.endswith(":free") or (str(pr.get("prompt")) == "0" and str(pr.get("completion")) == "0"))
            out.append({"id": mid, "name": m.get("name") or m.get("display_name") or "", "free": bool(free)})
        return sorted(out, key=lambda x: x["id"].lower())

    @staticmethod
    def _check(r):
        if r.status_code >= 400:
            raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
