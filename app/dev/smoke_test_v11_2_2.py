from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)
def main():
    ok((ROOT/'VERSION').read_text(encoding='utf-8').strip()=='11.2.2','VERSION 11.2.2')
    ok((ROOT/'data/reports/v11_2_2_cross_store_repair_execute.json').exists(),'onarım raporu oluşturuldu')
    print('\nFırsatAI v11.2.2 smoke test başarılı.'); return 0
if __name__=='__main__': raise SystemExit(main())
