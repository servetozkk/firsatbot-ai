from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from app.services.scraper_resilience_service import classify_scraper_error, resilient_call, store_code_from_url, all_store_health
def c(v,m):
 if not v: raise AssertionError(m)
 print("OK ",m)
def main():
 c(store_code_from_url("https://www.n11.com/urun/x")=="n11","URL mağaza kodu algılanıyor")
 k,r=classify_scraper_error(RuntimeError("429 Too Many Requests")); c(k=="transient" and r,"429 yeniden denenebilir")
 state={"n":0}
 def flaky():
  state["n"]+=1
  if state["n"]<2: raise TimeoutError("timeout")
  return "ok"
 c(resilient_call(store_code="smoke",url="https://smoke.invalid/x",operation=flaky,requested_retries=1)=="ok","otomatik kurtarma çalışıyor")
 c(isinstance(all_store_health(),list),"sağlık listesi üretiliyor")
 d=(ROOT/"app/services/category_discovery_service.py").read_text(encoding="utf-8"); c("return resilient_call(" in d,"detay taraması dayanıklılık katmanına bağlı")
 i=(ROOT/"app/services/v9_catalog_ingestion_service.py").read_text(encoding="utf-8"); c("assert_circuit_closed" in i,"katalog devre kesiciye bağlı")
 m=(ROOT/"main.py").read_text(encoding="utf-8-sig"); c("admin_v10_scraper_health_router" in m,"sağlık paneli bağlı")
 print("\nFırsatAI v10.2 smoke test başarılı.")
 return 0
if __name__=="__main__": raise SystemExit(main())
