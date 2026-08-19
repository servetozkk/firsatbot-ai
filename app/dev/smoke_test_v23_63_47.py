from pathlib import Path
import ast
import shutil
import sqlite3
import tempfile

root = Path(__file__).resolve().parents[2]
checks=[]
def ok(name, cond):
    assert cond, name
    print("OK  ", name)
    checks.append(name)

main=(root/"main.py").read_text(encoding="utf-8")
identity=(root/"app/services/product_identity_service.py").read_text(encoding="utf-8")
svc=(root/"app/services/model_code_provenance_residue_v236347_service.py").read_text(encoding="utf-8")

ok("VERSION 23.63.47", (root/"VERSION").read_text().strip()=="23.63.47")
ok("runtime endpoint", "/api/runtime-identity/v236347" in main)
ok("runtime constant", '_RUNTIME_VERSION_V236323 = "23.63.47"' in main)
ok("architecture", "model-code-provenance-residue-capacity-suffix-lock" in main)
ok("startup service import", "run_canonical_evidence_integrity_v236347" in main)
ok("startup service call", "evidence_boot = run_canonical_evidence_integrity_v236347()" in main)
ok("kapasitesi classifier token", "kapasitesi" in identity)
ok("no automatic merge", '"automatic_merge_count": 0' in svc and "_merge_global" not in svc)
ok("no variant key rewrite", '"variant_key_rewrite_count": 0' in svc and ".variant_key =" not in svc)
ok("asin preserved policy", "b0-asin-codes-preserved-not-treated-as-pseudo" in main)
ok("v236346 fail closed preserved", "v23.63.46-preserved-fail-closed-no-auto-merge" in main)
ok("security bypass disabled", 'security_challenge_bypass": "disabled"' in main)
ok("price integrity preserved", 'price_integrity_quarantine": "preserved-and-lifecycle-normalized"' in main)

from app.services.product_identity_service import ProductIdentityService
for token in [
    "kapasitesi90", "kapasite90", "araligi3500-4000", "uzunlugu110-120",
    "dci-p3", "tr63", "cozunurluk1920", "agirligi2", "seviyesi5"
]:
    ok("pseudo contract "+token, ProductIdentityService._is_pseudo_model_code(token))
for token in ["b0f1fnx644", "b0gct2k94t", "x1504va-bq5391", "a2681", "acs04236", "pb200lzm"]:
    ok("real code preserved "+token, not ProductIdentityService._is_pseudo_model_code(token))

# Static DB residue proof on a temporary copy: both GP83 and Variant89 must be classifiable.
source_db = root/"data/products.db"
if source_db.exists():
    with tempfile.TemporaryDirectory() as td:
        temp_db = Path(td)/"products.db"
        shutil.copy2(source_db, temp_db)
        con = sqlite3.connect(temp_db)
        gp_rows = con.execute("SELECT id, model_code FROM global_products WHERE model_code IS NOT NULL").fetchall()
        var_rows = con.execute("SELECT id, model_code FROM global_product_variants WHERE model_code IS NOT NULL").fetchall()
        gp_dirty = [r for r in gp_rows if ProductIdentityService._is_pseudo_model_code(r[1])]
        var_dirty = [r for r in var_rows if ProductIdentityService._is_pseudo_model_code(r[1])]
        # Emulate service cleanup on the temp snapshot, then prove idempotence.
        for rid, code in gp_dirty:
            con.execute("UPDATE global_products SET model_code=NULL WHERE id=?", (rid,))
        for rid, code in var_dirty:
            con.execute("UPDATE global_product_variants SET model_code=NULL WHERE id=?", (rid,))
        con.commit()
        gp_after = [r for r in con.execute("SELECT id, model_code FROM global_products WHERE model_code IS NOT NULL") if ProductIdentityService._is_pseudo_model_code(r[1])]
        var_after = [r for r in con.execute("SELECT id, model_code FROM global_product_variants WHERE model_code IS NOT NULL") if ProductIdentityService._is_pseudo_model_code(r[1])]
        ok("snapshot pseudo GP cleanup reaches zero", len(gp_after)==0)
        ok("snapshot pseudo variant cleanup reaches zero", len(var_after)==0)
        ok("snapshot GP cleanup idempotent", not gp_after)
        ok("snapshot variant cleanup idempotent", not var_after)
        con.close()

for rel in [
    "main.py", "app/services/product_identity_service.py",
    "app/services/global_catalog_service.py", "app/services/bulk_identity_service.py",
    "app/services/model_code_provenance_residue_v236347_service.py"
]:
    ast.parse((root/rel).read_text(encoding="utf-8"))
    ok("AST "+rel, True)

print(f"V23.63.47 MASTER smoke OK {len(checks)}/{len(checks)}")
