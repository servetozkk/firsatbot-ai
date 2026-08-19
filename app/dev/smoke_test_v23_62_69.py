from pathlib import Path
import sys
root=Path(__file__).resolve().parents[2]
main=(root/'main.py').read_text(encoding='utf-8')
search=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
amazon=(root/'app/scrapers/amazon.py').read_text(encoding='utf-8')
smart=(root/'app/services/smart_catalog_refresh_v218_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION',(root/'VERSION').read_text().strip()=='23.62.69'),
 ('runtime v236269','/api/runtime-identity/v236269' in main),
 ('soak v236269','/api/runtime-soak-stability/v236269' in main),
 ('single source v236269','_RUNTIME_VERSION_V236269 = "23.62.69"' in main),
 ('force uses v236269','"runtime_version": _RUNTIME_VERSION_V236269' in main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):]),
 ('store budget v68 preserved','V23.62.68 FORCE STORE-BUDGET CONTRACT' in smart),
 ('minimum contract preserved','minimum_offer_count' in main and 'minimum_store_success_count' in main),
 ('phone jelatin token','"jelatin"' in search),
 ('phone nano cam token','"nano cam"' in search),
 ('phone seramik film token','"seramik film"' in search),
 ('phone temperli cam token','"temperli cam"' in search),
 ('amazon browser nav 15s','navigation_timeout_ms=15_000' in amazon),
 ('amazon initial wait 1s','initial_wait_seconds=1.0' in amazon),
 ('amazon no scroll','scroll_page=False' in amazon),
 ('amazon old nav retired','navigation_timeout_ms=60_000' not in amazon[amazon.index('def _download_with_playwright'):amazon.index('def _is_security_page')]),
 ('amazon old wait retired','initial_wait_seconds=6.0' not in amazon[amazon.index('def _download_with_playwright'):amazon.index('def _is_security_page')]),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
 ('launcher exists',(root/'BASLAT_V23_62_69.bat').exists()),
 ('launcher calls v69 smoke','smoke_test_v23_62_69.py' in (root/'BASLAT_V23_62_69.bat').read_text(encoding='utf-8')),
]
# dependency-free behavioral evidence for the exact leaked N11 accessory card
import unicodedata, re
def fold(v):
    v=unicodedata.normalize("NFKD",str(v or "")).encode("ascii","ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+"," ",v).strip()
leaked=fold("Redmi Note 15 Pro 4G Ekran Nano Cam Koruyucu Jelatin Seramik Film Kavisli Esnek Tam Kaplar")
new_tokens=("jelatin","koruyucu jelatin","nano cam","seramik film","koruyucu film","temperli cam","tempered glass")
checks.append(("behavioral leaked phone accessory caught", any(fold(t) in leaked for t in new_tokens)))
real_phone=fold("Xiaomi Redmi Note 15 Pro 8 GB 256 GB Titanyum Gri")
checks.append(("behavioral real phone has no new accessory token", not any(fold(t) in real_phone for t in new_tokens)))
failed=[name for name,ok in checks if not ok]
for name,ok in checks:
    print(('OK  ' if ok else 'FAIL'),name)
print(f"V23.62.69 smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
if failed:
    raise SystemExit(1)
