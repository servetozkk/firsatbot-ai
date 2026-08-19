from __future__ import annotations
import sqlite3,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
DB=ROOT/"data"/"products.db"
PRESERVE_VARIANT=155
PLANS={27:(27,26,28,None),175:(154,126,29,30),244:(188,150,127,155)}
DELETE_VARIANTS=(27,154,188)

def fk_refs(db,vid):
    out=[]
    for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
        t=r[0]
        for fk in db.execute('PRAGMA foreign_key_list("'+t+'")').fetchall():
            if fk[2]!="global_product_variants": continue
            c=fk[3]
            n=db.execute('SELECT COUNT(*) FROM "'+t+'" WHERE "'+c+'"=?',(vid,)).fetchone()[0]
            if n: out.append((t,c,n))
    return out

db=sqlite3.connect(str(DB)); db.row_factory=sqlite3.Row; db.execute("PRAGMA foreign_keys=ON")
try:
    db.execute("BEGIN IMMEDIATE")
    baseline={
      "history_wrong_gp":db.execute("""SELECT COUNT(*) FROM global_offer_price_history h JOIN global_product_variants gv ON gv.id=h.global_variant_id WHERE h.global_variant_id IS NOT NULL AND h.global_product_id!=gv.global_product_id""").fetchone()[0],
      "variant_drift":db.execute("""SELECT COUNT(*) FROM global_offers go JOIN raw_products rp ON rp.id=go.raw_product_id WHERE go.is_active=1 AND go.global_variant_id IS NOT NULL AND rp.global_variant_id IS NOT NULL AND go.global_variant_id!=rp.global_variant_id""").fetchone()[0],
      "raw_counter":db.execute("""SELECT COUNT(*) FROM global_products gp WHERE gp.raw_product_count!=(SELECT COUNT(*) FROM raw_products rp WHERE rp.global_product_id=gp.id)""").fetchone()[0],
      "offer_counter":db.execute("""SELECT COUNT(*) FROM global_products gp WHERE gp.active_offer_count!=(SELECT COUNT(*) FROM global_offers go WHERE go.global_product_id=gp.id AND go.is_active=1 AND go.is_hidden=0 AND go.lifecycle_status='ACTIVE' AND go.current_price>0)""").fetchone()[0],
      "duplicate_variant_keys":db.execute("""SELECT COUNT(*) FROM (SELECT global_product_id,variant_key,COUNT(*) c FROM global_product_variants GROUP BY global_product_id,variant_key HAVING COUNT(*)>1)""").fetchone()[0],
    }
    if any(baseline.values()): raise RuntimeError("Pre-repair baseline not clean: {}".format(baseline))

    p=db.execute("SELECT id,global_product_id,variant_key,color,network,model_code FROM global_product_variants WHERE id=155").fetchone()
    if p is None: raise RuntimeError("PRESERVE V155 missing")
    p_before=tuple(p)

    expected={
      27:(27,26,"model_code=cozunurluk1920",None,None,None),
      154:(154,126,"color=gri|model_code=s100.1362-bv00x-g-f","gri",None,"s100.1362-bv00x-g-f"),
      188:(188,150,"color=siyah|model_code=600c-400c-ht14s","siyah",None,"600c-400c-ht14s"),
    }
    for vid,exp in expected.items():
        r=db.execute("SELECT id,global_product_id,variant_key,color,network,model_code FROM global_product_variants WHERE id=?",(vid,)).fetchone()
        if r is None or tuple(r)!=exp: raise RuntimeError("V{} precondition drift: {}".format(vid,tuple(r) if r else None))
        rr=db.execute("SELECT COUNT(*) FROM raw_products WHERE global_variant_id=?",(vid,)).fetchone()[0]
        oo=db.execute("SELECT COUNT(*) FROM global_offers WHERE global_variant_id=?",(vid,)).fetchone()[0]
        if rr or oo: raise RuntimeError("V{} unexpectedly live raw={} offer={}".format(vid,rr,oo))

    changed=[]
    for hid,(svid,sgp,tgp,tvid) in PLANS.items():
        h=db.execute("""SELECT h.id,h.global_product_id history_gp,h.global_variant_id history_variant,go.global_product_id offer_gp,go.global_variant_id offer_variant,go.lifecycle_status,go.is_active,go.is_hidden,rp.global_product_id raw_gp,rp.global_variant_id raw_variant,rp.reconciliation_status FROM global_offer_price_history h JOIN global_offers go ON go.id=h.global_offer_id JOIN raw_products rp ON rp.id=go.raw_product_id WHERE h.id=?""",(hid,)).fetchone()
        if h is None: raise RuntimeError("H{} missing".format(hid))
        if not (
            h["history_gp"]==sgp
            and h["history_variant"]==svid
            and h["offer_gp"]==tgp
            and h["raw_gp"]==tgp
            and h["lifecycle_status"]=="ACTIVE"
            and h["is_active"]==1
            and h["is_hidden"]==0
            and h["reconciliation_status"]=="MATCHED"
        ):
            raise RuntimeError(
                "H{} ownership evidence drift: {}".format(
                    hid,
                    tuple(h)
                )
            )

        if not (
            h["offer_variant"] is None
            and h["raw_variant"] is None
        ):
            raise RuntimeError(
                "H{} expected NULL current variant evidence: {}".format(
                    hid,
                    tuple(h)
                )
            )

        if tvid is not None:
            sv=db.execute(
                """SELECT
                       id,
                       global_product_id,
                       variant_key,
                       color,
                       network,
                       model_code
                   FROM global_product_variants
                   WHERE id=?""",
                (svid,)
            ).fetchone()

            tv=db.execute(
                """SELECT
                       id,
                       global_product_id,
                       variant_key,
                       color,
                       network,
                       model_code
                   FROM global_product_variants
                   WHERE id=?""",
                (tvid,)
            ).fetchone()

            if sv is None:
                raise RuntimeError(
                    "H{} source variant missing".format(hid)
                )

            if tv is None or tv["global_product_id"]!=tgp:
                raise RuntimeError(
                    "H{} target variant invalid".format(hid)
                )

            source_semantic=(
                sv["variant_key"],
                sv["color"],
                sv["network"],
                sv["model_code"],
            )

            target_semantic=(
                tv["variant_key"],
                tv["color"],
                tv["network"],
                tv["model_code"],
            )

            if source_semantic!=target_semantic:
                raise RuntimeError(
                    "H{} semantic reconstruction mismatch "
                    "source={} target={}".format(
                        hid,
                        source_semantic,
                        target_semantic
                    )
                )
        c=db.execute("UPDATE global_offer_price_history SET global_product_id=?,global_variant_id=? WHERE id=? AND global_product_id=? AND global_variant_id=?",(tgp,tvid,hid,sgp,svid)).rowcount
        if c!=1: raise RuntimeError("H{} update count={}".format(hid,c))
        changed.append((hid,sgp,svid,tgp,tvid))

    deleted=[]
    for vid in DELETE_VARIANTS:
        refs=fk_refs(db,vid)
        if refs: raise RuntimeError("V{} FK refs remain {}".format(vid,refs))
        c=db.execute("DELETE FROM global_product_variants WHERE id=?",(vid,)).rowcount
        if c!=1: raise RuntimeError("V{} delete count={}".format(vid,c))
        deleted.append(vid)

    p2=db.execute("SELECT id,global_product_id,variant_key,color,network,model_code FROM global_product_variants WHERE id=155").fetchone()
    if p2 is None or tuple(p2)!=p_before: raise RuntimeError("PRESERVE V155 changed")

    db.execute("""UPDATE global_products SET raw_product_count=(SELECT COUNT(*) FROM raw_products rp WHERE rp.global_product_id=global_products.id)""")
    db.execute("""UPDATE global_products SET active_offer_count=(SELECT COUNT(*) FROM global_offers go WHERE go.global_product_id=global_products.id AND go.is_active=1 AND go.is_hidden=0 AND go.lifecycle_status='ACTIVE' AND go.current_price>0)""")

    exact={27:(27,28,None),175:(175,29,30),244:(244,127,155)}
    for hid,exp in exact.items():
        r=db.execute("SELECT id,global_product_id,global_variant_id FROM global_offer_price_history WHERE id=?",(hid,)).fetchone()
        if r is None or tuple(r)!=exp: raise RuntimeError("H{} final mismatch: {}".format(hid,tuple(r) if r else None))

    checks={
      "history_wrong_gp":db.execute("""SELECT COUNT(*) FROM global_offer_price_history h JOIN global_product_variants gv ON gv.id=h.global_variant_id WHERE h.global_variant_id IS NOT NULL AND h.global_product_id!=gv.global_product_id""").fetchone()[0],
      "variant_drift":db.execute("""SELECT COUNT(*) FROM global_offers go JOIN raw_products rp ON rp.id=go.raw_product_id WHERE go.is_active=1 AND go.global_variant_id IS NOT NULL AND rp.global_variant_id IS NOT NULL AND go.global_variant_id!=rp.global_variant_id""").fetchone()[0],
      "offer_variant_wrong_gp":db.execute("""SELECT COUNT(*) FROM global_offers go JOIN global_product_variants gv ON gv.id=go.global_variant_id WHERE go.global_variant_id IS NOT NULL AND go.global_product_id!=gv.global_product_id""").fetchone()[0],
      "raw_variant_wrong_gp":db.execute("""SELECT COUNT(*) FROM raw_products rp JOIN global_product_variants gv ON gv.id=rp.global_variant_id WHERE rp.global_variant_id IS NOT NULL AND rp.global_product_id!=gv.global_product_id""").fetchone()[0],
      "raw_counter":db.execute("""SELECT COUNT(*) FROM global_products gp WHERE gp.raw_product_count!=(SELECT COUNT(*) FROM raw_products rp WHERE rp.global_product_id=gp.id)""").fetchone()[0],
      "offer_counter":db.execute("""SELECT COUNT(*) FROM global_products gp WHERE gp.active_offer_count!=(SELECT COUNT(*) FROM global_offers go WHERE go.global_product_id=gp.id AND go.is_active=1 AND go.is_hidden=0 AND go.lifecycle_status='ACTIVE' AND go.current_price>0)""").fetchone()[0],
      "quarantine":db.execute("""SELECT COUNT(*) FROM global_offers WHERE lifecycle_status='QUARANTINED' AND (is_active=1 OR is_hidden=0)""").fetchone()[0],
      "duplicate_variant_keys":db.execute("""SELECT COUNT(*) FROM (SELECT global_product_id,variant_key,COUNT(*) c FROM global_product_variants GROUP BY global_product_id,variant_key HAVING COUNT(*)>1)""").fetchone()[0],
      "deleted_variants_remaining":db.execute("SELECT COUNT(*) FROM global_product_variants WHERE id IN (27,154,188)").fetchone()[0],
      "deleted_variant_history_remaining":db.execute("SELECT COUNT(*) FROM global_offer_price_history WHERE global_variant_id IN (27,154,188)").fetchone()[0],
    }
    if any(checks.values()): raise RuntimeError("Post-repair integrity failure: {}".format(checks))
    db.commit()
    print("V23.63.58 repair OK: history={}; deleted={}; preserved=[155]; integrity={}".format(changed,deleted,checks))
except Exception:
    db.rollback(); raise
finally:
    db.close()
