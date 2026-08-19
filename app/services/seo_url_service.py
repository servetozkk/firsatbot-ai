from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote

ENGINE_VERSION = "13.6.0"

_TR_MAP = str.maketrans({"ı":"i","İ":"i","ş":"s","Ş":"s","ğ":"g","Ğ":"g","ü":"u","Ü":"u","ö":"o","Ö":"o","ç":"c","Ç":"c"})

def slugify(value: object, fallback: str = "urun") -> str:
    text = str(value or "").translate(_TR_MAP).strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    return text[:100] or fallback

def product_url(name: object, identity_key: object) -> str:
    key = quote(str(identity_key or "").strip(), safe="")
    return f"/urun/{slugify(name)}-p-{key}"

def parse_product_path(value: object) -> tuple[str, str | None]:
    raw = str(value or "").strip()
    if "-p-" not in raw:
        return raw, None
    slug, key = raw.rsplit("-p-", 1)
    return key.strip(), slug.strip() or None

def canonical_product_url(base_url: object, name: object, identity_key: object) -> str:
    return str(base_url).rstrip("/") + product_url(name, identity_key)
