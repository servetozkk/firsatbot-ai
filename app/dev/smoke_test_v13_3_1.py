from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)
def main():
    ok((ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()=='13.3.1','VERSION 13.3.1')
    p=ROOT/'data/reports/v13_3_1_smart_search_real_data_acceptance.json'
    ok(p.exists(),'gerçek veri akıllı arama raporu oluşturuldu')
    d=json.loads(p.read_text(encoding='utf-8'))
    ok(d.get('read_only') is True,'kabul testi salt okunur')
    ok(d.get('status')=='SMART_SEARCH_REAL_DATA_ACCEPTANCE_READY','akıllı arama kabul durumu hazır')
    ok(d['summary']['checks_passed']==d['summary']['checks_total'],'tüm akıllı arama kontrolleri geçti')
    print('\nFırsatAI v13.3.1 gerçek veri akıllı arama smoke testi başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
