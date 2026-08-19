from pathlib import Path
import ast
import re

root = Path(__file__).resolve().parents[2]
checks=[]
def ok(name, cond):
    assert cond, name
    print("OK  ", name)
    checks.append(name)

main=(root/"main.py").read_text(encoding="utf-8")
identity=(root/"app/services/product_identity_service.py").read_text(encoding="utf-8")
global_catalog=(root/"app/services/global_catalog_service.py").read_text(encoding="utf-8")
bulk=(root/"app/services/bulk_identity_service.py").read_text(encoding="utf-8")
svc=(root/"app/services/canonical_evidence_integrity_v236346_service.py").read_text(encoding="utf-8")

ok("VERSION 23.63.46", (root/"VERSION").read_text().strip()=="23.63.46")
ok("runtime endpoint", "/api/runtime-identity/v236346" in main)
ok("runtime constant", '_RUNTIME_VERSION_V236323 = "23.63.46"' in main)
ok("architecture", "canonical-evidence-provenance-hardening-no-auto-merge" in main)
ok("startup service import", "run_canonical_evidence_integrity_v236346" in main)
ok("post-v236345 startup order", main.index("quarantine_boot = run_quarantine_lifecycle_integrity_v236345()") < main.index("evidence_boot = run_canonical_evidence_integrity_v236346()"))
ok("araligi pseudo protected", "araligi" in identity)
ok("kapasite pseudo protected", "kapasite" in identity)
ok("dci p3 pseudo protected", "dci-p3" in identity)
ok("tr63 pseudo protected", "tr63" in identity)
ok("global catalog safe model code", "def _safe_model_code" in global_catalog and "ProductIdentityService._is_pseudo_model_code" in global_catalog)
ok("global preferred write safe", 'global_product.model_code = _safe_model_code(identity.get("model_code"))' in global_catalog)
ok("global variant write safe", 'model_code=_safe_model_code(identity.get("model_code"))' in global_catalog)
ok("bulk safe model code", "def _safe_model_code" in bulk and "ProductIdentityService._is_pseudo_model_code" in bulk)
ok("startup cleans global residue", "gp.model_code = None" in svc)
ok("startup cleans variant residue", "variant.model_code = None" in svc)
ok("no automatic merge", '"automatic_merge_count": 0' in svc and "_merge_global" not in svc)
ok("no variant key rewrite", '"variant_key_rewrite_count": 0' in svc and ".variant_key =" not in svc)
ok("asin preserved policy", "b0-asin-codes-preserved-not-treated-as-pseudo" in main)
ok("duplicate fail closed policy", "fail-closed-no-auto-merge-without-raw-evidence-consensus" in main)
ok("network evidence policy", "missing-network-is-not-equality-proof" in main)
ok("v236345 preserved", "run_quarantine_lifecycle_integrity_v236345" in main)
ok("v236344 preserved", "run_source_identity_integrity_v236344" in main)
ok("v236343 preserved", "run_model_code_counter_integrity_v236343" in main)
ok("v236342 preserved", "run_accessory_identity_convergence_v236342" in main)
ok("v236341 preserved", "run_variant_referential_convergence_v236341" in main)

# Production classifier boundary: pseudo specification labels are rejected, real ASIN/SKU codes survive.
from app.services.product_identity_service import ProductIdentityService
for token in ["araligi3500-4000","kapasite0-15","uzunlugu110-120","dci-p3","tr63","cozunurluk1920"]:
    ok("pseudo contract "+token, ProductIdentityService._is_pseudo_model_code(token))
for token in ["b0f1fnx644","b0gct2k94t","x1504va-bq5391","a2681","acs04236"]:
    ok("real code preserved "+token, not ProductIdentityService._is_pseudo_model_code(token))

for rel in ["main.py","app/services/product_identity_service.py","app/services/global_catalog_service.py","app/services/bulk_identity_service.py","app/services/canonical_evidence_integrity_v236346_service.py"]:
    ast.parse((root/rel).read_text(encoding="utf-8"))
    ok("AST "+rel, True)

ok("security bypass disabled", 'security_challenge_bypass": "disabled"' in main)
ok("price integrity preserved", 'price_integrity_quarantine": "preserved-and-lifecycle-normalized"' in main)
print(f"V23.63.46 MASTER smoke OK {len(checks)}/{len(checks)}")
