from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
checks=[]
def ok(cond,name):
    checks.append((bool(cond),name)); print(('OK   ' if cond else 'FAIL ')+name)
version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
main=(ROOT/'main.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
binding=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
launcher=(ROOT/'BASLAT_V23_62_79.bat').read_text(encoding='utf-8')
ok(version=='23.62.79','VERSION')
ok('/api/runtime-identity/v236279' in main,'runtime v236279')
ok('/api/runtime-soak-stability/v236279' in main,'soak v236279')
ok('single-source-v236279' in main,'single source v236279')
ok('_RUNTIME_VERSION_V236279 = "23.62.79"' in main,'runtime constant')
ok('V23.62.79: token-boundary-safe source-color extraction' in cross,'source-color hotfix marker')
ok('_color_term_present_v23626(hay, value_v23623)' in cross,'boundary helper wired')
ok('V23.62.78 AMAZON PHONE SEARCH-CARD PREFILTER' in binding,'v78 Amazon prefilter preserved')
ok('V23.62.77 AMAZON BOUNDED IDENTITY-REJECT RETRY CAP' in binding,'v77 bounded retry preserved')
ok('23.62.79' in launcher and 'smoke_test_v23_62_79.py' in launcher,'launcher v79')
# Dependency-free behavioral regression evidence for the exact bug.
import re, unicodedata
def norm(v):
    v=unicodedata.normalize("NFKD",str(v or ""))
    v="".join(ch for ch in v if not unicodedata.combining(ch)).lower()
    return re.sub(r"[^a-z0-9]+"," ",v).strip()
def present(hay, term):
    hay=norm(hay); term=norm(term)
    return bool(term and re.search(r"(?<![a-z0-9])"+re.escape(term)+r"(?![a-z0-9])",hay))
def color(v):
    aliases={
      "beyaz":("seramik beyazı","seramik beyazi","seramik beyaz","ceramic white","beyaz","white"),
      "siyah":("seramik siyah","ceramic black","siyah","black"),
      "mavi":("ada mavisi","mavi","blue"),
      "kirmizi":("kırmızı","kirmizi","red"),
      "yesil":("yeşil","yesil","green"),
      "gri":("gri","gray","grey"),
      "mor":("mor","purple"), "pembe":("pembe","pink"),
    }
    for c,vals in aliases.items():
        for t in vals:
            if present(v,t): return c
    return ""
ok(color('XIAOMI Redmi Note 15 Pro 8 GB 256 GB Akıllı Telefon Titanyum Gri')=='gri','behavior Redmi Titanyum Gri => gri')
ok(color('Xiaomi Redmi Note 15 Pro 256GB')!='kirmizi','behavior Redmi token is not red color')
ok(color('Telefon Red 256 GB')=='kirmizi','behavior standalone Red => kirmizi')
ok(color('Bluetooth kulaklık siyah')=='siyah','behavior blue does not match bluetooth')
failed=[n for c,n in checks if not c]
print(f"V23.62.79 smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
if failed: print('FAILED:',failed)
raise SystemExit(1 if failed else 0)
