"""BYOK helpers for speech and video generation (keys are request-scoped)."""
import asyncio
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx

BASE = Path(__file__).resolve().parents[1]
ASSETS = BASE / "output" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)


def _safe_error(response: httpx.Response, label: str) -> RuntimeError:
    try:
        body = response.json()
        detail = body.get("detail") or body.get("message") or body.get("error") or body
        if isinstance(detail, dict):
            detail = detail.get("message") or str(detail)
        detail = str(detail)[:350]
    except Exception:
        detail = response.text[:250]
    if response.status_code in (401, 403):
        detail = "API-Key ungültig oder nicht berechtigt. Prüfe deinen Zugang beim Anbieter."
    elif response.status_code == 402:
        detail = "Beim Anbieter ist kein ausreichendes Guthaben bzw. kein aktiver Tarif vorhanden."
    elif response.status_code == 429:
        detail = "Limit erreicht. Warte etwas oder prüfe dein Kontingent beim Anbieter."
    return RuntimeError(f"{label}: {detail}")


async def generate_speech(*, api_key: str, text: str, voice_id: str, model_id: str) -> dict:
    if not api_key.strip():
        raise ValueError("Bitte einen ElevenLabs-API-Key eintragen.")
    if not text.strip():
        raise ValueError("Bitte Text für die Sprachausgabe eingeben.")
    if len(text) > 5000:
        raise ValueError("Der Text darf höchstens 5.000 Zeichen lang sein.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}", voice_id.strip()):
        raise ValueError("Die Voice-ID sieht ungültig aus. Bitte eine Voice-ID aus ElevenLabs verwenden.")
    payload = {"text": text.strip(), "model_id": model_id.strip() or "eleven_multilingual_v2"}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id.strip()}?output_format=mp3_44100_128",
            headers={"xi-api-key": api_key.strip(), "Content-Type": "application/json", "Accept": "audio/mpeg"},
            json=payload,
        )
    if response.status_code >= 400:
        raise _safe_error(response, "ElevenLabs")
    if not response.content or len(response.content) > 40_000_000:
        raise RuntimeError("ElevenLabs lieferte keine gültige Audiodatei oder die Datei ist zu groß.")
    name = f"speech-{uuid.uuid4().hex}.mp3"
    (ASSETS / name).write_bytes(response.content)
    return {"url": f"/static/assets/{name}", "filename": name, "bytes": len(response.content), "provider": "ElevenLabs"}


async def generate_video(*, api_key: str, prompt: str, model_slug: str, duration_seconds: int = 5, reference_image_data_url: str = "") -> dict:
    if not api_key.strip():
        raise ValueError("Bitte einen Replicate-API-Token eintragen.")
    if not prompt.strip():
        raise ValueError("Bitte eine Beschreibung für das Video eingeben.")
    if len(prompt) > 2000:
        raise ValueError("Die Videobeschreibung darf höchstens 2.000 Zeichen lang sein.")
    slug = model_slug.strip().strip("/")
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,80}/[A-Za-z0-9_-]{2,100}", slug):
        raise ValueError("Modell muss im Format Anbieter/Modell angegeben werden, z. B. minimax/video-01.")
    duration_seconds = max(3, min(10, int(duration_seconds)))
    owner, model = slug.split("/", 1)
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json", "Prefer": "wait=60"}
    model_input = {"prompt": prompt.strip(), "duration": duration_seconds}
    if reference_image_data_url:
        match = re.fullmatch(r"data:image/(?:jpeg|png|webp);base64,([A-Za-z0-9+/=]+)", reference_image_data_url)
        if not match or len(reference_image_data_url) > 500_000:
            raise ValueError("Das Referenzbild für die Videogenerierung ist ungültig oder zu groß.")
        # minimax/video-01 accepts a first-frame image. Other model schemas vary, so don't send unsupported fields.
        if slug.lower() == "minimax/video-01":
            model_input["first_frame_image"] = reference_image_data_url
    async with httpx.AsyncClient(timeout=90, follow_redirects=False) as client:
        response = await client.post(
            f"https://api.replicate.com/v1/models/{owner}/{model}/predictions",
            headers=headers,
            json={"input": model_input},
        )
        if response.status_code >= 400:
            raise _safe_error(response, "Replicate")
        prediction = response.json()
        # Some models take longer than the synchronous wait. Poll only Replicate's own API URL.
        get_url = prediction.get("urls", {}).get("get")
        for _ in range(24):
            if prediction.get("status") in ("succeeded", "failed", "canceled"):
                break
            if not get_url or urlparse(get_url).hostname != "api.replicate.com" or urlparse(get_url).scheme != "https":
                raise RuntimeError("Replicate lieferte keine gültige Status-URL zurück.")
            await asyncio.sleep(5)
            poll = await client.get(get_url, headers={"Authorization": f"Bearer {api_key.strip()}"})
            if poll.status_code >= 400:
                raise _safe_error(poll, "Replicate-Status")
            prediction = poll.json()
    if prediction.get("status") != "succeeded":
        detail = str(prediction.get("error") or f"Status: {prediction.get('status', 'unbekannt')}")[:300]
        raise RuntimeError(f"Videogenerierung nicht abgeschlossen: {detail}")
    output = prediction.get("output")
    if isinstance(output, list):
        output = next((x for x in output if isinstance(x, str) and x.startswith("https://")), None)
    if not isinstance(output, str) or not output.startswith("https://"):
        raise RuntimeError("Das Modell lieferte keine herunterladbare Video-URL. Prüfe die Modell-Ausgabe bei Replicate.")
    parsed = urlparse(output)
    if not parsed.hostname or parsed.hostname in ("localhost", "127.0.0.1", "::1"):
        raise RuntimeError("Die zurückgelieferte Video-URL ist ungültig.")
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        media = await client.get(output)
    if media.status_code >= 400:
        raise RuntimeError("Das generierte Video konnte nicht heruntergeladen werden.")
    if not media.content or len(media.content) > 250_000_000:
        raise RuntimeError("Das Video ist leer oder größer als 250 MB.")
    name = f"video-{uuid.uuid4().hex}.mp4"
    (ASSETS / name).write_bytes(media.content)
    return {"url": f"/static/assets/{name}", "filename": name, "bytes": len(media.content), "provider": "Replicate", "model": slug}
