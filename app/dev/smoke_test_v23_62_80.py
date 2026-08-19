from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(c,n):
    checks.append((bool(c),n)); print(("OK   " if c else "FAIL ")+n)
version=(ROOT/"VERSION").read_text(encoding="utf-8").strip()
main=(ROOT/"main.py").read_text(encoding="utf-8")
repair=(ROOT/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
cross=(ROOT/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
launcher=(ROOT/"BASLAT_V23_62_80.bat").read_text(encoding="utf-8")
ok(version=="23.62.80","VERSION")
ok('_RUNTIME_VERSION_V236280 = "23.62.80"' in main,"runtime constant")
ok('/api/runtime-identity/v236280' in main,"runtime v236280")
ok('/api/runtime-soak-stability/v236280' in main,"soak v236280")
ok('"runtime_version": _RUNTIME_VERSION_V236280' in main,"force uses v236280")
ok('detail-color-reject-evidence-telemetry' in main,"architecture")
ok('V23.62.80 DETAIL COLOR REJECT EVIDENCE' in repair,"color evidence marker")
for fld in ('source_name=','source_model=','source_category=','source_url=','candidate_name=','candidate_model=','candidate_category=','candidate_url='):
    ok(fld in repair, 'evidence '+fld.rstrip('='))
ok('source_detail_color != candidate_detail_color' in repair,"fail-closed color gate preserved")
ok('V23.62.79: token-boundary-safe source-color extraction' in cross,"v79 source boundary preserved")
ok('V23.62.78 AMAZON PHONE' in repair or 'V23.62.78' in repair,"v78 amazon prefilter preserved")
ok('V23.62.77 AMAZON' in repair,"v77 bounded retry preserved")
ok('security_challenge_bypass": "disabled"' in main,"security bypass disabled")
ok('23.62.80' in launcher and 'smoke_test_v23_62_80.py' in launcher,"launcher v80")
failed=[n for c,n in checks if not c]
print(f"V23.62.80 smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
if failed:
    print('FAILED:',failed); sys.exit(1)
