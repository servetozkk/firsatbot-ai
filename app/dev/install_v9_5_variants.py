from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()


def main() -> int:
    route = ROOT / "app/web/product_group_routes.py"
    text = route.read_text(encoding="utf-8")
    old = """def product_group_detail(
    request: Request,
    identity_key: str,
    firsat_session: str | None = Cookie(default=None),
):"""
    new = """def product_group_detail(
    request: Request,
    identity_key: str,
    variant: int | None = None,
    firsat_session: str | None = Cookie(default=None),
):"""
    if "variant: int | None = None" not in text:
        if old not in text:
            raise RuntimeError("Ürün detay imzası bulunamadı.")
        text = text.replace(old, new, 1)

    old_call = """        global_comparison = get_global_product_comparison(
            db=db,
            identity_key=group.group_key,
        )"""
    new_call = """        global_comparison = get_global_product_comparison(
            db=db,
            identity_key=group.group_key,
            selected_variant_id=variant,
        )"""
    if "selected_variant_id=variant" not in text:
        if old_call not in text:
            raise RuntimeError("Global comparison çağrısı bulunamadı.")
        text = text.replace(old_call, new_call, 1)
    route.write_text(text, encoding="utf-8")

    template = ROOT / "app/templates/product_group_detail_v4.html"
    tpl = template.read_text(encoding="utf-8")
    if "v9-variant-selector" not in tpl:
        marker = '                <div class="product-trust-strip">'
        block = """                {% if comparison_data_source == "global_catalog_v9" and comparison.variants %}
                <section class="v9-variant-selector">
                    <div class="v9-variant-heading">
                        <span>Varyant seçenekleri</span>
                        {% if comparison.selected_variant %}<strong>{{ comparison.selected_variant.label }}</strong>{% endif %}
                    </div>
                    <div class="v9-variant-list">
                    {% for item in comparison.variants %}
                        <a href="/urun/{{ comparison.identity_key }}?variant={{ item.id }}" class="v9-variant-chip{% if item.id == comparison.selected_variant_id %} active{% endif %}">
                            {% if item.image %}<img src="{{ item.image }}" alt="" loading="lazy" referrerpolicy="no-referrer">{% endif %}
                            <span>
                                <b>{{ item.label }}</b>
                                <small>{{ item.store_count }} mağaza{% if item.best_price is not none %} - {{ "{:,.0f}".format(item.best_price).replace(",", ".") }} TL'den{% endif %}</small>
                            </span>
                        </a>
                    {% endfor %}
                    </div>
                </section>
                {% endif %}

"""
        if marker not in tpl:
            raise RuntimeError("Varyant şablon noktası bulunamadı.")
        tpl = tpl.replace(marker, block + marker, 1)
        css = """.v9-variant-selector{margin:14px 0;padding:13px;border:1px solid #dfe7f2;border-radius:14px;background:rgba(255,255,255,.82)}
.v9-variant-heading{display:flex;justify-content:space-between;gap:12px;margin-bottom:9px}.v9-variant-heading span{color:#64748b;font-size:.57rem;font-weight:900;text-transform:uppercase}.v9-variant-heading strong{font-size:.68rem}.v9-variant-list{display:flex;gap:7px;overflow-x:auto}.v9-variant-chip{display:flex;align-items:center;gap:8px;flex:0 0 auto;min-width:150px;padding:8px;border:1px solid #dce4ef;border-radius:11px;background:#fff;color:#334155;text-decoration:none}.v9-variant-chip.active{border:2px solid #4f46e5;background:#f5f3ff}.v9-variant-chip img{width:34px;height:34px;object-fit:contain}.v9-variant-chip b,.v9-variant-chip small{display:block}.v9-variant-chip b{font-size:.59rem}.v9-variant-chip small{margin-top:3px;color:#64748b;font-size:.48rem}
"""
        tpl = tpl.replace("</style>", css + "</style>", 1)
    template.write_text(tpl, encoding="utf-8")
    print("V9.5 global varyant sistemi entegre edildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
