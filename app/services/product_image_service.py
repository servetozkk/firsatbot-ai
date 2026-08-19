from __future__ import annotations

import html as html_module
import json
import re
from collections.abc import Iterable
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit

try:
    from selectolax.parser import HTMLParser
except Exception:  # pragma: no cover - uygulama selectolax ile geliyor
    HTMLParser = None

_IMAGE_EXT_RE = re.compile(r"\.(?:jpe?g|png|webp|avif)(?:$|[?#])", re.I)
_URL_RE = re.compile(r"https?://[^\s\"'<>\\]+", re.I)
_JSON_IMAGE_KEY_RE = re.compile(
    r'(?i)[\"\'](?:image|images|imageUrl|imageUrls|gallery|media|contentUrl|zoomImage|largeImage)[\"\']\s*:\s*'
)
_DIMENSION_RE = re.compile(r"(?<!\d)(\d{2,4})[xX](\d{2,4})(?!\d)")

# Ürün fotoğrafı olmayan varlıkların URL/path parçaları.
_BLOCKED_TOKENS = {
    "logo", "logos", "icon", "icons", "sprite", "avatar", "badge", "badges",
    "payment", "banner", "banners", "placeholder", "favicon", "loader", "loading",
    "merchant-logo", "merchant_logo", "seller-logo", "seller_logo", "store-logo",
    "brand-logo", "brand_logo", "campaign", "campaigns", "coupon", "kupon",
    "cargo", "shipping", "delivery", "rating", "stars", "star-rating", "trust",
    "secure", "certificate", "seal", "footer", "header", "appstore", "googleplay",
    "qr-code", "qrcode", "social", "facebook", "instagram", "youtube", "tiktok",
    "flag", "country", "bank", "credit-card", "wallet", "trgo", "tr-go",
    "receipt", "invoice", "fatura", "etiket", "watermark", "no-image", "noimage",
    "empty-image", "default-image", "blank-image", "pixel.gif", "tracking-pixel",
    "analytics", "advert", "reklam", "promotion", "promo", "thumbnail-video",
    "recommendation", "recommended", "widget", "cross-sell", "cross_sell",
    "upsell", "marketing", "newsletter", "breadcrumb", "navigation", "menu-icon",
    "review-avatar", "review_image", "user-content", "customer-image",
    "installment", "taksit", "warranty", "garanti-logo", "service-logo",
    "bank-logo", "card-logo", "advantage", "worldcard", "maximum", "bonus-card",
    "category-banner", "category_image", "landing-page", "mobile-app",
}

# URL'de bunlar varsa gerçek ürün medyası olma ihtimali yüksektir.
_PRODUCT_HINTS = {
    "product", "products", "product-image", "product_image", "productmedia",
    "product-media", "gallery", "images", "image", "media", "zoom", "large",
    "original", "detail", "pim", "catalog", "catalogue", "cdn.dsmcdn.com/ty",
    "productimages", "productimages.hepsiburada", "m.media-amazon", "images-na.ssl",
}

_GALLERY_SELECTORS = (
    '[class*="gallery"] img', '[id*="gallery"] img', '[data-testid*="gallery"] img',
    '[class*="product-image"] img', '[class*="productImage"] img',
    '[class*="product-media"] img', '[class*="productMedia"] img',
    '[class*="carousel"] img', '[class*="slider"] img',
    'img[data-zoom-image]', 'img[data-large-image]', 'img[data-original]',
    'meta[property="og:image"]', 'meta[name="twitter:image"]',
)


def _extract_dimensions(value: str) -> tuple[int, int] | None:
    """URL/path veya query içindeki açık boyut bilgisini döndürür."""
    text = html_module.unescape(str(value or ""))
    matches = _DIMENSION_RE.findall(text)
    if matches:
        # En büyük çifti seç; bazen URL'de hem thumb hem original geçebilir.
        return max(((int(w), int(h)) for w, h in matches), key=lambda pair: pair[0] * pair[1])

    try:
        query = parse_qs(urlsplit(text).query)
    except Exception:
        return None
    width_values = query.get("width") or query.get("w") or query.get("wid") or []
    height_values = query.get("height") or query.get("h") or query.get("hei") or []
    try:
        if width_values and height_values:
            return int(width_values[0]), int(height_values[0])
    except (TypeError, ValueError):
        return None
    return None


def _looks_too_small(url: str) -> bool:
    dimensions = _extract_dimensions(url)
    if not dimensions:
        return False
    width, height = dimensions
    # 1x1 pixel, küçük ikon ve mağaza logolarını ele. Uzun/dar swatch'lar da alınmaz.
    return width < 260 or height < 260 or min(width, height) / max(width, height) < 0.38


def _is_blocked_asset(url: str) -> bool:
    lower = html_module.unescape(url).lower()
    normalized = re.sub(r"[^a-z0-9çğıöşü_-]+", "-", lower)
    if any(token in lower or token in normalized for token in _BLOCKED_TOKENS):
        return True
    path = urlsplit(lower).path
    filename = path.rsplit("/", 1)[-1]
    path_parts = [part for part in path.split("/") if part]
    noisy_segments = {
        "banners", "banner", "campaign", "campaigns", "widgets", "widget",
        "logos", "logo", "icons", "icon", "badges", "badge", "avatars",
        "reviews", "review", "recommendations", "recommendation", "marketing",
        "navigation", "footer", "header", "payments", "payment", "banks",
    }
    if any(part in noisy_segments for part in path_parts):
        return True
    # logo1.webp gibi birleşik dosya adlarını da yakala.
    if re.search(r"(?:^|[-_.])(logo|icon|badge|banner|placeholder|sprite|avatar|trgo|receipt|invoice)(?:[-_.0-9]|$)", filename):
        return True
    return _looks_too_small(url)


def _normalize_url(url: str, base_url: str | None = None) -> str | None:
    value = html_module.unescape(str(url or "").strip().strip('"\''))
    value = value.replace("\\u002F", "/").replace("\\/", "/")
    if not value or value.startswith(("data:", "blob:", "javascript:")):
        return None
    if value.startswith("//"):
        value = "https:" + value
    elif base_url and value.startswith("/"):
        value = urljoin(base_url, value)
    if not value.startswith(("http://", "https://")):
        return None
    lower = value.lower()
    if _is_blocked_asset(value):
        return None
    if any(lower.split("?", 1)[0].endswith(ext) for ext in (".js", ".css", ".svg", ".woff", ".woff2", ".json", ".mp4", ".webm", ".gif")):
        return None
    image_hint = any(token in lower for token in _PRODUCT_HINTS)
    transform_hint = any(token in lower for token in ("width=", "height=", "quality=", "format=", "resize=", "imwidth="))
    if not (_IMAGE_EXT_RE.search(value) or image_hint or transform_hint):
        return None

    # Açıkça kampanya/içerik varlığı olan CDN yollarını, uzantısı resim olsa bile alma.
    path_lower = urlsplit(lower).path
    if any(token in path_lower for token in (
        "/cms/", "/content/banner", "/campaign/", "/marketing/",
        "/recommendation/", "/widgets/", "/navigation/", "/footer/",
        "/header/", "/payment/", "/bank/", "/reviews/",
    )):
        return None
    return value


def canonical_image_key(url: str) -> str:
    parts = urlsplit(url)
    path = re.sub(r"/(?:small|medium|large|thumbnail|thumb|zoom)/", "/", parts.path, flags=re.I)
    path = re.sub(r"[-_](?:\d{2,4}x\d{2,4}|\d{2,4})\.(jpg|jpeg|png|webp|avif)$", r".\1", path, flags=re.I)
    # CDN dönüşüm parametrelerini kaldırarak aynı fotoğrafın thumb/original kopyalarını birleştir.
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path.lower(), "", ""))


def _quality_score(url: str, *, primary: str | None = None) -> int:
    lower = url.lower()
    score = 0
    if primary and canonical_image_key(url) == canonical_image_key(primary):
        score += 10_000
    if any(token in lower for token in _PRODUCT_HINTS):
        score += 120
    if any(token in lower for token in ("zoom", "large", "original", "quality=100", "imwidth=1200")):
        score += 80
    dimensions = _extract_dimensions(url)
    if dimensions:
        width, height = dimensions
        score += min((width * height) // 20_000, 250)
        if width >= 600 and height >= 600:
            score += 120
    if _IMAGE_EXT_RE.search(url):
        score += 20
    return score


def dedupe_image_urls(
    values: Iterable[str], *, base_url: str | None = None, limit: int = 60, primary: str | None = None
) -> list[str]:
    best_by_key: dict[str, tuple[int, int, str]] = {}
    for position, raw in enumerate(values):
        url = _normalize_url(raw, base_url)
        if not url:
            continue
        key = canonical_image_key(url)
        candidate = (_quality_score(url, primary=primary), -position, url)
        if key not in best_by_key or candidate[:2] > best_by_key[key][:2]:
            best_by_key[key] = candidate

    ranked = sorted(best_by_key.values(), key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in ranked[:limit]]


def _walk_json(value, output: list[str], *, trusted: bool = False) -> None:
    if isinstance(value, str):
        if trusted and value.startswith(("http://", "https://", "//", "/")):
            output.append(value)
        return
    if isinstance(value, list):
        for item in value:
            _walk_json(item, output, trusted=trusted)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            key_lower = str(key).lower()
            image_key = any(token in key_lower for token in ("image", "gallery", "media", "photo", "picture", "contenturl"))
            if image_key:
                _walk_json(item, output, trusted=True)
            elif isinstance(item, (dict, list)):
                _walk_json(item, output, trusted=False)


def _extract_attrs_from_fragment(fragment: str, candidates: list[str]) -> None:
    attr_pattern = re.compile(
        r'(?i)(?:src|data-src|data-original|data-zoom-image|data-large-image|content)\s*=\s*["\']([^"\']+)["\']'
    )
    candidates.extend(attr_pattern.findall(fragment))
    for srcset in re.findall(r'(?i)srcset\s*=\s*["\']([^"\']+)["\']', fragment):
        candidates.extend(part.strip().split()[0] for part in srcset.split(",") if part.strip())


def _collect_from_gallery_nodes(text: str, candidates: list[str]) -> None:
    if not text:
        return

    if HTMLParser is not None:
        try:
            tree = HTMLParser(text)
            seen_nodes: set[int] = set()
            for selector in _GALLERY_SELECTORS:
                try:
                    nodes = tree.css(selector)
                except Exception:
                    continue
                for node in nodes:
                    marker = id(node)
                    if marker in seen_nodes:
                        continue
                    seen_nodes.add(marker)
                    attrs = node.attributes or {}
                    for name in ("src", "data-src", "data-original", "data-zoom-image", "data-large-image", "content"):
                        value = attrs.get(name)
                        if value:
                            candidates.append(value)
                    srcset = attrs.get("srcset")
                    if srcset:
                        candidates.extend(part.strip().split()[0] for part in srcset.split(",") if part.strip())
            return
        except Exception:
            pass

    # selectolax yoksa veya HTML bozuksa güvenli regex geri dönüşü.
    # Yalnızca gallery/product-media/carousel benzeri kapsayıcıların yakın çevresini tarar.
    for match in re.finditer(
        r'(?is)<(?:div|section|ul)[^>]*(?:class|id)=["\'][^"\']*(?:gallery|product[-_ ]?(?:image|media)|carousel|slider)[^"\']*["\'][^>]*>',
        text,
    ):
        fragment = text[match.start(): match.start() + 50_000]
        closing = re.search(r'(?is)</(?:div|section|ul)>', fragment)
        if closing:
            fragment = fragment[: closing.end()]
        _extract_attrs_from_fragment(fragment, candidates)

    # Kapsayıcı bulunmasa bile doğrudan zoom/original attribute'ları yüksek güvenlidir.
    for tag in re.findall(r'(?is)<img[^>]+(?:data-zoom-image|data-large-image|data-original)=[^>]+>', text):
        _extract_attrs_from_fragment(tag, candidates)


def collect_image_urls(html: str, *, primary: str | None = None, base_url: str | None = None, limit: int = 60) -> list[str]:
    """Yalnızca ürün galerisi olma ihtimali yüksek görselleri toplar.

    Önceki sürümde sayfadaki bütün URL'ler tarandığı için logo, rozet ve banner'lar
    galeriye girebiliyordu. Bu sürüm galeri düğümleri, güvenilir JSON image alanları
    ve mağazaların ürün medyası yapılarını esas alır.
    """
    candidates: list[str] = []
    if primary:
        candidates.append(primary)
    text = html or ""

    # Gerçek galeri / ürün medyası düğümleri.
    _collect_from_gallery_nodes(text, candidates)

    # Amazon'un doğrudan ürün galeri haritası.
    for payload in re.findall(r'(?i)data-a-dynamic-image\s*=\s*["\']([^"\']+)["\']', text):
        try:
            decoded = html_module.unescape(payload)
            data = json.loads(decoded)
            candidates.extend(data.keys() if isinstance(data, dict) else [])
        except Exception:
            candidates.extend(_URL_RE.findall(payload))

    # JSON-LD ve gömülü store-state içindeki yalnızca image/gallery anahtarları.
    for script in re.findall(r'(?is)<script[^>]*>(.*?)</script>', text):
        stripped = html_module.unescape(script.strip())
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
            _walk_json(parsed, candidates)
        except Exception:
            if _JSON_IMAGE_KEY_RE.search(stripped):
                # Bütün script URL'lerini almak yerine image anahtarı yakınındaki URL'leri al.
                for match in _JSON_IMAGE_KEY_RE.finditer(stripped):
                    window = stripped[match.end(): match.end() + 12_000]
                    candidates.extend(_URL_RE.findall(window)[:80])

    # Sayfanın tamamındaki kaçak URL'leri artık özellikle toplamıyoruz.
    return dedupe_image_urls(candidates, base_url=base_url, limit=limit, primary=primary)


def serialize_image_gallery(urls: Iterable[str]) -> str | None:
    cleaned = dedupe_image_urls(urls)
    return json.dumps(cleaned, ensure_ascii=False) if cleaned else None


def parse_image_gallery(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return dedupe_image_urls([str(item) for item in value])
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed = parsed.get("images") or parsed.get("urls") or parsed.get("gallery") or []
        if isinstance(parsed, list):
            return dedupe_image_urls([str(item) for item in parsed])
    except Exception:
        pass
    return dedupe_image_urls(re.split(r"[\n\r|;]+|,(?=\s*https?://)", text))

def persist_product_images(db, *, product_id:int, primary:str|None=None, gallery=None, source:str|None=None, replace:bool=False):
    from app.database.models import ProductImage, ProductDB
    values=([primary] if primary else []) + parse_image_gallery(gallery)
    cleaned=dedupe_image_urls(values, primary=primary, limit=60)
    if not cleaned:
        return []
    if replace:
        db.query(ProductImage).filter(ProductImage.product_id==product_id).delete(synchronize_session=False)
        db.flush()
    rows=db.query(ProductImage).filter(ProductImage.product_id==product_id).all()
    by_key={r.canonical_key:r for r in rows}
    next_order=max((r.sort_order for r in rows), default=-1)+1
    for pos,url in enumerate(cleaned):
        key=canonical_image_key(url)
        row=by_key.get(key)
        if row is None:
            row=ProductImage(product_id=product_id,image_url=url,canonical_key=key,source=source,sort_order=next_order,is_primary=(pos==0 and not rows))
            next_order+=1
            db.add(row); by_key[key]=row
        elif _quality_score(url,primary=primary)>_quality_score(row.image_url,primary=primary):
            row.image_url=url
    db.flush()
    rows=db.query(ProductImage).filter(ProductImage.product_id==product_id).order_by(ProductImage.is_primary.desc(),ProductImage.sort_order.asc(),ProductImage.id.asc()).all()
    result=dedupe_image_urls([r.image_url for r in rows],primary=primary,limit=60)
    product=db.query(ProductDB).filter(ProductDB.id==product_id).first()
    if product:
        product.image_gallery=serialize_image_gallery(result)
        if result and not product.image: product.image=result[0]
    return result

def load_persistent_product_images(db, product_ids, *, limit:int=60):
    from app.database.models import ProductImage
    ids=sorted({int(v) for v in product_ids if v and int(v)>0})
    if not ids: return []
    rows=db.query(ProductImage).filter(ProductImage.product_id.in_(ids)).order_by(ProductImage.is_primary.desc(),ProductImage.sort_order.asc(),ProductImage.id.asc()).all()
    return dedupe_image_urls([r.image_url for r in rows],limit=limit)
