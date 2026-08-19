from pathlib import Path
import sys
def main():
 root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root))
 from app.services.catalog_scan_plan_service import get_catalog_plans
 from app.services.catalog_scan_manager import catalog_scan_manager
 from app.web.admin_catalog_scan_routes import router
 assert callable(get_catalog_plans);assert callable(catalog_scan_manager.start_plan)
 assert any(r.path=="/admin/catalog-scans" for r in router.routes)
 assert (root/"app/templates/admin_catalog_scans.html").exists()
 print("Otomatik Katalog Tarama Merkezi smoke test başarılı.");return 0
if __name__=="__main__":raise SystemExit(main())
