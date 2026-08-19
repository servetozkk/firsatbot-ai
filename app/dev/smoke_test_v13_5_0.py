from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)
def main():
    ok((ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()=='13.5.0','VERSION 13.5.0')
    s=(ROOT/'app/services/campaign_center_service.py').read_text(encoding='utf-8')
    r=(ROOT/'app/web/campaign_center_routes.py').read_text(encoding='utf-8')
    t=(ROOT/'app/templates/campaign_center.html').read_text(encoding='utf-8')
    main=(ROOT/'main.py').read_text(encoding='utf-8')
    ok('price_drop' in s and 'free_shipping' in s and 'installment' in s,'kampanya sınıfları mevcut')
    ok('/kampanyalar' in r and '/api/campaign-center/v13' in r,'kampanya merkezi route ve API mevcut')
    ok('campaign_center_router' in main,'kampanya router uygulamaya bağlı')
    ok('Fiyatı düşenler' in t and 'Ücretsiz kargo' in t,'kampanya filtreleri arayüzde mevcut')
    ok('Fiyatları karşılaştır' in t,'kampanya kartları ürün karşılaştırmaya bağlı')
    print('\nFırsatAI v13.5.0 Kampanya Merkezi smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
