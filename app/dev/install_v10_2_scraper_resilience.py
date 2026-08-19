from pathlib import Path
ROOT=Path.cwd()
def main():
 p=ROOT/"app/services/category_discovery_service.py"; t=p.read_text(encoding="utf-8")
 imp="from app.services.scraper_resilience_service import resilient_call, store_code_from_url\n"
 if imp not in t: t=t.replace("from app.services.product_identity_service import ProductIdentityService\n","from app.services.product_identity_service import ProductIdentityService\n"+imp,1)
 old="""    @staticmethod
    def _scrape_one(url: str, retry_count: int) -> Any:
        last_error: Exception | None = None
        for attempt in range(retry_count + 1):
            try:
                registry = ScraperRegistry()
                return registry.scrape(url)
            except Exception as error:  # noqa: BLE001 - hata sonuçta raporlanır
                last_error = error
                if attempt < retry_count:
                    time.sleep(1.0 + attempt)
        assert last_error is not None
        raise last_error
"""
 new="""    @staticmethod
    def _scrape_one(url: str, retry_count: int) -> Any:
        def operation() -> Any:
            return ScraperRegistry().scrape(url)
        return resilient_call(store_code=store_code_from_url(url),url=url,operation=operation,requested_retries=retry_count,context="category_product_detail")
"""
 if "return resilient_call(" not in t:
  if old not in t: raise RuntimeError("_scrape_one bulunamadı")
  t=t.replace(old,new,1)
 p.write_text(t,encoding="utf-8")
 p=ROOT/"app/services/v9_catalog_ingestion_service.py"; t=p.read_text(encoding="utf-8")
 imp="from app.services.scraper_resilience_service import assert_circuit_closed, get_store_health\n"
 if imp not in t: t=t.replace("from app.services.operational_log_service import record_operation_event\n","from app.services.operational_log_service import record_operation_event\n"+imp,1)
 if 'assert_circuit_closed(source["store_code"])' not in t: t=t.replace("    try:\n        try:\n            result = service.scan_and_save(","    try:\n        assert_circuit_closed(source[\"store_code\"])\n        try:\n            result = service.scan_and_save(",1)
 p.write_text(t,encoding="utf-8")
 p=ROOT/"main.py"; t=p.read_text(encoding="utf-8-sig"); imp="from app.web.admin_v10_scraper_health_routes import router as admin_v10_scraper_health_router\n"
 if imp not in t: t=t.replace("from app.web.admin_v10_operations_routes import router as admin_v10_operations_router\n","from app.web.admin_v10_operations_routes import router as admin_v10_operations_router\n"+imp,1)
 if "app.include_router(admin_v10_scraper_health_router)" not in t: t=t.replace("app.include_router(admin_v10_operations_router)\n","app.include_router(admin_v10_operations_router)\napp.include_router(admin_v10_scraper_health_router)\n",1)
 p.write_text(t,encoding="utf-8-sig")
 print("V10.2 entegrasyonu tamamlandı.")
 return 0
if __name__=="__main__": raise SystemExit(main())
