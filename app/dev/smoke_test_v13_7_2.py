from pathlib import Path
import json
import os
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.services.image_optimization_v13 import (
    ENGINE_VERSION,
    DEFAULT_PLACEHOLDER,
    build_srcset,
    choose_format,
    image_attributes,
    optimized_image_url,
)


def ok(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main():
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    ok(version == "13.7.2", "VERSION 13.7.2")
    ok(ENGINE_VERSION == "13.7.2", "görsel optimizasyon motoru sürümü doğru")
    ok(choose_format("image/avif,image/webp") == "avif", "AVIF destek algılama doğru")
    ok(choose_format("image/webp") == "webp", "WebP destek algılama doğru")
    attrs = image_attributes("https://example.com/a.jpg", hero=False)
    ok(attrs["loading"] == "lazy", "lazy loading uygulanıyor")
    ok(attrs["decoding"] == "async", "async decoding uygulanıyor")
    ok(attrs["width"] > 0 and attrs["height"] > 0, "width/height CLS koruması mevcut")
    hero = image_attributes("https://example.com/a.jpg", hero=True)
    ok(hero["fetchpriority"] == "high" and hero["loading"] == "eager", "hero görseli fetchpriority high kullanıyor")
    ok(DEFAULT_PLACEHOLDER.endswith(".svg"), "güvenli placeholder mevcut")
    os.environ.pop("FIRSATAI_IMAGE_CDN_TEMPLATE", None)
    ok(optimized_image_url("https://example.com/a.jpg", width=480, format_name="webp") == "https://example.com/a.jpg", "CDN yokken orijinal görsel korunuyor")
    ok(build_srcset("https://example.com/a.jpg") == "", "olmayan responsive görseller uydurulmuyor")
    os.environ["FIRSATAI_IMAGE_CDN_TEMPLATE"] = "https://img.example/{width}/{format}?url={url}"
    srcset = build_srcset("https://example.com/a.jpg", format_name="webp")
    ok("240w" in srcset and "960w" in srcset, "responsive srcset CDN yapılandırmasıyla üretiliyor")
    js = (ROOT / "app/static/js/image-optimization-v13.js").read_text(encoding="utf-8")
    ok('loading' in js and 'fetchpriority' in js and 'MutationObserver' in js, "global görsel iyileştirici mevcut")
    base = (ROOT / "app/templates/public_base.html").read_text(encoding="utf-8")
    ok("image-optimization-v13.css" in base and "image-optimization-v13.js" in base, "görsel optimizasyon kaynakları arayüze bağlı")
    main_py = (ROOT / "main.py").read_text(encoding="utf-8")
    ok("image_optimization_router" in main_py, "görsel optimizasyon API router uygulamaya bağlı")
    print("\\nFırsatAI v13.7.2 Görsel Optimizasyonu smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
