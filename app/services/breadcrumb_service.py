from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence
from urllib.parse import urlsplit

ENGINE_VERSION = "13.6.3"

@dataclass(frozen=True)
class BreadcrumbItem:
    label: str
    url: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {"label": self.label, "url": self.url}


def normalize_breadcrumbs(items: Iterable[object] | None) -> list[dict[str, str | None]]:
    """Normalize tuple/dict/dataclass breadcrumb inputs and remove duplicates safely."""
    result: list[dict[str, str | None]] = []
    seen: set[tuple[str, str | None]] = set()
    for raw in items or []:
        label: str | None = None
        url: str | None = None
        if isinstance(raw, BreadcrumbItem):
            label, url = raw.label, raw.url
        elif isinstance(raw, Mapping):
            label = str(raw.get("label") or raw.get("name") or "").strip()
            value = raw.get("url")
            url = str(value).strip() if value else None
        elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) and raw:
            label = str(raw[0]).strip()
            if len(raw) > 1 and raw[1]:
                url = str(raw[1]).strip()
        if not label:
            continue
        key = (label, url)
        if key in seen:
            continue
        seen.add(key)
        result.append({"label": label, "url": url})
    if not result or result[0]["url"] != "/":
        result.insert(0, {"label": "Ana Sayfa", "url": "/"})
    if result:
        result[-1]["url"] = None
    return result


def page_breadcrumbs(*items: object) -> list[dict[str, str | None]]:
    return normalize_breadcrumbs(items)


def category_breadcrumb(category: str, category_url: str | None = None) -> list[dict[str, str | None]]:
    return page_breadcrumbs(("Kategoriler", "/kategoriler"), (category, category_url))


def brand_breadcrumb(brand: str, brand_url: str | None = None) -> list[dict[str, str | None]]:
    return page_breadcrumbs(("Markalar", "/markalar"), (brand, brand_url))


def store_breadcrumb(store: str, store_url: str | None = None) -> list[dict[str, str | None]]:
    return page_breadcrumbs(("Mağazalar", "/magazalar"), (store, store_url))


def product_breadcrumb(
    product_name: str,
    *,
    category: str | None = None,
    category_url: str | None = None,
    brand: str | None = None,
    brand_url: str | None = None,
) -> list[dict[str, str | None]]:
    items: list[object] = []
    if category:
        items.extend([("Kategoriler", "/kategoriler"), (category, category_url)])
    if brand:
        items.extend([("Markalar", "/markalar"), (brand, brand_url)])
    items.append((product_name, None))
    return page_breadcrumbs(*items)


def absolute_breadcrumbs(base_url: str, items: Iterable[object] | None) -> list[tuple[str, str]]:
    base = base_url.rstrip("/")
    output: list[tuple[str, str]] = []
    for item in normalize_breadcrumbs(items):
        url = item["url"] or ""
        if url.startswith("http://") or url.startswith("https://"):
            absolute = url
        elif url:
            absolute = base + (url if url.startswith("/") else "/" + url)
        else:
            absolute = base + (urlsplit(base).path or "")
        output.append((str(item["label"]), absolute))
    return output
