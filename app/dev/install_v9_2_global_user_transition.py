from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()


def main() -> int:
    route_path = ROOT / "app/web/product_group_routes.py"
    text = route_path.read_text(encoding="utf-8")

    if "    GlobalProduct,\n" not in text:
        text = text.replace(
            "    RecentlyViewed,\n",
            "    RecentlyViewed,\n    GlobalProduct,\n",
            1,
        )

    import_anchor = (
        "from app.services.comparison_service import (\n"
        "    get_product_comparison,\n"
        ")\n"
    )
    import_value = (
        "from app.services.global_comparison_service import "
        "get_global_product_comparison\n"
    )
    if import_value not in text:
        if import_anchor not in text:
            raise RuntimeError("Karşılaştırma servis import noktası bulunamadı.")
        text = text.replace(import_anchor, import_anchor + import_value, 1)

    old_group_check = '''        if group is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Ürün grubu bulunamadı."
                ),
            )
'''
    new_group_check = '''        global_product = (
            db.query(GlobalProduct)
            .filter(GlobalProduct.identity_key == identity_key)
            .first()
        )

        if group is None and global_product is not None:
            group = (
                db.query(ProductGroup)
                .filter(
                    ProductGroup.group_key
                    == global_product.identity_key
                )
                .first()
            )

        if group is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Ürün grubu bulunamadı."
                ),
            )
'''
    detail_start = text.find("def product_group_detail(")
    if detail_start < 0:
        raise RuntimeError("Ürün detay fonksiyonu bulunamadı.")
    prefix = text[:detail_start]
    detail = text[detail_start:]

    if "global_product = (" not in detail:
        if old_group_check not in detail:
            raise RuntimeError("Ürün grubu kontrol bloğu bulunamadı.")
        detail = detail.replace(old_group_check, new_group_check, 1)

    old_comparison = '''        comparison = (
            get_product_comparison(
                db=db,
                identity_key=identity_key,
            )
        )

        if comparison is None:
'''
    new_comparison = '''        legacy_comparison = (
            get_product_comparison(
                db=db,
                identity_key=group.group_key,
            )
        )
        global_comparison = get_global_product_comparison(
            db=db,
            identity_key=group.group_key,
        )
        comparison = global_comparison or legacy_comparison

        if comparison is None:
'''
    if "global_comparison = get_global_product_comparison(" not in detail:
        if old_comparison not in detail:
            raise RuntimeError("Karşılaştırma veri bloğu bulunamadı.")
        detail = detail.replace(old_comparison, new_comparison, 1)

    # Yardımcı servislerin eski ProductGroup anahtarıyla güvenli çalışması.
    detail = detail.replace(
        "identity_key=identity_key,",
        "identity_key=group.group_key,",
    )

    context_anchor = '    "current_user": user,\n'
    context_value = (
        '    "comparison_data_source": '
        'comparison.get("data_source", "legacy"),\n'
    )
    if '"comparison_data_source":' not in detail:
        if context_anchor not in detail:
            raise RuntimeError("Şablon context noktası bulunamadı.")
        detail = detail.replace(
            context_anchor,
            context_anchor + context_value,
            1,
        )

    route_path.write_text(prefix + detail, encoding="utf-8")

    template_path = ROOT / "app/templates/product_group_detail_v4.html"
    tpl = template_path.read_text(encoding="utf-8")
    if "v9-global-data-badge" not in tpl:
        marker = '<div class="detail-page">'
        badge = (
            '<div class="detail-page">\n'
            '{% if comparison_data_source == "global_catalog_v9" %}\n'
            '<div class="v9-global-data-badge">'
            'V9 Global Katalog - {{ comparison.store_count }} mağaza teklifi'
            '</div>\n'
            '{% endif %}'
        )
        if marker not in tpl:
            raise RuntimeError("Ürün detay ana alanı bulunamadı.")
        tpl = tpl.replace(marker, badge, 1)
        style = (
            ".v9-global-data-badge{display:inline-flex;margin:0 0 10px;"
            "padding:6px 9px;border-radius:999px;background:#ede9fe;"
            "color:#6d28d9;font-size:.57rem;font-weight:900}\n"
        )
        tpl = tpl.replace("</style>", style + "</style>", 1)
    template_path.write_text(tpl, encoding="utf-8")

    print("V9.2 global teklif kullanıcı geçişi entegre edildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
