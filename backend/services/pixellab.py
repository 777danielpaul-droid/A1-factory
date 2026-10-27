"""PixelLab v2 client used only by the Game Assets workspace."""
import asyncio
import base64
import binascii
import io
import re
import uuid
from pathlib import Path

import httpx
from PIL import Image

BASE_URL = "https://api.pixellab.ai/v2"
ASSET_DIR = Path(__file__).resolve().parent.parent / "output" / "assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)


class PixelLabError(RuntimeError):
    pass


def _decode_image_payload(payload: dict) -> bytes | None:
    """Decode the common PixelLab image response shapes."""
    if not isinstance(payload, dict):
        return None
    candidates = [payload.get("image"), payload.get("result"), payload]
    images = payload.get("images")
    if isinstance(images, list):
        candidates.extend(images)
    last = payload.get("last_response")
    if isinstance(last, dict):
        candidates.extend([last.get("image"), last.get("result")])
        if isinstance(last.get("images"), list):
            candidates.extend(last["images"])
    for item in candidates:
        if not isinstance(item, dict):
            continue
        b64 = item.get("base64") or item.get("b64_json")
        if isinstance(b64, str) and b64:
            b64 = re.sub(r"^data:image/[^;]+;base64,", "", b64)
            try:
                return base64.b64decode(b64, validate=False)
            except (binascii.Error, ValueError):
                continue
    return None


class PixelLabClient:
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None):
        if not api_key or not api_key.strip():
            raise PixelLabError("Bitte zuerst einen PixelLab API-Key eintragen.")
        self.api_key = api_key.strip()
        self._client = client

    async def generate(self, prompt: str, width: int = 128, height: int = 128,
                       transparent: bool = True, seed: int | None = None,
                       on_status=None, reference: dict | None = None) -> Path:
        if not prompt.strip():
            raise PixelLabError("Bitte eine Beschreibung für das Pixel-Art-Asset eingeben.")
        if not (16 <= width <= 768 and 16 <= height <= 768):
            raise PixelLabError("Breite und Höhe müssen zwischen 16 und 768 Pixeln liegen.")
        body = {"description": prompt.strip()[:2000], "image_size": {"width": width, "height": height},
                "no_background": bool(transparent)}
        if seed is not None:
            body["seed"] = max(0, int(seed))
        # PixelLab's text-to-pixel endpoint has no reference input. When a base
        # image is supplied, use the documented image-to-pixel-art endpoint.
        endpoint = "create-image-pixen"
        if reference:
            endpoint = "image-to-pixelart"
            body["image"] = {"base64": f"data:{reference['mime']};base64,{reference['b64']}", "type": reference["mime"]}
        own_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=90)
        try:
            response = await client.post(f"{BASE_URL}/{endpoint}",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, json=body)
            if response.status_code not in (200, 201, 202):
                self._raise_api_error(response.status_code, response.text)
            data = response.json()
            image_bytes = _decode_image_payload(data)
            job_id = data.get("background_job_id") or data.get("job_id")
            if image_bytes is None and job_id:
                image_bytes = await self._poll(client, str(job_id), on_status)
            if image_bytes is None:
                raise PixelLabError("PixelLab hat weder ein direktes Bild noch eine Job-ID zurückgegeben. Antwortformat prüfen.")
            try:
                with Image.open(io.BytesIO(image_bytes)) as image:
                    image.load()
                    buffer = io.BytesIO()
                    image.save(buffer, format="PNG")
                    image_bytes = buffer.getvalue()
            except Exception as exc:
                raise PixelLabError("PixelLab-Antwort war keine lesbare Bilddatei.") from exc
            path = ASSET_DIR / f"pixellab_{uuid.uuid4().hex[:12]}.png"
            path.write_bytes(image_bytes)
            return path
        finally:
            if own_client:
                await client.aclose()

    async def _poll(self, client: httpx.AsyncClient, job_id: str, on_status=None) -> bytes:
        # Typical generation jobs finish within seconds to a few minutes.
        for attempt in range(90):
            await asyncio.sleep(2 if attempt < 10 else 4)
            response = await client.get(f"{BASE_URL}/background-jobs/{job_id}",
                headers={"Authorization": f"Bearer {self.api_key}"})
            if response.status_code != 200:
                self._raise_api_error(response.status_code, response.text)
            data = response.json()
            status = str(data.get("status", "")).lower()
            if on_status:
                await on_status(status or "processing")
            if status == "completed":
                image_bytes = _decode_image_payload(data)
                if image_bytes is not None:
                    return image_bytes
                raise PixelLabError("PixelLab meldet 'completed', hat aber kein Bild geliefert.")
            if status in {"failed", "error", "cancelled", "canceled"}:
                detail = (data.get("last_response") or {}).get("detail") if isinstance(data.get("last_response"), dict) else None
                raise PixelLabError(f"PixelLab-Generierung fehlgeschlagen: {detail or data.get('error') or status}")
        raise PixelLabError("PixelLab-Generierung dauert zu lange. Bitte später erneut versuchen.")

    @staticmethod
    def _raise_api_error(status: int, body: str):
        if status in (401, 403):
            raise PixelLabError("PixelLab hat den API-Key abgelehnt. Prüfe Token und Berechtigungen.")
        if status == 402:
            raise PixelLabError("PixelLab meldet zu wenig Guthaben/Credits. Prüfe dein Konto, bevor du erneut generierst.")
        if status == 429:
            raise PixelLabError("PixelLab-Limit erreicht. Bitte warte und versuche es später erneut.")
        raise PixelLabError(f"PixelLab API-Fehler HTTP {status}: {body[:240]}")
