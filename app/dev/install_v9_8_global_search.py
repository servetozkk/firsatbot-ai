from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()


def patch_route() -> None:
    path = ROOT / "app/web/routes.py"
    text = path.read_text(encoding="utf-8")

    import_line = (
        "from app.services.global_catalog_search_service import "
        "build_global_search_candidates\n"
    )
    anchor = (
        "from app.services.catalog_search_service import (\n"
        "    calculate_relevance,\n"
        "    parse_capacity_gb,\n"
        "    parse_identity_attributes,\n"
        ")\n"
    )
    if import_line not in text:
        if anchor not in text:
            raise RuntimeError("Arama servis import bloğu bulunamadı.")
        text = text.replace(anchor, anchor + import_line, 1)

    start_marker = (
        "        groups = db.query(ProductGroup)"
        ".order_by(ProductGroup.updated_at.desc()).all()\n"
    )
    end_marker = (
        "        # Facet counts are generated before their own filters "
        "so users can widen choices.\n"
    )

    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError("Eski arama aday üretim bloğu bulunamadı.")

    replacement = (
        "        candidates = build_global_search_candidates(\n"
        "            db=db,\n"
        "            query=query,\n"
        "        )\n\n"
    )
    text = text[:start] + replacement + text[end:]

    # Mağaza filtresinde fiyat artık kargo dahil toplam fiyat olmalı.
    text = text.replace(
        'matching_offers.sort(key=lambda offer: offer["price"])',
        'matching_offers.sort(key=lambda offer: offer.get("total_price", offer["price"]))',
        1,
    )
    text = text.replace(
        'item["price"] = matching_offers[0]["price"]',
        'item["price"] = matching_offers[0].get("total_price", matching_offers[0]["price"])',
        1,
    )

    path.write_text(text, encoding="utf-8")


def patch_template() -> None:
    path = ROOT / "app/templates/search_results.html"
    text = path.read_text(encoding="utf-8")

    old = (
        '<div class="active-summary">{{ total_results }} ürün grubu bulundu'
    )
    new = (
        '<div class="active-summary">{{ total_results }} global ürün bulundu'
    )
    text = text.replace(old, new, 1)

    old_info = (
        '<div class="offer-info">{{ product.offer_count }} mağaza'
        '{% if product.best_store %} · En ucuz: {{ product.best_store }}'
        '{% endif %}</div>'
    )
    new_info = (
        '<div class="offer-info">{{ product.offer_count }} mağaza'
        '{% if product.best_store %} · En ucuz: {{ product.best_store }}'
        '{% endif %}</div>'
        '{% if product.data_source == "global_catalog_v9" %}'
        '<div class="product-badges">'
        '<span class="product-badge global">V9 Global Katalog</span>'
        '{% if product.variant_count > 1 %}'
        '<span class="product-badge">{{ product.variant_count }} varyant</span>'
        '{% endif %}'
        '</div>'
        '{% endif %}'
    )
    if "V9 Global Katalog" not in text:
        if old_info not in text:
            raise RuntimeError("Arama kartı teklif bilgisi bulunamadı.")
        text = text.replace(old_info, new_info, 1)

    if ".product-badge.global{" not in text:
        text = text.replace(
            ".product-badge.success{background:#dcfce7;color:#15803d}",
            ".product-badge.success{background:#dcfce7;color:#15803d}"
            ".product-badge.global{background:#ede9fe;color:#6d28d9}",
            1,
        )

    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_route()
    patch_template()
    print("V9.8 global arama ve filtre motoru entegre edildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
