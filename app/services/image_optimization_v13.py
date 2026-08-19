from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote


ENGINE_VERSION = "13.7.2"
DEFAULT_PLACEHOLDER = "/static/img/product-placeholder-v1372.svg"
DEFAULT_WIDTHS = (240, 360, 480, 720, 960)


@dataclass(frozen=True)
class ImageOptimizationConfig:
    engine_version: str = ENGINE_VERSION
    placeholder_url: str = DEFAULT_PLACEHOLDER
    lazy_loading: bool = True
    async_decoding: bool = True
    supported_formats: tuple[str, ...] = ("avif", "webp", "original")
    responsive_widths: tuple[int, ...] = DEFAULT_WIDTHS
    cdn_template_configured: bool = False


def get_config() -> ImageOptimizationConfig:
    return ImageOptimizationConfig(
        cdn_template_configured=bool(os.getenv("FIRSATAI_IMAGE_CDN_TEMPLATE", "").strip())
    )


def choose_format(accept_header: str | None) -> str:
    accept = (accept_header or "").lower()
    if "image/avif" in accept:
        return "avif"
    if "image/webp" in accept:
        return "webp"
    return "original"


def optimized_image_url(source_url: str | None, *, width: int | None = None, format_name: str = "original") -> str:
    """Return a CDN URL only when an explicit template is configured.

    Template placeholders: {url}, {width}, {format}. Without a configured
    CDN the original URL is preserved; the application never invents a
    converted asset that does not exist.
    """
    source = (source_url or "").strip()
    if not source:
        return DEFAULT_PLACEHOLDER
    template = os.getenv("FIRSATAI_IMAGE_CDN_TEMPLATE", "").strip()
    if not template:
        return source
    safe_format = format_name if format_name in {"avif", "webp", "original"} else "original"
    safe_width = max(1, min(int(width or 720), 2400))
    return template.format(url=quote(source, safe=""), width=safe_width, format=safe_format)


def build_srcset(source_url: str | None, *, format_name: str = "original") -> str:
    if not source_url or not os.getenv("FIRSATAI_IMAGE_CDN_TEMPLATE", "").strip():
        return ""
    return ", ".join(
        f"{optimized_image_url(source_url, width=width, format_name=format_name)} {width}w"
        for width in DEFAULT_WIDTHS
    )


def image_attributes(source_url: str | None, *, hero: bool = False, width: int = 320, height: int = 240) -> dict[str, str | int]:
    source = (source_url or "").strip() or DEFAULT_PLACEHOLDER
    return {
        "src": source,
        "loading": "eager" if hero else "lazy",
        "decoding": "async",
        "fetchpriority": "high" if hero else "auto",
        "width": max(1, int(width)),
        "height": max(1, int(height)),
        "referrerpolicy": "no-referrer",
        "onerror": f"this.onerror=null;this.src='{DEFAULT_PLACEHOLDER}'",
    }
