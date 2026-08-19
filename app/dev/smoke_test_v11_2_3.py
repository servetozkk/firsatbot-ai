from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'data'/'reports'/'v11_2_3_group_merge_safety_analysis.json'

def ok(v,m):
    if not v: raise AssertionError(m)
    print(f'OK  {m}')

def main():
    ok((ROOT/'VERSION').read_text(encoding='utf-8').strip()=='11.2.3','VERSION 11.2.3')
    ok(REPORT.exists(),'güvenlik analiz raporu oluşturuldu')
    data=json.loads(REPORT.read_text(encoding='utf-8'))
    ok(data.get('mode')=='read_only_dry_run','analiz salt okunur modda')
    ok(data.get('analysis',{}).get('verdict') in {'safe_for_automatic_merge','reference_migration_required','manual_schema_review_required'},'birleştirme kararı üretildi')
    ok(bool(data.get('selected_direction',{}).get('source_group_id')),'kaynak grup belirlendi')
    ok(bool(data.get('selected_direction',{}).get('target_group_id')),'hedef grup belirlendi')
    print('\nFırsatAI v11.2.3 smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
