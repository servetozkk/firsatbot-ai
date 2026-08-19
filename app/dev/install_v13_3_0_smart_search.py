from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def patch(path, old, new, label):
    text=path.read_text(encoding='utf-8')
    if new in text:
        print('OK ',label,'zaten uygulanmış'); return
    if old not in text:
        raise RuntimeError(f'Marker bulunamadı: {label}')
    path.write_text(text.replace(old,new,1),encoding='utf-8')
    print('OK ',label)

def main():
    main=ROOT/'main.py'
    text=main.read_text(encoding='utf-8')
    if 'smart_search_routes' not in text:
        import_marker='from app.web import '
        # bağımsız import; mevcut import düzenine bağlı değil
        insert='from app.web.smart_search_routes import router as smart_search_router\n'
        first_route=text.find('app.include_router(')
        if first_route<0: raise RuntimeError('main.py include_router marker bulunamadı')
        text=text[:first_route]+insert+text[first_route:]
        # ilk include_router öncesine yeni include ekle
        idx=text.find('app.include_router(')
        text=text[:idx]+'app.include_router(smart_search_router)\n'+text[idx:]
        main.write_text(text,encoding='utf-8')
        print('OK  smart search router main.py içine bağlandı')
    else: print('OK  smart search router zaten bağlı')

    routes=ROOT/'app/web/routes.py'
    patch(routes,
        'from app.web.account_routes import _current_user\n',
        'from app.web.account_routes import _current_user\nfrom app.services.smart_search_service import enrich_and_rank_candidates, parse_smart_query\n',
        'smart search servis importu')
    patch(routes,
        '    query = " ".join(str(params.get("q", "") or "").split())\n',
        '    query = " ".join(str(params.get("q", "") or "").split())\n    smart_query = parse_smart_query(query)\n',
        'sorgu parser bağlantısı')
    patch(routes,
        '        candidates = build_global_search_candidates(\n            db=db,\n            query=query,\n        )\n',
        '        candidates = build_global_search_candidates(\n            db=db,\n            query=smart_query.get("search_text") or query,\n        )\n        candidates = enrich_and_rank_candidates(candidates, smart_query)\n        if min_price is None and smart_query.get("price_min") is not None:\n            min_price = float(smart_query["price_min"])\n        if max_price is None and smart_query.get("price_max") is not None:\n            max_price = float(smart_query["price_max"])\n',
        'semantic filtre ve sıralama bağlantısı')
    patch(routes,
        '                "query": query,\n                "products": products,\n',
        '                "query": query,\n                "smart_query": smart_query,\n                "products": products,\n',
        'template semantic context')

    tpl=ROOT/'app/templates/search_results.html'
    patch(tpl,
        '.active-summary{margin-top:10px;font-size:.8rem;color:#dbeafe}\n',
        '.active-summary{margin-top:10px;font-size:.8rem;color:#dbeafe}.smart-query-panel{margin-top:14px;padding:12px 14px;border:1px solid rgba(255,255,255,.24);border-radius:14px;background:rgba(255,255,255,.10)}.smart-query-title{font-size:.72rem;font-weight:950;text-transform:uppercase;letter-spacing:.08em}.smart-query-chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:8px}.smart-query-chip{padding:5px 9px;border-radius:999px;background:rgba(255,255,255,.16);font-size:.72rem;font-weight:850}.search-reasons{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}.search-reason{padding:4px 7px;border-radius:999px;background:#ecfdf5;color:#047857;font-size:.62rem;font-weight:850}\n',
        'akıllı sorgu paneli stili')
    patch(tpl,
        '    <div class="active-summary">{{ total_results }} global ürün bulundu{% if query %} · “{{ query }}” araması{% endif %}</div>\n',
        '    <div class="active-summary">{{ total_results }} global ürün bulundu{% if query %} · “{{ query }}” araması{% endif %}</div>\n    {% if smart_query and (smart_query.extracted or smart_query.corrections) %}<div class="smart-query-panel"><div class="smart-query-title">FırsatAI sorguyu şöyle anladı</div><div class="smart-query-chips">{% for item in smart_query.extracted %}<span class="smart-query-chip">{{ item }}</span>{% endfor %}{% for item in smart_query.corrections %}<span class="smart-query-chip">Düzeltme: {{ item }}</span>{% endfor %}</div></div>{% endif %}\n',
        'akıllı sorgu özeti arayüzü')
    patch(tpl,
        '                <div class="offer-info">{{ product.offer_count }} mağaza{% if product.best_store %} · En ucuz: {{ product.best_store }}{% endif %}</div>',
        '                <div class="offer-info">{{ product.offer_count }} mağaza{% if product.best_store %} · En ucuz: {{ product.best_store }}{% endif %}</div>{% if product.search_reasons %}<div class="search-reasons">{% for reason in product.search_reasons[:3] %}<span class="search-reason">✓ {{ reason }}</span>{% endfor %}</div>{% endif %}',
        'açıklanabilir sonuç nedenleri')
    return 0
if __name__=='__main__': raise SystemExit(main())
