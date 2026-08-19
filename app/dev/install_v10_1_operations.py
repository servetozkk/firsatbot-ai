from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()


def patch_main() -> None:
    path = ROOT / "main.py"
    text = path.read_text(encoding="utf-8-sig")
    router_import = "from app.web.admin_v10_operations_routes import router as admin_v10_operations_router\n"
    if router_import not in text:
        anchor = "from app.web.admin_v10_release_routes import router as admin_v10_release_router\n"
        text = text.replace(anchor, anchor + router_import, 1) if anchor in text else router_import + text
    service_import = "from app.services.operational_log_service import configure_operational_logging, record_operation_event\n"
    if service_import not in text:
        text = text.replace("from app.core.config import settings\n", "from app.core.config import settings\n" + service_import, 1)
    if "configure_operational_logging()" not in text:
        text = text.replace(
            '    print("Fırsat AI başlatılıyor...")',
            '    configure_operational_logging()\n    record_operation_event(level="INFO", source="application", event_type="startup", message="Fırsat AI başlatılıyor.")\n    print("Fırsat AI başlatılıyor...")',
            1,
        )
    if 'event_type="shutdown"' not in text:
        text = text.replace(
            '        print("Fırsat AI kapatılıyor...")',
            '        record_operation_event(level="INFO", source="application", event_type="shutdown", message="Fırsat AI kapatılıyor.")\n        print("Fırsat AI kapatılıyor...")',
            1,
        )
    if 'event_type="unhandled_exception"' not in text:
        marker = '@app.exception_handler(500)\nasync def server_error_handler(request: Request, exc):\n'
        replacement = marker + '    record_operation_event(level="ERROR", source="http", event_type="unhandled_exception", message=f"{type(exc).__name__}: {exc}", details={"method": request.method, "path": request.url.path})\n'
        if marker not in text:
            raise RuntimeError("500 handler bulunamadı")
        text = text.replace(marker, replacement, 1)
    include = "app.include_router(admin_v10_operations_router)\n"
    if include not in text:
        anchor = "app.include_router(admin_v10_release_router)\n"
        text = text.replace(anchor, anchor + include, 1) if anchor in text else text + "\n" + include
    path.write_text(text, encoding="utf-8-sig")


def patch_reconciliation() -> None:
    path = ROOT / "app/services/catalog_reconciliation_service.py"
    text = path.read_text(encoding="utf-8")
    imp = "from app.services.operational_log_service import record_operation_event\n"
    if imp not in text:
        anchor = "from app.services.product_identity_service import ProductIdentityService\n"
        text = text.replace(anchor, anchor + imp, 1)
    old = '    except Exception as error:\n        raw.reconciliation_status = "FAILED"\n'
    new = '    except Exception as error:\n        record_operation_event(level="ERROR", source="reconciliation", event_type="raw_product_failed", message=f"{type(error).__name__}: {error}", details={"raw_product_id": raw.id, "store_code": raw.store_code, "source_url": raw.source_url})\n        raw.reconciliation_status = "FAILED"\n'
    if 'event_type="raw_product_failed"' not in text:
        if old not in text:
            raise RuntimeError("reconciliation error block not found")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def patch_ingestion() -> None:
    path = ROOT / "app/services/v9_catalog_ingestion_service.py"
    text = path.read_text(encoding="utf-8")
    imp = "from app.services.operational_log_service import record_operation_event\n"
    if imp not in text:
        lines = text.splitlines(True)
        index = max((i + 1 for i, line in enumerate(lines) if line.startswith(("import ", "from "))), default=0)
        lines.insert(index, imp)
        text = "".join(lines)
    if 'source="catalog_ingestion"' not in text:
        marker = "    _append_history(row)\n"
        addition = '    record_operation_event(level=("WARNING" if row["failed_store_count"] > 0 else "INFO"), source="catalog_ingestion", event_type="plan_completed", message=f"{row[\'plan_name\']} tamamlandı: {row[\'successful_store_count\']}/{row[\'store_count\']} mağaza başarılı", details={"plan_id": row["plan_id"], "status": row["status"], "found_count": row["found_count"], "saved_count": row["saved_count"], "failed_store_count": row["failed_store_count"]})\n    _append_history(row)\n'
        if marker not in text:
            raise RuntimeError("ingestion history marker not found")
        text = text.replace(marker, addition, 1)
    path.write_text(text, encoding="utf-8")


def patch_menu() -> None:
    path = ROOT / "app/templates/base.html"
    text = path.read_text(encoding="utf-8")
    if "/admin/v10-operations" in text:
        return
    text += '\n<a style="display:none" href="/admin/v10-operations">V10 Operasyon</a>\n'
    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_main(); patch_reconciliation(); patch_ingestion(); patch_menu()
    print("V10.1 operasyon, log ve hata merkezi entegre edildi.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
