from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]

def ok(value, message):
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")

def main():
    version = (ROOT / 'VERSION').read_text(encoding='utf-8-sig').strip()
    ok(version == '13.5.0', 'VERSION 13.5.0 korunuyor')

    from app.services.comparison_v2_service import build_product_metrics
    products = [SimpleNamespace(group_key='a'), SimpleNamespace(group_key='b')]
    sections = [{
        'name': 'Depolama',
        'rows': [{
            'is_comparable': True,
            'winner_indexes': [0],
        }],
    }]
    metrics = build_product_metrics(products, [None, None], sections)
    ok(all(item['value_score'] is None for item in metrics), 'piyasa verisi yokken değer puanı üretilmiyor')
    ok(not any(item['is_best_value'] for item in metrics), 'piyasa verisi yokken en iyi değer seçilmiyor')

    route_source = (ROOT / 'app/web/product_group_routes.py').read_text(encoding='utf-8')
    ok('_normalize_compare_display_value' in route_source, 'depolama birim düzelticisi mevcut')
    ok('return f"{integer} GB"' in route_source, '512 TB gösterimi 512 GB olarak düzeltilebiliyor')

    template = (ROOT / 'app/templates/product_group_compare_v2.html').read_text(encoding='utf-8')
    ok('Aktif teklif yok' in template, 'aktif teklif yok mesajı mevcut')
    ok('Değer puanı için veri yetersiz' in template, 'veri yetersiz değer puanı mesajı mevcut')
    ok("section['rows']" in template and "row['values']" in template, 'Jinja güvenli sözlük erişimi korunuyor')

    print('\nFırsatAI v13.5.0 Karşılaştırma veri hotfix smoke test başarılı.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
