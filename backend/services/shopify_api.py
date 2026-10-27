"""Shopify Admin GraphQL API: legt Produkte als ENTWURF an (Bilder per staged upload).
Zugang entweder per festem Admin-Token (ältere Custom Apps) oder per Client-ID und Client-Secret (Dev Dashboard, Token hält 24 Stunden)."""
import html, re
from pathlib import Path
import httpx

DEFAULT_VERSION = "2026-04"
SHOP_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$")
HOST = "https://{shop}"  # in Tests umbiegbar


class ShopifyError(Exception):
    pass


def to_html(text: str) -> str:
    paras = [p.strip() for p in re.split(r"\n\s*\n", str(text)) if p.strip()]
    return "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paras)


class ShopifyService:
    def __init__(self, creds: dict):
        self.shop = creds.get("shop", "").strip().lower()
        self.token = creds.get("access_token", "").strip()
        self.client_id = creds.get("client_id", "").strip()
        self.client_secret = creds.get("client_secret", "").strip()
        self.version = creds.get("api_version", "").strip() or DEFAULT_VERSION

    @property
    def base(self):
        return HOST.format(shop=self.shop)

    async def _ensure_token(self, c: httpx.AsyncClient):
        if self.token:
            return
        r = await c.post(f"{self.base}/admin/oauth/access_token",
                         data={"client_id": self.client_id, "client_secret": self.client_secret, "grant_type": "client_credentials"})
        if r.status_code != 200 or "access_token" not in r.text:
            hint = (" Client Credentials funktionieren nur, wenn App und Shop zur selben Organisation gehören. "
                    "Sonst brauchst du einen festen Admin-Token.") if "cannot be performed" in r.text or "shop_not_permitted" in r.text else ""
            raise ShopifyError(f"Shopify: Anmeldung fehlgeschlagen (HTTP {r.status_code}). Prüfe Shop-Adresse, Client-ID und Secret.{hint}")
        self.token = r.json()["access_token"]

    async def _gql(self, c: httpx.AsyncClient, query: str, variables: dict) -> dict:
        r = await c.post(f"{self.base}/admin/api/{self.version}/graphql.json", json={"query": query, "variables": variables},
                         headers={"X-Shopify-Access-Token": self.token})
        if r.status_code in (401, 403):
            raise ShopifyError("Shopify: Zugang abgelehnt. Prüfe Token und Berechtigungen (write_products und write_files) und ob die App im Shop installiert ist.")
        if r.status_code == 404:
            raise ShopifyError(f"Shopify: Adresse oder API-Version nicht gefunden ({self.shop}, {self.version}).")
        if r.status_code >= 400:
            raise ShopifyError(f"Shopify HTTP {r.status_code}: {r.text[:200]}")
        j = r.json()
        if j.get("errors"):
            raise ShopifyError(f"Shopify: {str(j['errors'])[:300]}")
        return j["data"]

    @staticmethod
    def _user_errors(node: dict, what: str):
        errs = (node or {}).get("userErrors") or []
        if errs:
            raise ShopifyError(f"Shopify ({what}): " + "; ".join(e.get("message", "?") for e in errs)[:300])

    async def _upload_images(self, c, paths: list) -> list:
        d = await self._gql(c, """mutation($input:[StagedUploadInput!]!){stagedUploadsCreate(input:$input){
            stagedTargets{url resourceUrl parameters{name value}} userErrors{field message}}}""",
                            {"input": [{"resource": "IMAGE", "filename": p.name, "mimeType": "image/png", "httpMethod": "POST"} for p in paths]})
        self._user_errors(d["stagedUploadsCreate"], "Bild-Upload")
        urls = []
        for p, t in zip(paths, d["stagedUploadsCreate"]["stagedTargets"]):
            r = await c.post(t["url"], data={x["name"]: x["value"] for x in t["parameters"]}, files={"file": (p.name, p.read_bytes(), "image/png")})
            if r.status_code >= 300:
                raise ShopifyError(f"Shopify: Bild-Upload fehlgeschlagen (HTTP {r.status_code}).")
            urls.append(t["resourceUrl"])
        return urls

    async def create_draft(self, title: str, description: str, tags: list, price, images: list, product_type: str,
                           digital: bool = False, vendor: str = "", alt: str = "") -> dict:
        async with httpx.AsyncClient(timeout=120) as c:
            await self._ensure_token(c)
            urls = await self._upload_images(c, [Path(p) for p in images[:20]]) if images else []
            product = {"title": str(title)[:255], "descriptionHtml": to_html(description), "productType": product_type,
                       "tags": [str(t)[:60] for t in tags][:30], "status": "DRAFT"}
            if vendor:
                product["vendor"] = vendor[:255]
            d = await self._gql(c, """mutation($product:ProductCreateInput!,$media:[CreateMediaInput!]){
                productCreate(product:$product,media:$media){product{id variants(first:1){nodes{id}}} userErrors{field message}}}""",
                                {"product": product, "media": [{"originalSource": u, "alt": (alt or title)[:250], "mediaContentType": "IMAGE"} for u in urls]})
            self._user_errors(d["productCreate"], "Produkt")
            pid = d["productCreate"]["product"]["id"]
            warning = None
            try:  # Preis (und bei Downloads: kein Versand) steckt in der Standard-Variante
                vid = d["productCreate"]["product"]["variants"]["nodes"][0]["id"]
                v = {"id": vid, "price": f"{float(price):.2f}"}
                if digital:
                    v["inventoryItem"] = {"requiresShipping": False}
                u = await self._gql(c, """mutation($pid:ID!,$v:[ProductVariantsBulkInput!]!){
                    productVariantsBulkUpdate(productId:$pid,variants:$v){productVariants{id} userErrors{field message}}}""", {"pid": pid, "v": [v]})
                self._user_errors(u["productVariantsBulkUpdate"], "Preis")
            except (ShopifyError, KeyError, IndexError, ValueError) as e:
                warning = f"Produkt angelegt, aber der Preis konnte nicht gesetzt werden: {e}"
        num = pid.rsplit("/", 1)[-1]
        store = self.shop.removesuffix(".myshopify.com")
        return {"id": pid, "url": f"https://admin.shopify.com/store/{store}/products/{num}", "warning": warning}
