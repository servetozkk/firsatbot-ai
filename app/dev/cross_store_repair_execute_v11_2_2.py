from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from sqlalchemy import MetaData, Table, select, update, delete, func, inspect

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from app.database.database import engine
from app.dev.cross_store_repair_preview_v11_2_1 import main as preview_main

VERSION='11.2.2'
REPORT_DIR=ROOT/'data'/'reports'
BACKUP_DIR=ROOT/'data'/'backups'/'cross_store_repair'
PREVIEW=REPORT_DIR/'v11_2_1_cross_store_repair_preview.json'

def serial(v:Any):
    if isinstance(v,(datetime,)): return v.isoformat()
    return v

def rowdict(r): return {k:serial(v) for k,v in dict(r).items()}

def fk_refs(metadata, group_table):
    refs=[]
    for name in inspect(engine).get_table_names():
        t=Table(name,metadata,autoload_with=engine)
        for fk in t.foreign_keys:
            if fk.column.table.name==group_table.name:
                refs.append((t,fk.parent.name))
    return refs

def count_refs(conn, refs, gid):
    out={}
    for t,col in refs:
        out[f'{t.name}.{col}']=int(conn.execute(select(func.count()).select_from(t).where(t.c[col]==gid)).scalar_one())
    return out

def main():
    REPORT_DIR.mkdir(parents=True,exist_ok=True); BACKUP_DIR.mkdir(parents=True,exist_ok=True)
    preview_main()
    data=json.loads(PREVIEW.read_text(encoding='utf-8'))
    moves=data.get('high_confidence_move_candidates',[])
    merges=[x for x in data.get('group_merge_candidates',[]) if x.get('decision')=='high_confidence_merge_candidate']
    if len(moves)>1 or len(merges)>1:
        raise RuntimeError(f'Güvenlik durdurması: beklenenden fazla aday var (taşıma={len(moves)}, birleştirme={len(merges)}).')
    md=MetaData(); groups=Table('product_groups',md,autoload_with=engine); offers=Table('product_offers',md,autoload_with=engine)
    refs=fk_refs(md,groups); stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    backup={'version':VERSION,'created_at':datetime.now(timezone.utc).isoformat(),'preview_summary':data.get('summary',{}),'moves':moves,'merges':merges,'rows':{}}
    result={'version':VERSION,'executed_at':datetime.now(timezone.utc).isoformat(),'moves_applied':[],'merges_applied':[],'skipped':[]}
    with engine.begin() as conn:
        affected_gids=set()
        for m in moves: affected_gids|={int(m['current_group_id']),int(m['suggested_group_id'])}
        for m in merges: affected_gids|={int(m['left_group_id']),int(m['right_group_id'])}
        backup['rows']['product_groups']=[rowdict(r) for r in conn.execute(select(groups).where(groups.c.id.in_(affected_gids))).mappings()]
        backup['rows']['product_offers']=[rowdict(r) for r in conn.execute(select(offers).where(offers.c.group_id.in_(affected_gids))).mappings()]
        backup['reference_counts']={str(g):count_refs(conn,refs,g) for g in affected_gids}
        # Tek yüksek güvenli teklif taşıması
        for m in moves:
            oid=int(m['offer_id']); src=int(m['current_group_id']); dst=int(m['suggested_group_id'])
            current=conn.execute(select(offers.c.group_id).where(offers.c.id==oid)).scalar_one_or_none()
            if current!=src:
                result['skipped'].append({'type':'move','offer_id':oid,'reason':'current_group_changed'}); continue
            conn.execute(update(offers).where(offers.c.id==oid).values(group_id=dst))
            result['moves_applied'].append({'offer_id':oid,'from_group_id':src,'to_group_id':dst,'score':m.get('suggested_score')})
        # Tek yüksek güvenli grup birleştirmesi. Yalnızca offer referansları varsa uygulanır.
        for m in merges:
            a,b=int(m['left_group_id']),int(m['right_group_id'])
            counts_a=count_refs(conn,refs,a); counts_b=count_refs(conn,refs,b)
            non_offer_a=sum(v for k,v in counts_a.items() if not k.startswith('product_offers.'))
            non_offer_b=sum(v for k,v in counts_b.items() if not k.startswith('product_offers.'))
            if non_offer_a or non_offer_b:
                result['skipped'].append({'type':'merge','left_group_id':a,'right_group_id':b,'reason':'non_offer_references_exist','left_refs':counts_a,'right_refs':counts_b}); continue
            ca=int(conn.execute(select(func.count()).select_from(offers).where(offers.c.group_id==a)).scalar_one())
            cb=int(conn.execute(select(func.count()).select_from(offers).where(offers.c.group_id==b)).scalar_one())
            target,source=(a,b) if (ca,-a)>=(cb,-b) else (b,a)
            conn.execute(update(offers).where(offers.c.group_id==source).values(group_id=target))
            remaining=count_refs(conn,refs,source)
            if sum(remaining.values())==0:
                conn.execute(delete(groups).where(groups.c.id==source))
                result['merges_applied'].append({'source_group_id':source,'target_group_id':target,'score':m.get('score'),'source_offer_count':min(ca,cb)})
            else:
                raise RuntimeError(f'Birleştirme sonrası kaynak grupta referans kaldı: {remaining}')
    backup_path=BACKUP_DIR/f'v11_2_2_before_repair_{stamp}.json'; backup_path.write_text(json.dumps(backup,ensure_ascii=False,indent=2),encoding='utf-8')
    # Son doğrulama önizlemesi
    preview_main(); post=json.loads(PREVIEW.read_text(encoding='utf-8'))
    result['post_summary']=post.get('summary',{})
    report=REPORT_DIR/'v11_2_2_cross_store_repair_execute.json'; report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"OK  Uygulanan teklif taşıması: {len(result['moves_applied'])}")
    print(f"OK  Uygulanan grup birleştirmesi: {len(result['merges_applied'])}")
    print(f"BİLGİ  Güvenlik nedeniyle atlanan: {len(result['skipped'])}")
    print(f"BİLGİ  Kalan yüksek güvenli taşıma adayı: {result['post_summary'].get('high_confidence_move_candidate_count')}")
    print(f"BİLGİ  Kalan yüksek güvenli birleştirme adayı: {result['post_summary'].get('high_confidence_merge_candidate_count')}")
    print(f'YEDEK: {backup_path}'); print(f'RAPOR: {report}')
    return 0
if __name__=='__main__': raise SystemExit(main())
