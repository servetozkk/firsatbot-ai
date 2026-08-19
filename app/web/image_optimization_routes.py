from fastapi import APIRouter, Request

from app.services.image_optimization_v13 import (
    ENGINE_VERSION,
    build_srcset,
    choose_format,
    get_config,
    image_attributes,
)

router = APIRouter(tags=["image-optimization"])


@router.get("/api/image-optimization/v13")
def image_optimization_status(request: Request, url: str | None = None, hero: bool = False):
    config = get_config()
    preferred_format = choose_format(request.headers.get("accept"))
    sample = image_attributes(url, hero=hero) if url else None
    return {
        "engine_version": ENGINE_VERSION,
        "status": "IMAGE_OPTIMIZATION_READY",
        "preferred_format": preferred_format,
        "lazy_loading": config.lazy_loading,
        "async_decoding": config.async_decoding,
        "placeholder_url": config.placeholder_url,
        "supported_formats": list(config.supported_formats),
        "responsive_widths": list(config.responsive_widths),
        "cdn_template_configured": config.cdn_template_configured,
        "sample_attributes": sample,
        "sample_srcset": build_srcset(url, format_name=preferred_format) if url else "",
        "read_only": True,
    }
