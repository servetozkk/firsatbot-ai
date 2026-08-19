from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Iterable
from urllib.parse import urljoin

SCHEMA_VERSION = "13.6.1"


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(Decimal(str(value)))
    except (ValueError, TypeError, ArithmeticError):
        return None
    return round(number, 2) if number >= 0 else None


def _absolute(base_url: Any, value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    if text.startswith(("http://", "https://")):
        return text
    return urljoin(str(base_url), text.lstrip("/"))


def _availability(offer: dict[str, Any]) -> str:
    if offer.get("is_available") is False:
        return "https://schema.org/OutOfStock"
    status = _text(offer.get("stock_status") or offer.get("availability")).lower()
    if any(token in status for token in ("tükendi", "stok yok", "out_of_stock", "outofstock")):
        return "https://schema.org/OutOfStock"
    if any(token in status for token in ("az kaldı", "low_stock", "limited")):
        return "https://schema.org/LimitedAvailability"
    return "https://schema.org/InStock"


def website_schema(base_url: Any) -> dict[str, Any]:
    root = str(base_url).rstrip("/") + "/"
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": root + "#website",
        "url": root,
        "name": "Fırsat AI",
        "description": "Ürün fiyatlarını, mağaza tekliflerini ve fiyat geçmişini karşılaştırma platformu.",
        "inLanguage": "tr-TR",
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": root + "arama?q={search_term_string}",
            },
            "query-input": "required name=search_term_string",
        },
    }


def breadcrumb_schema(base_url: Any, items: Iterable[tuple[str, str]]) -> dict[str, Any]:
    elements = []
    for position, (name, path) in enumerate(items, start=1):
        label = _text(name)
        url = _absolute(base_url, path)
        if not label or not url:
            continue
        elements.append({
            "@type": "ListItem",
            "position": position,
            "name": label,
            "item": url,
        })
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": elements,
    }


def _offer_schema(base_url: Any, offer: dict[str, Any], currency: str = "TRY") -> dict[str, Any] | None:
    price = _number(offer.get("total_price") or offer.get("price"))
    if price is None or price <= 0:
        return None
    url = _absolute(base_url, offer.get("url") or offer.get("product_url") or offer.get("offer_url"))
    item: dict[str, Any] = {
        "@type": "Offer",
        "priceCurrency": currency,
        "price": f"{price:.2f}",
        "availability": _availability(offer),
    }
    if url:
        item["url"] = url
    seller = _text(offer.get("store") or offer.get("store_name") or offer.get("seller"))
    if seller:
        item["seller"] = {"@type": "Organization", "name": seller}
    condition = _text(offer.get("item_condition")).lower()
    item["itemCondition"] = (
        "https://schema.org/UsedCondition" if "used" in condition or "ikinci" in condition
        else "https://schema.org/NewCondition"
    )
    return item


def product_schema(
    *,
    base_url: Any,
    canonical_url: str,
    group: Any,
    comparison: dict[str, Any],
    available_offers: list[dict[str, Any]],
    image_urls: Iterable[Any] = (),
    description: str = "",
) -> dict[str, Any]:
    name = _text(getattr(group, "canonical_name", None) or comparison.get("product_name"))
    brand = _text(getattr(group, "brand", None) or comparison.get("brand"))
    category = _text(getattr(group, "category", None) or comparison.get("category"))
    identity = _text(getattr(group, "group_key", None) or comparison.get("identity_key"))
    images = []
    for value in image_urls:
        url = _absolute(base_url, value)
        if url and url not in images:
            images.append(url)

    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Product",
        "@id": canonical_url + "#product",
        "url": canonical_url,
        "name": name,
        "description": _text(description) or f"{name} fiyatları ve mağaza teklifleri.",
        "sku": identity,
    }
    if images:
        data["image"] = images
    if brand:
        data["brand"] = {"@type": "Brand", "name": brand}
    if category:
        data["category"] = category

    valid_offers = [item for offer in available_offers if (item := _offer_schema(base_url, offer))]
    if len(valid_offers) == 1:
        data["offers"] = valid_offers[0]
    elif valid_offers:
        prices = [float(item["price"]) for item in valid_offers]
        data["offers"] = {
            "@type": "AggregateOffer",
            "priceCurrency": "TRY",
            "lowPrice": f"{min(prices):.2f}",
            "highPrice": f"{max(prices):.2f}",
            "offerCount": len(valid_offers),
            "availability": "https://schema.org/InStock",
            "offers": valid_offers,
            "url": canonical_url,
        }
    return data


def dumps(data: dict[str, Any] | list[Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
