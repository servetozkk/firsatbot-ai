from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def text(p): return (ROOT/p).read_text(encoding="utf-8")
checks=[]
def ok(cond,name):
    checks.append((name,bool(cond))); print(("OK   " if cond else "FAIL ")+name)
version=text("VERSION").strip(); main=text("main.py"); amazon=text("app/scrapers/amazon.py"); cross=text("app/services/cross_store_search_service.py")
ok(version=="23.62.72","VERSION")
ok("/api/runtime-identity/v236272" in main,"runtime v236272")
ok("/api/runtime-soak-stability/v236272" in main,"soak v236272")
ok("single-source-v236272" in main,"single source v236272")
ok("amazon-store-level-wall-clock-detail-budget" in main,"architecture")
ok("detail_budget_seconds = 18.0" in amazon,"amazon 18s wall-clock budget")
ok("detail_deadline = time.monotonic() + detail_budget_seconds" in amazon,"amazon deadline")
ok("remaining_budget(cap=6.0)" in amazon,"detail/browser per-stage caps")
ok("timeout_seconds=recovery_timeout" in amazon,"recovery shares remaining budget")
ok("timeout=20" not in amazon,"old 20s recovery timeouts retired")
ok("timeout=max(0.5, float(timeout_seconds))" in amazon,"bounded requests/recovery timeout")
ok("navigation_timeout_ms=max(1_000, int(navigation_timeout_ms))" in amazon,"bounded browser navigation")
ok("V23.62.70 AMAZON NO-BUYABLE CIRCUIT BREAK" in cross,"v70 circuit preserved")
ok("jelatin" in cross and "seramik film" in cross,"v69 phone accessory filter preserved")
ok("security_challenge_bypass" in main and "disabled" in main,"security bypass disabled")
ok("price_integrity_quarantine" in main and "preserved" in main,"price integrity preserved")
launcher=ROOT/"BASLAT_V23_62_72.bat"
ok(launcher.exists(),"launcher exists")
if launcher.exists():
    lt=launcher.read_text(encoding="utf-8-sig")
    ok("smoke_test_v23_62_72.py" in lt,"launcher calls v72 smoke")
failed=[n for n,v in checks if not v]
print(f"V23.62.72 smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
