from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]

def ok(v, m):
    if not v: raise AssertionError(m)
    print(f"OK  {m}")

def main():
    ok((ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()=='12.2.1','VERSION 12.2.1')
    p=ROOT/'data/reports/v12_2_1_beta1_acceptance_report.json'
    ok(p.exists(),'kullanıcı kabul raporu oluşturuldu')
    d=json.loads(p.read_text(encoding='utf-8'))
    ok(d.get('status')=='BETA1_ACCEPTANCE_READY','Beta-1 kabul durumu hazır')
    ok(d.get('read_only') is True,'kabul testi salt okunur')
    ok(d.get('passed')==d.get('total'),'tüm kabul kontrolleri geçti')
    ok(d.get('counts',{}).get('active_global_offers',0)>0,'aktif global teklifler doğrulandı')
    ok(d.get('counts',{}).get('multi_store_products',0)>0,'çok mağazalı ürün doğrulandı')
    print('\nFırsatAI v12.2.1 smoke test başarılı.')
    return 0

if __name__=='__main__': raise SystemExit(main())
