from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, asdict
from typing import Iterable

from sqlalchemy.orm import Session

from app.database.models import ProductDB
from app.services.data_integrity_service import record_admin_action


KNOWN_BRANDS = (
    "Apple", "Samsung", "Xiaomi", "Redmi", "Poco", "Huawei", "Honor", "Oppo", "Realme",
    "Vivo", "OnePlus", "Google", "Asus", "Acer", "Lenovo", "HP", "Dell", "MSI", "Monster",
    "Casper", "Huawei", "Sony", "LG", "Philips", "TCL", "Vestel", "Arçelik", "Beko", "Bosch",
    "Siemens", "Dyson", "JBL", "Anker", "Logitech", "Razer", "Corsair", "Kingston", "Sandisk",
    "Seagate", "WD", "Western Digital", "Intel", "AMD", "Nvidia", "Canon", "Nikon", "GoPro",
)

CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Telefon", ("iphone", "galaxy s", "galaxy a", "telefon", "smartphone", "redmi note", "poco ", "pixel ")),
    ("Laptop", ("laptop", "notebook", "macbook", "thinkpad", "vivobook", "ideapad", "victus", "tuf gaming")),
    ("Tablet", ("tablet", "ipad", "galaxy tab", "matepad")),
    ("Televizyon", ("televizyon", "smart tv", "oled tv", "qled tv", "mini led tv")),
    ("Monitör", ("monitör", "monitor", "gaming monitor", "oyuncu monitörü")),
    ("Kulaklık", ("kulaklık", "earbuds", "headset", "airpods")),
    ("Akıllı Saat", ("akıllı saat", "smartwatch", "watch series", "galaxy watch")),
    ("Ekran Kartı", ("rtx ", "radeon rx", "ekran kartı", "graphics card")),
    ("İşlemci", ("işlemci", "processor", "ryzen ", "core i3", "core i5", "core i7", "core i9")),
    ("SSD", ("ssd", "nvme", "solid state")),
    ("Beyaz Eşya", ("çamaşır makinesi", "buzdolabı", "bulaşık makinesi", "kurutma makinesi")),
    ("Küçük Ev Aletleri", ("airfryer", "robot süpürge", "kahve makinesi", "blender", "ütü", "süpürge")),
    ("Fotoğraf Makinesi", ("fotoğraf makinesi", "mirrorless", "dslr", "aksiyon kamerası")),
)

MODEL_PATTERNS = (
    r"\b(?:iphone\s+\d{1,2}(?:\s+(?:pro|max|plus|mini)){0,2})\b",
    r"\b(?:galaxy\s+(?:s|a|m|z|note|tab)\s?\d{1,3}(?:\s+(?:ultra|plus|fe))?)\b",
    r"\b(?:redmi\s+note\s+\d{1,2}(?:\s+pro\+?)?)\b",
    r"\b(?:poco\s+[xfm]\d{1,2}(?:\s+pro)?)\b",
    r"\b(?:rtx\s*\d{4}(?:\s*(?:ti|super))?)\b",
    r"\b(?:rx\s*\d{4}(?:\s*xt)?)\b",
    r"\b(?:ryzen\s+[3579]\s+\d{4,5}[a-z]{0,3})\b",
    r"\b(?:core\s+i[3579][\s-]*\d{4,5}[a-z]{0,3})\b",
    r"\b[A-Z]{1,5}[- ]?\d{2,6}[A-Z0-9-]*\b",
)


@dataclass(slots=True)
class ProductFixSuggestion:
    product_id: int
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    normalized_name: str | None = None

    def changes(self) -> dict[str, str]:
        return {key: value for key, value in asdict(self).items() if key != "product_id" and value}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()


def normalize_product_name(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value or "")).strip(" -|,")
    value = re.sub(r"\s+([,.;:])", r"\1", value)
    return value


def infer_brand(name: str) -> str | None:
    folded = _fold(name)
    for brand in KNOWN_BRANDS:
        if re.search(rf"(?<![a-z0-9]){re.escape(_fold(brand))}(?![a-z0-9])", folded):
            return brand
    return None


def infer_category(name: str) -> str | None:
    folded = _fold(name)
    for category, keywords in CATEGORY_RULES:
        if any(_fold(keyword) in folded for keyword in keywords):
            return category
    return None


def infer_model(name: str, brand: str | None = None) -> str | None:
    compact = normalize_product_name(name)
    for pattern in MODEL_PATTERNS:
        match = re.search(pattern, compact, flags=re.IGNORECASE)
        if match:
            model = normalize_product_name(match.group(0))
            if brand and _fold(model).startswith(_fold(brand)):
                model = normalize_product_name(model[len(brand):])
            return model
    return None


def suggest_product_fix(product: ProductDB) -> ProductFixSuggestion:
    clean_name = normalize_product_name(product.name)
    brand = None if str(product.brand or "").strip() else infer_brand(clean_name)
    effective_brand = str(product.brand or "").strip() or brand
    model = None if str(product.model or "").strip() else infer_model(clean_name, effective_brand)
    category = None if str(product.category or "").strip() else infer_category(clean_name)
    normalized_name = clean_name if clean_name and clean_name != product.name else None
    return ProductFixSuggestion(
        product_id=int(product.id),
        brand=brand,
        model=model,
        category=category,
        normalized_name=normalized_name,
    )


def apply_safe_fixes(
    db: Session,
    *,
    product_ids: Iterable[int] | None = None,
    issue: str | None = None,
    actor: str = "admin",
) -> dict[str, int]:
    query = db.query(ProductDB)
    if hasattr(ProductDB, "is_deleted"):
        query = query.filter((ProductDB.is_deleted.is_(False)) | (ProductDB.is_deleted.is_(None)))
    ids = [int(value) for value in (product_ids or []) if str(value).strip().isdigit()]
    if ids:
        query = query.filter(ProductDB.id.in_(ids))
    products = query.all()

    scanned = 0
    updated = 0
    fields_changed = 0
    for product in products:
        scanned += 1
        suggestion = suggest_product_fix(product)
        changes = suggestion.changes()
        if issue == "missing_brand":
            changes = {key: value for key, value in changes.items() if key in {"brand", "model"}}
        elif issue == "missing_category":
            changes = {key: value for key, value in changes.items() if key == "category"}
        elif issue == "missing_model":
            changes = {key: value for key, value in changes.items() if key == "model"}
        elif issue == "name":
            changes = {key: value for key, value in changes.items() if key == "normalized_name"}

        applied: dict[str, str] = {}
        for key, value in changes.items():
            target = "name" if key == "normalized_name" else key
            current = str(getattr(product, target, "") or "").strip()
            if target == "name" or not current:
                if value and current != value:
                    setattr(product, target, value)
                    applied[target] = value
        if applied:
            updated += 1
            fields_changed += len(applied)
            record_admin_action(
                db,
                action="data_quality_safe_fix",
                entity_type="product",
                entity_id=product.id,
                details={"changes": applied},
                actor=actor,
            )
    db.commit()
    return {"scanned": scanned, "updated": updated, "fields_changed": fields_changed}
