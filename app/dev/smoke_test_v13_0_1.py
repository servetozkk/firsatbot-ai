from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def ok(v: bool, m: str):
    if not v: raise AssertionError(m)
    print(f"OK  {m}")

def main() -> int:
    ok((ROOT/'VERSION').read_text(encoding='utf-8').strip()=='13.0.1','VERSION 13.0.1')
    p=ROOT/'data/reports/v13_0_1_deal_engine_real_data_acceptance.json'
    ok(p.exists(),'gerçek veri kabul raporu oluşturuldu')
    d=json.loads(p.read_text(encoding='utf-8'))
    ok(d.get('read_only') is True,'kabul testi salt okunur')
    ok(d.get('status')=='DEAL_ENGINE_REAL_DATA_ACCEPTANCE_READY','gerçek veri kabul durumu hazır')
    s=d.get('summary') or {}
    ok(int(s.get('analyzed_product_groups') or 0)>0,'gerçek ürünler analiz edildi')
    ok(int(s.get('eligible_history_groups') or 0)>0,'fiyat geçmişi yeterli ürün doğrulandı')
    ok(int(s.get('multi_offer_groups') or 0)>0,'çok mağazalı ürün doğrulandı')
    ok(0 <= float(s.get('minimum_score')) <= 100,'minimum skor geçerli')
    ok(0 <= float(s.get('maximum_score')) <= 100,'maksimum skor geçerli')
    print('\nFırsatAI v13.0.1 gerçek veri kabul smoke testi başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
