from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTE = ROOT / "app/web/product_group_routes.py"
TEMPLATE = ROOT / "app/templates/product_group_detail_v4.html"


def patch_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Marker bulunamadı: {label}")
    return text.replace(old, new, 1)


def main() -> int:
    route = ROUTE.read_text(encoding="utf-8-sig")
    route = patch_once(
        route,
        "from app.services.price_analysis_service import build_price_analysis\n",
        "from app.services.price_analysis_service import build_price_analysis\nfrom app.services.deal_intelligence_v13_service import build_deal_intelligence_v13\n",
        "route import",
    )
    route = patch_once(
        route,
        "        feature_sections = get_grouped_product_features(\n",
        "        deal_intelligence_v13 = build_deal_intelligence_v13(\n            price_analysis=price_analysis,\n            ai_analysis=ai_analysis,\n            comparison=comparison,\n        )\n\n        feature_sections = get_grouped_product_features(\n",
        "service call",
    )
    route = patch_once(
        route,
        '    "price_analysis": price_analysis,\n',
        '    "price_analysis": price_analysis,\n    "deal_intelligence_v13": deal_intelligence_v13,\n',
        "template context",
    )
    ROUTE.write_text(route, encoding="utf-8")

    template = TEMPLATE.read_text(encoding="utf-8-sig")
    css_marker = ".product-insight-strip{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:18px 0}\n"
    css = css_marker + """.v13-deal-engine{margin:20px 0;padding:22px;border:1px solid #dfe7f2;border-radius:22px;background:linear-gradient(135deg,#ffffff 0%,#f6f8ff 100%);box-shadow:0 14px 34px rgba(30,41,59,.06)}
.v13-deal-head{display:flex;align-items:center;justify-content:space-between;gap:18px}.v13-deal-title span{display:block;color:#6366f1;font-size:.63rem;font-weight:950;text-transform:uppercase;letter-spacing:.08em}.v13-deal-title h2{margin:5px 0 0;color:#172033;font-size:1.2rem}.v13-score{display:grid;place-items:center;width:90px;height:90px;border-radius:50%;background:#111827;color:#fff}.v13-score strong{font-size:1.55rem}.v13-score small{font-size:.58rem;opacity:.75}.v13-deal-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:16px;margin-top:18px}.v13-verdict,.v13-metrics{padding:17px;border:1px solid #e3e9f3;border-radius:16px;background:#fff}.v13-action{color:#111827;font-weight:950;font-size:1rem}.v13-verdict p{margin:7px 0 0;color:#475569;font-size:.76rem;line-height:1.65}.v13-reasons{display:grid;gap:7px;margin:14px 0 0;padding:0;list-style:none}.v13-reasons li{color:#334155;font-size:.7rem}.v13-reasons li:before{content:'✓';margin-right:7px;color:#16a34a;font-weight:950}.v13-metric{display:flex;align-items:center;justify-content:space-between;padding:9px 0;border-bottom:1px solid #eef2f7;font-size:.72rem}.v13-metric:last-child{border:0}.v13-badges{display:flex;flex-wrap:wrap;gap:7px;margin-top:14px}.v13-badge{padding:7px 10px;border-radius:999px;background:#eef2ff;color:#3730a3;font-size:.63rem;font-weight:850}@media(max-width:760px){.v13-deal-head{align-items:flex-start}.v13-score{width:74px;height:74px}.v13-deal-grid{grid-template-columns:1fr}}
"""
    if ".v13-deal-engine{" not in template:
        if css_marker not in template:
            raise RuntimeError("Marker bulunamadı: template CSS")
        template = template.replace(css_marker, css, 1)

    html_marker = '    <section class="product-insight-strip">\n'
    html = """    {% if deal_intelligence_v13 %}
    <section id="ai-analysis" class="v13-deal-engine">
        <div class="v13-deal-head">
            <div class="v13-deal-title">
                <span>FırsatAI Karar Motoru v13</span>
                <h2>Açıklanabilir fırsat analizi</h2>
            </div>
            <div class="v13-score">
                <strong>{{ deal_intelligence_v13.score }}</strong>
                <small>/ 100</small>
            </div>
        </div>
        <div class="v13-deal-grid">
            <article class="v13-verdict">
                <div class="v13-action">{{ deal_intelligence_v13.action }}</div>
                <p>{{ deal_intelligence_v13.verdict }}</p>
                <ul class="v13-reasons">
                    {% for reason in deal_intelligence_v13.reasons %}<li>{{ reason }}</li>{% endfor %}
                </ul>
            </article>
            <article class="v13-metrics">
                <div class="v13-metric"><span>Fırsat seviyesi</span><strong>{{ deal_intelligence_v13.score_label }}</strong></div>
                <div class="v13-metric"><span>Fiyat eğilimi</span><strong>{{ deal_intelligence_v13.trend.icon }} {{ deal_intelligence_v13.trend.label }}</strong></div>
                <div class="v13-metric"><span>Analiz güveni</span><strong>{{ deal_intelligence_v13.confidence }}</strong></div>
                <div class="v13-metric"><span>Veri kapsamı</span><strong>{{ deal_intelligence_v13.record_count }} kayıt / {{ deal_intelligence_v13.offer_count }} teklif</strong></div>
            </article>
        </div>
        {% if deal_intelligence_v13.badges %}<div class="v13-badges">{% for badge in deal_intelligence_v13.badges %}<span class="v13-badge">{{ badge.icon }} {{ badge.label }}</span>{% endfor %}</div>{% endif %}
    </section>
    {% endif %}

""" + html_marker
    if 'id="ai-analysis" class="v13-deal-engine"' not in template:
        if html_marker not in template:
            raise RuntimeError("Marker bulunamadı: template HTML")
        template = template.replace(html_marker, html, 1)
    TEMPLATE.write_text(template, encoding="utf-8")
    print("OK  v13 fırsat motoru route ve ürün detay sayfasına bağlandı")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
