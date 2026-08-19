from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'data'/'reports'/'v11_2_4_specification_merge_execute.json'

def ok(v,m):
    if not v: raise AssertionError(m)
    print(f'OK  {m}')

def main():
    ok((ROOT/'VERSION').read_text(encoding='utf-8').strip()=='11.2.4','VERSION 11.2.4')
    ok(REPORT.exists(),'birleştirme raporu oluşturuldu')
    data=json.loads(REPORT.read_text(encoding='utf-8'))
    ok(data.get('specification_conflicts')==0,'specification çakışması yok')
    ok(data.get('source_group_deleted') is True,'kaynak grup silindi')
    ok(data.get('source_group_exists_after') is False,'kaynak grup artık yok')
    ok(data.get('source_specification_count_before',0)==data.get('moved_specifications',0)+data.get('duplicate_specifications_removed',0),'tüm specification kayıtları işlendi')
    ok(data.get('remaining_high_confidence_move_candidates')==0,'yüksek güvenli taşıma adayı kalmadı')
    ok(data.get('remaining_high_confidence_merge_candidates')==0,'yüksek güvenli birleştirme adayı kalmadı')
    print('\nFırsatAI v11.2.4 smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
