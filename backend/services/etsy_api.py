from pathlib import Path
import httpx

BASE = "https://openapi.etsy.com/v3/application"
AI_NOTE = "\n\nDesign created with the help of AI tools and reviewed by the shop owner."


class EtsyApiService:
    def __init__(self, creds: dict):
        self.api_key = creds.get("api_key")
        self.shop_id = creds.get("shop_id")
        self.taxonomy_id = creds.get("taxonomy_id")
        self.access_token = creds.get("access_token")
        self.refresh_token = creds.get("refresh_token")
        self.rotated = False  # True, sobald neue Tokens ausgestellt wurden

    def _require(self):
        missing = [n for n, v in [("API-Keystring", self.api_key), ("Shop-ID", self.shop_id),
                                  ("Kategorie-ID", self.taxonomy_id), ("Access-Token", self.access_token)] if not v]
        if missing:
            raise RuntimeError("Etsy-Angaben fehlen: " + ", ".join(missing))

    def _headers(self):
        return {"x-api-key": self.api_key, "Authorization": f"Bearer {self.access_token}"}

    async def _refresh(self, c: httpx.AsyncClient):
        if not self.refresh_token:
            raise RuntimeError("Access-Token abgelaufen und Refresh-Token fehlt")
        r = await c.post("https://api.etsy.com/v3/public/oauth/token",
                         data={"grant_type": "refresh_token", "client_id": self.api_key, "refresh_token": self.refresh_token})
        if r.status_code != 200:
            raise RuntimeError(f"Token-Refresh fehlgeschlagen: {r.text[:200]}")
        j = r.json()
        self.access_token, self.refresh_token = j["access_token"], j["refresh_token"]
        self.rotated = True

    async def _request(self, c: httpx.AsyncClient, method: str, path: str, files=None, **kw) -> httpx.Response:
        """`files` ist eine Factory, damit Dateien beim Retry nach Token-Refresh neu geöffnet werden."""
        r = None
        for attempt in range(2):
            r = await c.request(method, f"{BASE}{path}", headers=self._headers(), files=files() if files else None, **kw)
            if r.status_code == 401 and attempt == 0:
                await self._refresh(c)
                continue
            break
        return r

    @staticmethod
    def clean_tags(tags) -> list:
        out = []
        for t in tags or []:
            t = str(t).strip()[:20].strip()
            if t and t.lower() not in [x.lower() for x in out]:
                out.append(t)
        return out[:13]

    async def create_draft_listing(self, listing: dict, image_paths: list, preview_paths: list | None = None) -> dict:
        self._require()
        payload = {
            "quantity": 999,
            "title": str(listing["title"])[:140],
            "description": str(listing["description"]) + AI_NOTE,
            "price": float(listing["suggested_price"]),
            "who_made": "i_did",
            "when_made": "made_to_order",
            "taxonomy_id": int(self.taxonomy_id),
            "type": "download",
            "is_supply": False,
            "tags": ",".join(self.clean_tags(listing.get("tags"))),
        }
        async with httpx.AsyncClient(timeout=60) as c:
            r = await self._request(c, "POST", f"/shops/{self.shop_id}/listings", data=payload)
            if r.status_code != 201:
                raise RuntimeError(f"Etsy HTTP {r.status_code}: {r.text[:300]}")
            lid = r.json()["listing_id"]
            for rank, path in enumerate(((preview_paths or []) + image_paths)[:10], 1):  # Mockups zuerst, Etsy erlaubt bis zu 10 Bilder
                img = lambda p=path: {"image": (p.name, open(p, "rb"), "image/png")}
                ri = await self._request(c, "POST", f"/shops/{self.shop_id}/listings/{lid}/images", files=img, data={"rank": rank})
                if ri.status_code >= 300:
                    raise RuntimeError(f"Bild-Upload {rank} fehlgeschlagen: {ri.text[:200]}")
            for path in image_paths[:5]:  # digitale Dateien: bis zu 5 pro Listing
                dl = lambda p=path: {"file": (p.name, open(p, "rb"), "image/png")}
                rf = await self._request(c, "POST", f"/shops/{self.shop_id}/listings/{lid}/files", files=dl, data={"name": path.name})
                if rf.status_code >= 300:
                    raise RuntimeError(f"Download-Datei-Upload fehlgeschlagen: {rf.text[:200]}")
        return {"listing_id": lid, "url": f"https://www.etsy.com/your/shops/me/tools/listings/{lid}"}
