import asyncio, json, os, re, uuid
from pathlib import Path
from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()  # optional; es werden keine API-Keys aus Dateien gelesen
from pipeline import AgentFactoryPipeline  # noqa: E402
from studio_pipeline import StudioPipeline  # noqa: E402
from content_pipeline import ContentPipeline  # noqa: E402
from services.content_render import BANNERS, FORMATS  # noqa: E402
from services.llm_gateway import PROVIDERS, LLMError, LLMGateway  # noqa: E402
from services.shopify_api import SHOP_RE  # noqa: E402
from services.image_generator import IMAGE_PROVIDERS, IMG2IMG, REQUIRED  # noqa: E402
from product_store import init_db, save_product, list_products, get_product, update_product, delete_product  # noqa: E402
from story_store import init_story_db, list_characters, get_character, save_character, delete_character, list_stories, get_story, save_story, delete_story  # noqa: E402
from game_asset_store import init_game_asset_db, save_game_asset, list_game_assets, delete_game_asset  # noqa: E402
from services.pixellab import PixelLabClient, PixelLabError  # noqa: E402

from services.media_generation import generate_speech, generate_video  # noqa: E402

BASE = Path(__file__).resolve().parent
(BASE / "output" / "assets").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Agent Factory (BYOK)")
app.add_middleware(CORSMiddleware, allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
                   allow_methods=["*"], allow_headers=["*"])
app.mount("/static/assets", StaticFiles(directory=BASE / "output" / "assets"), name="assets")
init_db()
init_story_db()
init_game_asset_db()

REF_RE = re.compile(r"^data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=\s]+)$")
MODULES = ["merch", "brand", "mockups"]
CONTENT_MODULES = ["thumbnails", "streamer", "banners"]
SHOPIFY_FIELDS = ["shop", "access_token", "client_id", "client_secret", "api_version"]
ETSY_FIELDS = ["api_key", "shop_id", "taxonomy_id", "access_token", "refresh_token"]


def parse_reference_data_url(data_url: str):
    """Validate and normalize a small user-supplied image reference."""
    if not data_url:
        return None
    match = REF_RE.match(data_url)
    if not match or len(data_url) > 8_000_000:
        raise HTTPException(422, "Referenzbild ungültig oder zu groß. Bitte PNG, JPEG oder WebP bis ca. 6 MB verwenden.")
    return {"mime": match.group(1), "b64": re.sub(r"\s", "", match.group(2))}


class Session:
    """Eine Browser-Verbindung. Ergebnisse und Tokens gehen nur an diese Verbindung."""
    def __init__(self, ws: WebSocket):
        self.ws, self.running = ws, False

    async def send(self, type_: str, data: dict):
        try:
            if type_ == "PRODUCT_CREATED":
                try:
                    data = save_product(data)
                except Exception as exc:
                    await self.ws.send_text(json.dumps({"type": "RUN_FAILED", "data": {
                        "stage": "database", "error": f"Produkt konnte nicht gespeichert werden: {str(exc)[:200]}"}}))
                    return
            await self.ws.send_text(json.dumps({"type": type_, "data": data}))
        except Exception:
            pass


@app.get("/health")
def health():
    return {"ok": True, "providers": PROVIDERS, "database": "sqlite"}


class SpeechRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=500)
    text: str = Field(min_length=1, max_length=5000)
    voice_id: str = Field(default="JBFqnCBsd6RMkjVDRZzb", min_length=3, max_length=100)
    model_id: str = Field(default="eleven_multilingual_v2", max_length=100)


class VideoRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=500)
    prompt: str = Field(min_length=1, max_length=2000)
    model_slug: str = Field(default="minimax/video-01", min_length=5, max_length=180)
    duration_seconds: int = Field(default=5, ge=3, le=10)


@app.post("/api/media/audio")
async def api_generate_audio(req: SpeechRequest):
    try:
        return await generate_speech(api_key=req.api_key, text=req.text, voice_id=req.voice_id, model_id=req.model_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Zeitüberschreitung beim Audioanbieter. Versuch es erneut.") from exc


@app.post("/api/media/video")
async def api_generate_video(req: VideoRequest):
    try:
        return await generate_video(api_key=req.api_key, prompt=req.prompt, model_slug=req.model_slug, duration_seconds=req.duration_seconds)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Videogenerierung dauert zu lange. Prüfe das Modell bei Replicate und versuche es erneut.") from exc


class ProductCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=20000)
    price: float = Field(default=0, ge=0, le=1000000)
    niche: str = Field(default="", max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=50)


class ProductUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=20000)
    price: float | None = Field(default=None, ge=0, le=1000000)
    niche: str | None = Field(default=None, max_length=120)
    tags: list[str] | None = Field(default=None, max_length=50)


@app.get("/api/products")
def api_list_products():
    return {"products": list_products()}


@app.post("/api/products", status_code=201)
def api_create_product(req: ProductCreate):
    payload = req.model_dump()
    payload["title"] = payload["title"].strip()
    if not payload["title"]:
        raise HTTPException(422, "Der Titel darf nicht leer sein.")
    payload["tags"] = [str(tag).strip()[:100] for tag in payload["tags"] if str(tag).strip()][:50]
    payload.update({"id": str(uuid.uuid4()), "provider": "manual", "image_url": None, "image_urls": [], "mockup_urls": []})
    return save_product(payload)


@app.get("/api/products/{product_id}")
def api_get_product(product_id: str):
    try:
        product = get_product(product_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if product is None:
        raise HTTPException(404, "Produkt nicht gefunden.")
    return product


@app.put("/api/products/{product_id}")
def api_update_product(product_id: str, req: ProductUpdate):
    patch = req.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(400, "Keine Änderungen übermittelt.")
    for key, value in patch.items():
        if value is None:
            raise HTTPException(422, f"Das Feld {key} darf nicht null sein.")
    if "title" in patch:
        patch["title"] = patch["title"].strip()
        if not patch["title"]:
            raise HTTPException(422, "Der Titel darf nicht leer sein.")
    if "tags" in patch and patch["tags"] is not None:
        patch["tags"] = [str(tag).strip()[:100] for tag in patch["tags"] if str(tag).strip()][:50]
    try:
        product = update_product(product_id, patch)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if product is None:
        raise HTTPException(404, "Produkt nicht gefunden.")
    return product


@app.delete("/api/products/{product_id}")
def api_delete_product(product_id: str):
    try:
        deleted = delete_product(product_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not deleted:
        raise HTTPException(404, "Produkt nicht gefunden.")
    return {"ok": True, "id": product_id}


class CharacterInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    appearance: str = Field(default="", max_length=4000)
    style: str = Field(default="anime", max_length=120)
    reference_prompt: str = Field(default="", max_length=3000)
    reference_image_data_url: str = Field(default="", max_length=8_000_000)

class StoryInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    premise: str = Field(min_length=1, max_length=5000)
    style: str = Field(default="webtoon, clean line art", max_length=500)
    language: str = Field(default="Deutsch", max_length=40)
    panel_count: int = Field(default=4, ge=1, le=12)
    character_ids: list[str] = Field(default_factory=list, max_length=12)
    generate_images: bool = False
    image: dict = Field(default_factory=dict)
    reference_data_url: str = Field(default="", max_length=8_000_000)

class GameAssetInput(BaseModel):
    api_key: str = Field(min_length=1, max_length=1000)
    name: str = Field(min_length=1, max_length=160)
    prompt: str = Field(min_length=1, max_length=2000)
    asset_type: str = Field(default="sprite", max_length=40)
    width: int = Field(default=128, ge=16, le=768)
    height: int = Field(default=128, ge=16, le=768)
    transparent: bool = True
    seed: int | None = Field(default=None, ge=0, le=2147483647)
    reference_data_url: str = Field(default="", max_length=8_000_000)


@app.get("/api/game-assets")
def game_assets_list():
    return {"assets": list_game_assets()}


@app.post("/api/game-assets/generate", status_code=201)
async def game_asset_generate(req: GameAssetInput):
    name = req.name.strip()
    if not name:
        raise HTTPException(422, "Bitte einen Asset-Namen eingeben.")
    reference = parse_reference_data_url(req.reference_data_url)
    try:
        path = await PixelLabClient(req.api_key).generate(req.prompt, req.width, req.height, req.transparent, req.seed, reference=reference)
    except PixelLabError as exc:
        message = str(exc)
        status = 502
        if "API-Key" in message: status = 401
        elif "Guthaben/Credits" in message: status = 402
        elif "Limit erreicht" in message: status = 429
        raise HTTPException(status, message) from exc
    item = save_game_asset({"name": name, "prompt": req.prompt.strip(), "asset_type": req.asset_type,
        "width": req.width, "height": req.height, "transparent": req.transparent, "provider": "pixellab", "reference_used": bool(reference),
        "image_url": "/static/assets/" + path.name})
    return item


@app.delete("/api/game-assets/{asset_id}")
def game_asset_delete(asset_id: str):
    image_url = delete_game_asset(asset_id)
    if not image_url:
        raise HTTPException(404, "Game-Asset nicht gefunden.")
    filename = Path(image_url).name
    path = (BASE / "output" / "assets" / filename).resolve()
    assets_root = (BASE / "output" / "assets").resolve()
    if path.parent == assets_root and path.name.startswith("pixellab_") and path.exists():
        path.unlink()
    return {"ok": True, "id": asset_id}


@app.get("/api/story/characters")
def story_characters_list():
    return {"characters": list_characters()}

@app.post("/api/story/characters", status_code=201)
def story_character_create(req: CharacterInput):
    data=req.model_dump(); data["name"]=data["name"].strip()
    if not data["name"]: raise HTTPException(422, "Charaktername darf nicht leer sein.")
    return save_character(data)

@app.put("/api/story/characters/{character_id}")
def story_character_update(character_id: str, req: CharacterInput):
    if not get_character(character_id): raise HTTPException(404, "Charakter nicht gefunden.")
    existing=get_character(character_id)
    data={**existing, **req.model_dump(), "id":character_id}; data["name"]=data["name"].strip()
    if not data["name"]: raise HTTPException(422, "Charaktername darf nicht leer sein.")
    return save_character(data)

@app.delete("/api/story/characters/{character_id}")
def story_character_delete(character_id: str):
    if not delete_character(character_id): raise HTTPException(404, "Charakter nicht gefunden.")
    return {"ok":True,"id":character_id}

@app.post("/api/story/characters/{character_id}/portraits")
async def story_character_portraits(character_id: str, payload: dict):
    char=get_character(character_id)
    if not char: raise HTTPException(404, "Charakter nicht gefunden.")
    cfg=dict(payload.get("image") or {})
    provider=str(cfg.get("provider", "placeholder")).lower()
    if provider not in IMAGE_PROVIDERS: raise HTTPException(422, "Unbekannter Bildanbieter.")
    missing=[f for f in REQUIRED[provider] if not str(cfg.get(f, "")).strip()]
    if missing: raise HTTPException(422, "Bildanbieter benötigt: "+", ".join(missing))
    from services.image_generator import ImageGeneratorService
    reference = parse_reference_data_url(str(payload.get("reference_data_url") or char.get("reference_image_data_url") or ""))
    if reference and provider not in ("gemini", "openai", "local"):
        raise HTTPException(422, "Für eine echte Bildvorlage wähle Gemini, OpenAI Bilder oder die lokale Stable-Diffusion-WebUI.")
    service=ImageGeneratorService(); portraits=dict(char.get("portraits") or {}); errors={}
    for emotion in ("neutral", "angry", "happy", "surprised"):
        prompt=(f"{char.get('style','anime')} character portrait sheet, single head-and-shoulders portrait, same exact character identity. "
                f"Character name: {char['name']}. Appearance: {char.get('appearance','')}. Personality: {char.get('description','')}. "
                f"Continuity rules: {char.get('reference_prompt','')}. Facial expression only: {emotion}. Keep hairstyle, eye color, clothing and proportions unchanged. "
                "Centered bust portrait, plain simple background, no text, no labels, high-quality game dialogue sprite.")
        try:
            path=await service.generate_asset(cfg, prompt, negative_prompt="different character, changed hairstyle, changed clothes, text, watermark, extra face", reference=reference)
            portraits[emotion]="/static/assets/"+path.name
        except Exception as exc:
            errors[emotion]=str(exc)[:240]
    char["portraits"]=portraits
    char["portrait_errors"]=errors
    saved=save_character(char)
    return {"character":saved,"errors":errors}


@app.get("/api/story/stories")
def story_list(): return {"stories":list_stories()}

@app.get("/api/story/stories/{story_id}")
def story_get(story_id: str):
    item=get_story(story_id)
    if not item: raise HTTPException(404,"Geschichte nicht gefunden.")
    return item

@app.delete("/api/story/stories/{story_id}")
def story_delete(story_id: str):
    if not delete_story(story_id): raise HTTPException(404,"Geschichte nicht gefunden.")
    return {"ok":True,"id":story_id}

@app.post("/api/story/stories", status_code=201)
async def story_create(req: StoryInput):
    chars=[]
    for ident in req.character_ids:
        char=get_character(ident)
        if not char: raise HTTPException(422, f"Unbekannter Charakter: {ident}")
        chars.append(char)
    # Build beat-by-beat prompts with a fixed character/style bible to encourage continuity.
    beats=[x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+",req.premise.strip()) if x.strip()]
    if not beats: beats=[req.premise.strip()]
    reference = parse_reference_data_url(req.reference_data_url or next((str(c.get("reference_image_data_url") or "") for c in chars if c.get("reference_image_data_url")), ""))
    if reference and req.generate_images and str((req.image or {}).get("provider", "placeholder")).lower() not in ("gemini", "openai", "local"):
        raise HTTPException(422, "Für eine echte Bildvorlage wähle Gemini, OpenAI Bilder oder die lokale Stable-Diffusion-WebUI.")
    panels=[]
    for i in range(req.panel_count):
        beat=beats[min(i, len(beats)-1)] if len(beats)>=req.panel_count else (beats[i] if i<len(beats) else f"Fortsetzung der Handlung: {req.premise.strip()}")
        char_bible="; ".join(f"{c['name']}: {c.get('appearance','')} ({c.get('description','')}); continuity rules: {c.get('reference_prompt','')}" for c in chars) or "No named character profile; use scene-appropriate characters."
        prompt=f"{req.style}. Panel {i+1} of {req.panel_count}; visual continuity across the same story. Character bible: {char_bible}. Scene/action: {beat}. Compose as a single comic/webtoon panel, consistent face, hairstyle, clothing and proportions, clear focal point, no extra fingers, no text or speech bubbles, leave readable negative space for later lettering."
        panel={"number":i+1,"beat":beat,"prompt":prompt,"image_url":None,"status":"prompt_ready"}
        if req.generate_images:
            try:
                from services.image_generator import ImageGeneratorService
                cfg=dict(req.image or {})
                provider=str(cfg.get('provider','placeholder')).lower()
                if provider not in IMAGE_PROVIDERS: raise ValueError('Unbekannter Bildanbieter.')
                missing=[f for f in REQUIRED[provider] if not str(cfg.get(f,'')).strip()]
                if missing: raise ValueError('Bildanbieter benötigt: '+', '.join(missing))
                path=await ImageGeneratorService().generate_asset(cfg,prompt,negative_prompt="inconsistent character design, watermark, logo, blurry face",reference=reference)
                panel['image_url']='/static/assets/'+path.name; panel['status']='generated'
            except Exception as exc:
                panel['status']='image_error'; panel['error']=str(exc)[:300]
        panels.append(panel)
    story={"title":req.title.strip(),"premise":req.premise.strip(),"style":req.style,"language":req.language,"panel_count":req.panel_count,"character_ids":req.character_ids,"characters":[{k:v for k,v in c.items() if k != "reference_image_data_url"} for c in chars],"panels":panels,"reference_used":bool(reference)}
    return save_story(story)


class ModelsReq(BaseModel):
    provider: str
    api_key: str = ""
    base_url: str = ""


@app.post("/models")
async def models(req: ModelsReq):
    """Modellliste eines Anbieters. Der Key wird nur für diese Anfrage genutzt, nicht gespeichert."""
    try:
        return {"models": await LLMGateway().list_models(req.provider.lower(), req.api_key.strip(), req.base_url.strip())}
    except LLMError as e:
        msg = str(e)
        raise HTTPException(400, "Key wurde abgelehnt." if "HTTP 401" in msg or "HTTP 403" in msg else msg)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Anbieter nicht erreichbar: {e}")


def validate(cmd: dict, publish: bool):
    provider = str(cmd.get("provider", "")).lower()
    category = str(cmd.get("category", "")).strip()[:120]
    if provider not in PROVIDERS or not category:
        return "Nische oder Anbieter ungültig."
    if provider == "custom":
        if not str(cmd.get("base_url", "")).strip() or not str(cmd.get("model", "")).strip():
            return "Eigener Anbieter: Base-URL und Modellname fehlen."
    elif not str(cmd.get("api_key", "")).strip():
        return f"Es fehlt der Key für {provider}."
    img = cmd.get("image") or {}
    ip = str(img.get("provider", "pollinations")).lower()
    if ip not in IMAGE_PROVIDERS:
        return "Unbekannter Bildanbieter."
    miss = [f for f in REQUIRED[ip] if not str(img.get(f, "")).strip()]
    if miss:
        return f"Bildanbieter {ip}: Angaben fehlen ({', '.join(miss)})."
    ref = cmd.get("reference")
    if ref:
        if not isinstance(ref, dict) or ref.get("mode") not in (("style", "direct", "asset") if cmd.get("action") == "start_content" else ("style", "direct")):
            return "Referenzbild: ungültiger Modus."
        if not REF_RE.match(str(ref.get("data_url", ""))) or len(str(ref.get("data_url"))) > 8_000_000:
            return "Referenzbild: ungültig oder zu groß (PNG, JPEG oder WebP bis ca. 6 MB)."
        if ref["mode"] == "direct" and ip not in IMG2IMG:
            return "Bild-zu-Bild geht nur mit Gemini, OpenAI oder Lokal. Wähl 'Stil übernehmen' oder wechsle den Bildanbieter."
    if cmd.get("shopify_enabled"):
        sh = cmd.get("shopify") or {}
        g = lambda k: str(sh.get(k, "")).strip()
        if not SHOP_RE.match(g("shop").lower()):
            return "Shopify: Die Shop-Adresse muss wie mein-shop.myshopify.com aussehen."
        if not g("access_token") and not (g("client_id") and g("client_secret")):
            return "Shopify: Trag entweder den Admin-Token oder Client-ID und Client-Secret ein."
    if publish:
        etsy = cmd.get("etsy") or {}
        missing = [f for f in ETSY_FIELDS if not str(etsy.get(f, "")).strip()]
        if missing:
            return "Etsy-Angaben fehlen: " + ", ".join(missing)
    return None


def validate_studio(cmd: dict):
    err = validate(cmd, False)
    if err:
        return err
    mods = cmd.get("modules")
    if not isinstance(mods, list) or not mods or any(m not in MODULES for m in mods):
        return "Wähl mindestens ein Modul (Merch, Brand-Kit, Mockups)."
    return None


def validate_content(cmd: dict):
    err = validate(cmd, False)
    if err:
        return err
    mods = cmd.get("modules")
    if not isinstance(mods, list) or not mods or any(m not in CONTENT_MODULES for m in mods):
        return "Wähl mindestens ein Modul (Thumbnails, Streamer-Paket, Banner)."
    if "thumbnails" in mods and not (isinstance(cmd.get("formats"), list) and cmd["formats"] and all(f in FORMATS for f in cmd["formats"])):
        return "Wähl mindestens ein Thumbnail-Format."
    if "banners" in mods and not (isinstance(cmd.get("banners"), list) and cmd["banners"] and all(b in BANNERS for b in cmd["banners"])):
        return "Wähl mindestens ein Banner-Format."
    return None


async def run_job(sess: Session, cmd: dict, publish: bool):
    try:
        count = max(1, min(5, int(cmd.get("image_count", 1))))
    except (TypeError, ValueError):
        count = 1
    keys = {"llm_key": str(cmd.get("api_key", "")).strip(), "base_url": str(cmd.get("base_url", "")).strip(), "model": str(cmd.get("model", "")).strip(),
            "image": {k: str((cmd.get("image") or {}).get(k, "")).strip() for k in ("provider", "key", "account_id", "base_url", "model")},
            "etsy": {k: str((cmd.get("etsy") or {}).get(k, "")).strip() for k in ETSY_FIELDS},
            "mockups": bool(cmd.get("mockups")), "shopify_on": bool(cmd.get("shopify_enabled")),
            "shopify": {k: str((cmd.get("shopify") or {}).get(k, "")).strip() for k in SHOPIFY_FIELDS}}
    m = REF_RE.match(str((cmd.get("reference") or {}).get("data_url", "")))
    keys["reference"] = {"mime": m.group(1), "b64": re.sub(r"\s", "", m.group(2)), "mode": cmd["reference"]["mode"]} if m else None
    niche, provider = str(cmd["category"]).strip()[:120], cmd["provider"].lower()
    try:
        if cmd.get("action") == "start_content":
            opts = {"variants": max(1, min(3, count)), "formats": cmd.get("formats") or ["yt"], "banners": cmd.get("banners") or [],
                    "language": "Englisch" if cmd.get("language") == "Englisch" else "Deutsch", "hint": str(cmd.get("hint", "")).strip()[:300]}
            await ContentPipeline(sess).run(niche, provider, cmd["modules"], keys, opts)
        elif cmd.get("action") == "start_studio":
            await StudioPipeline(sess).run(niche, provider, cmd["modules"], keys, max(1, min(3, count)))
        else:
            await AgentFactoryPipeline(sess).run(niche, provider, publish, keys, count)
    finally:
        sess.running = False


@app.websocket("/ws/factory")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    sess = Session(ws)
    await sess.send("HELLO", {"providers": PROVIDERS})
    try:
        while True:
            cmd = json.loads(await ws.receive_text())
            act = cmd.get("action")
            if act not in ("start_production", "start_studio", "start_content"):
                continue
            publish = bool(cmd.get("publish", False)) and act == "start_production"
            err = "Es läuft bereits ein Durchlauf." if sess.running else (
                validate_studio(cmd) if act == "start_studio" else validate_content(cmd) if act == "start_content" else validate(cmd, publish))
            if err:
                await sess.send("RUN_FAILED", {"stage": "factory", "error": err})
                await sess.send("RUN_FINISHED", {})
            else:
                sess.running = True
                asyncio.create_task(run_job(sess, cmd, publish))
    except WebSocketDisconnect:
        pass
