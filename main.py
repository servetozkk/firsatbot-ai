from app.web.admin_bulk_identity_routes import router as bulk_identity_router
from app.web.health_v12_routes import router as health_v12_router
from app.web.store_ecosystem_v13_routes import router as store_ecosystem_v13_router
from app.web.advanced_alert_routes import router as advanced_alert_router
from app.web.anonymous_analytics_routes import router as anonymous_analytics_router
from app.web.admin_v9_performance_routes import router as admin_v9_performance_router
from app.web.admin_v10_release_routes import router as admin_v10_release_router
from app.web.admin_v10_operations_routes import router as admin_v10_operations_router
from app.web.admin_v10_scraper_health_routes import router as admin_v10_scraper_health_router
from contextlib import asynccontextmanager
from pathlib import Path

# V16_CONSOLE_ENCODING
import sys

for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


from app.ops.runtime_crash_diagnostics_v23618 import (
    install_runtime_crash_diagnostics_v23618,
    crash_diagnostics_status_v23618,
)
install_runtime_crash_diagnostics_v23618()
from fastapi import FastAPI, Request
from app.web.admin_bulk_catalog_routes import router as admin_bulk_catalog_router
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import Response

from app.database.database import create_db
from app.scheduler import start_scheduler, stop_scheduler
from app.services.catalog_feed_v213_service import start_catalog_feed, stop_catalog_feed
from app.services.price_integrity_v219_service import audit_all_prices
from app.services.smart_catalog_refresh_v218_service import smart_refresh_product
from app.services.production_ingestion_v220_service import _deep_refresh_store_telemetry_v2347
from app.services.canonical_identity_convergence_v223_service import run_identity_convergence
from app.services.wearable_identity_convergence_v225_service import run_wearable_convergence
from app.services.canonical_alias_reliability_v227_service import audit_all_aliases
from app.services.canonical_lifecycle_v230_service import install_database_guards, lifecycle_status
from app.services.variant_referential_convergence_v236341_service import run_variant_referential_convergence_v236341
from app.services.accessory_identity_convergence_v236342_service import run_accessory_identity_convergence_v236342
from app.services.model_code_counter_integrity_v236343_service import run_model_code_counter_integrity_v236343
from app.services.source_identity_integrity_v236344_service import run_source_identity_integrity_v236344
from app.services.quarantine_lifecycle_integrity_v236345_service import run_quarantine_lifecycle_integrity_v236345
from app.services.model_code_provenance_residue_v236347_service import run_canonical_evidence_integrity_v236347
from app.services.canonical_atomic_merge_v236348_service import run_canonical_atomic_merge_v236348
from app.core.config import settings
from app.services.operational_log_service import configure_operational_logging, record_operation_event

_RUNTIME_VERSION_V236242 = "23.62.42"
_RUNTIME_VERSION_V236243 = "23.62.43"
_RUNTIME_VERSION_V236245 = "23.62.45"
_RUNTIME_VERSION_V236246 = "23.62.46"
_RUNTIME_VERSION_V236247 = "23.62.47"
_RUNTIME_VERSION_V236249 = "23.62.49"
_RUNTIME_VERSION_V236250 = "23.62.50"
_RUNTIME_VERSION_V236257 = "23.62.57"
_RUNTIME_VERSION_V236259 = "23.62.59"
_RUNTIME_VERSION_V236260 = "23.62.60"
_RUNTIME_VERSION_V236262 = "23.62.62"
_RUNTIME_VERSION_V236266 = "23.62.66"
_RUNTIME_VERSION_V236267 = "23.62.67"
_RUNTIME_VERSION_V236275 = "23.62.75"
_RUNTIME_VERSION_V236276 = "23.62.76"
_RUNTIME_VERSION_V236278 = "23.62.78"
_RUNTIME_VERSION_V236279 = "23.62.79"
_RUNTIME_VERSION_V236280 = "23.62.80"
_RUNTIME_VERSION_V236283 = "23.62.83"
_RUNTIME_VERSION_V236284 = "23.62.84"
_RUNTIME_VERSION_V236285 = "23.62.85"
_RUNTIME_VERSION_V236286 = "23.62.86"
_RUNTIME_VERSION_V236287 = "23.62.87"
_RUNTIME_VERSION_V236288 = "23.62.88"
_RUNTIME_VERSION_V236290 = "23.62.90"
_RUNTIME_VERSION_V236291 = "23.62.91"
_RUNTIME_VERSION_V236296 = "23.62.96"
_RUNTIME_VERSION_V236299 = "23.62.99"
_RUNTIME_VERSION_V236301 = "23.63.01"
_RUNTIME_VERSION_V236302 = "23.63.02"
_RUNTIME_VERSION_V236303 = "23.63.03"
_RUNTIME_VERSION_V236304 = "23.63.04"
_RUNTIME_VERSION_V236305 = "23.63.05"
_RUNTIME_VERSION_V236314 = "23.63.14"
_RUNTIME_VERSION_V236315 = "23.63.15"
_RUNTIME_VERSION_V236316 = "23.63.16"
_RUNTIME_VERSION_V236317 = "23.63.17"
_RUNTIME_VERSION_V236318 = "23.63.18"
_RUNTIME_VERSION_V236319 = "23.63.19"
_RUNTIME_VERSION_V236323 = "23.63.60"
_RUNTIME_VERSION_V236322 = "23.63.22"
_RUNTIME_VERSION_V236321 = "23.63.21"
_RUNTIME_VERSION_V236320 = "23.63.20"
_RUNTIME_VERSION_V236310 = "23.63.10"
_RUNTIME_VERSION_V236309 = "23.63.09"
_RUNTIME_VERSION_V236307 = "23.63.07"
_RUNTIME_VERSION_V236306 = "23.63.06"
_RUNTIME_VERSION_V236300 = "23.63.00"
_RUNTIME_VERSION_V236281 = "23.62.81"

from app.web.admin_routes import router as admin_router
from app.web.admin_category_routes import router as admin_category_router
from app.web.admin_catalog_scan_routes import router as admin_catalog_scan_router
from app.web.admin_v9_catalog_routes import router as admin_v9_catalog_router
from app.web.admin_v9_ingestion_routes import router as admin_v9_ingestion_router
from app.web.admin_v9_match_review_routes import router as admin_v9_match_review_router
from app.web.admin_scraper_routes import router as admin_scraper_router
from app.web.admin_platform_routes import router as admin_platform_router
from app.routes.favorites import router as favorites_router
from app.routes.price_alerts import router as price_alerts_router
from app.web.category_routes import router as category_router
from app.web.category_center_routes import router as category_center_router
from app.web.brand_center_routes import router as brand_center_router
from app.web.store_center_routes import router as store_center_router
from app.web.dashboard_routes import router as dashboard_router
from app.web.product_routes import router as product_router
from app.web.routes import router as main_router
from app.web.brand_store_routes import router as brand_store_router
from app.web.data_quality_routes import router as data_quality_router
from app.web.identity_routes import router as identity_router
from app.web.account_routes import router as account_router
from app.web.notification_routes import router as notification_router
from app.web.production_routes import router as production_router
from app.web.community_routes import router as community_router
from app.middleware.production import ProductionHeadersMiddleware
from app.middleware.api_cache import PublicApiCacheMiddleware
from app.middleware.performance import RequestTimingMiddleware
from app.middleware.security import AdminAccessMiddleware, SameOriginCSRFMiddleware, RateLimitMiddleware
from app.web.admin_v10_security_routes import router as admin_v10_security_router
from app.web.admin_v11_stable_routes import router as admin_v11_stable_router
from app.web.whatsapp_routes import router as whatsapp_router
from app.web.product_group_routes import (
    router as product_group_router,
)
from app.web.global_product_routes import router as global_product_router

from app.routes.scrape import router as scrape_router
from app.routes.comparison import router as comparison_router
from app.routes.search import router as search_router
from app.routes.history import router as history_router
from app.web.devtools_routes import router as devtools_router
from app.web.system_routes import router as system_router
from app.web.whatsapp_admin_routes import (
    router as whatsapp_admin_router,
)
from app.services.workload_priority_v23612 import user_deep_priority_snapshot_v23612, user_priority_generation_v23617



BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))





@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_operational_logging()
    record_operation_event(
        level="INFO",
        source="application",
        event_type="startup",
        message="Fırsat AI başlatılıyor.",
    )
    print("Fırsat AI başlatılıyor...")

    create_db()
    print("Veritabanı kontrol edildi ve hazırlandı.")

    try:
        convergence_boot = run_identity_convergence()
        merged_groups = int(
            convergence_boot.get("product_groups", {}).get("merged_group_count", 0) or 0
        )
        updated_groups = int(
            convergence_boot.get("product_groups", {}).get("updated_group_count", 0) or 0
        )
        merged_globals = int(
            convergence_boot.get("global_products", {}).get("merged_global_product_count", 0) or 0
        )
        updated_globals = int(
            convergence_boot.get("global_products", {}).get("updated_global_product_count", 0) or 0
        )
        print(
            "V23.13 conflict-safe canonical convergence tamamlandı. "
            f"ProductGroup güncellendi={updated_groups}, birleşti={merged_groups}; "
            f"GlobalProduct güncellendi={updated_globals}, birleşti={merged_globals}."
        )
    except Exception as convergence_error:
        print(
            "V23.13 conflict-safe canonical convergence hata verdi; "
            f"sunucu devam ediyor: {type(convergence_error).__name__}: {convergence_error}"
        )

    try:
        wearable_boot = run_wearable_convergence()
        wearable_groups = wearable_boot.get("product_groups", {})
        wearable_globals = wearable_boot.get("global_products", {})
        print(
            "V23.1 wearable identity contract convergence tamamlandı. "
            f"ProductGroup güncellendi={int(wearable_groups.get('updated_group_count', 0) or 0)}, "
            f"birleşti={int(wearable_groups.get('merged_group_count', 0) or 0)}; "
            f"GlobalProduct güncellendi={int(wearable_globals.get('updated_global_product_count', 0) or 0)}, "
            f"birleşti={int(wearable_globals.get('merged_global_product_count', 0) or 0)}."
        )
    except Exception as wearable_error:
        print(
            "V22.5 wearable identity convergence hata verdi; "
            f"sunucu devam ediyor: {type(wearable_error).__name__}: {wearable_error}"
        )

    try:
        alias_boot = audit_all_aliases()
        print(
            "V22.7 canonical alias audit tamamlandı. "
            f"GlobalProduct birleşti={len(alias_boot.get('merged_global_product_ids', []) or [])}; "
            f"ProductGroup birleşti={len(alias_boot.get('merged_product_group_ids', []) or [])}; "
            f"stale offer count düzeltildi={int(alias_boot.get('stale_active_offer_count_fixed', 0) or 0)}."
        )
    except Exception as alias_error:
        print(
            "V22.7 canonical alias audit hata verdi; "
            f"sunucu devam ediyor: {type(alias_error).__name__}: {alias_error}"
        )

    try:
        lifecycle_boot = install_database_guards()
        lifecycle_snapshot = lifecycle_status()
        print(
            "V23.0 canonical lifecycle single-source guard aktif. "
            f"mapping={int(lifecycle_snapshot.get('mapping_count', 0) or 0)}, "
            f"duplicate_group={int(lifecycle_snapshot.get('duplicate_product_group_identity_count', 0) or 0)}, "
            f"duplicate_global={int(lifecycle_snapshot.get('duplicate_global_product_identity_count', 0) or 0)}."
        )
    except Exception as lifecycle_error:
        print(
            "V23.0 canonical lifecycle guard hata verdi; "
            f"sunucu devam ediyor: {type(lifecycle_error).__name__}: {lifecycle_error}"
        )

    try:
        variant_boot = run_variant_referential_convergence_v236341()
        print(
            "V23.63.41 global variant referential convergence tamamlandı. "
            f"drift={int(variant_boot.get('checked_drift_count', 0) or 0)}, "
            f"offer={int(variant_boot.get('repaired_offer_count', 0) or 0)}, "
            f"history={int(variant_boot.get('history_relinked_count', 0) or 0)}, "
            f"unsafe={int(variant_boot.get('unsafe_count', 0) or 0)}."
        )
    except Exception as variant_error:
        print(
            "V23.63.41 variant referential convergence hata verdi; "
            f"sunucu devam ediyor: {type(variant_error).__name__}: {variant_error}"
        )

    try:
        accessory_boot = run_accessory_identity_convergence_v236342()
        print(
            "V23.63.42 accessory identity convergence tamamlandı. "
            f"candidate={int(accessory_boot.get('checked_candidate_count', 0) or 0)}, "
            f"global={int(accessory_boot.get('repaired_global_product_count', 0) or 0)}, "
            f"raw={int(accessory_boot.get('repaired_raw_product_count', 0) or 0)}, "
            f"group={int(accessory_boot.get('repaired_product_group_count', 0) or 0)}, "
            f"unsafe={int(accessory_boot.get('unsafe_count', 0) or 0)}."
        )
    except Exception as accessory_error:
        print(
            "V23.63.42 accessory identity convergence hata verdi; "
            f"sunucu devam ediyor: {type(accessory_error).__name__}: {accessory_error}"
        )

    try:
        integrity_boot = run_model_code_counter_integrity_v236343()
        print(
            "V23.63.43 model-code/counter integrity tamamlandı. "
            f"gp_model={int(integrity_boot.get('global_product_model_code_fixed', 0) or 0)}, "
            f"variant_model={int(integrity_boot.get('variant_model_code_fixed', 0) or 0)}, "
            f"raw_counter={int(integrity_boot.get('raw_product_counter_fixed', 0) or 0)}, "
            f"offer_counter={int(integrity_boot.get('active_offer_counter_fixed', 0) or 0)}, "
            f"affected={int(integrity_boot.get('affected_global_product_count', 0) or 0)}."
        )
    except Exception as integrity_error:
        print(
            "V23.63.43 model-code/counter integrity hata verdi; "
            f"sunucu devam ediyor: {type(integrity_error).__name__}: {integrity_error}"
        )

    try:
        source_identity_boot = run_source_identity_integrity_v236344()
        print(
            "V23.63.44 source/canonical identity integrity tamamlandı. "
            f"checked={int(source_identity_boot.get('checked_link_count', 0) or 0)}, "
            f"raw={int(source_identity_boot.get('quarantined_raw_count', 0) or 0)}, "
            f"offer={int(source_identity_boot.get('quarantined_offer_count', 0) or 0)}, "
            f"already={int(source_identity_boot.get('already_quarantined_count', 0) or 0)}, "
            f"counter={int(source_identity_boot.get('counter_reconciled_product_count', 0) or 0)}."
        )
    except Exception as source_identity_error:
        print(
            "V23.63.44 source/canonical identity integrity hata verdi; "
            f"sunucu devam ediyor: {type(source_identity_error).__name__}: {source_identity_error}"
        )

    try:
        price_integrity_boot = audit_all_prices()
        quarantined_count = int(price_integrity_boot.get("quarantined_offer_count", 0) or 0)
        print(
            f"V21.9 fiyat bütünlüğü başlangıç denetimi tamamlandı. "
            f"Karantina: {quarantined_count}."
        )
    except Exception as price_integrity_error:
        print(
            "V21.9 fiyat bütünlüğü başlangıç denetimi hata verdi; "
            f"sunucu devam ediyor: {type(price_integrity_error).__name__}: {price_integrity_error}"
        )

    try:
        quarantine_boot = run_quarantine_lifecycle_integrity_v236345()
        print(
            "V23.63.45 quarantine lifecycle convergence tamamlandı. "
            f"total={int(quarantine_boot.get('quarantined_offer_count', 0) or 0)}, "
            f"offer={int(quarantine_boot.get('offer_state_fixed_count', 0) or 0)}, "
            f"legacy={int(quarantine_boot.get('legacy_state_fixed_count', 0) or 0)}, "
            f"counter={int(quarantine_boot.get('active_offer_counter_fixed_count', 0) or 0)}, "
            f"affected={int(quarantine_boot.get('affected_global_product_count', 0) or 0)}."
        )
    except Exception as quarantine_error:
        print(
            "V23.63.45 quarantine lifecycle convergence hata verdi; "
            f"sunucu devam ediyor: {type(quarantine_error).__name__}: {quarantine_error}"
        )

    try:
        evidence_boot = run_canonical_evidence_integrity_v236347()
        print(
            "V23.63.47 model-code provenance residue cleanup tamamlandı. "
            f"gp_model={int(evidence_boot.get('global_product_model_code_fixed', 0) or 0)}, "
            f"variant_model={int(evidence_boot.get('variant_model_code_fixed', 0) or 0)}, "
            f"duplicates={int(evidence_boot.get('duplicate_candidate_group_count', 0) or 0)}, "
            f"auto_merge={int(evidence_boot.get('automatic_merge_count', 0) or 0)}, "
            f"affected={int(evidence_boot.get('affected_global_product_count', 0) or 0)}."
        )
    except Exception as evidence_error:
        print(
            "V23.63.47 model-code provenance residue cleanup hata verdi; "
            f"sunucu devam ediyor: {type(evidence_error).__name__}: {evidence_error}"
        )

    try:
        merge_boot = run_canonical_atomic_merge_v236348()
        print(
            "V23.63.48 atomic canonical convergence tamamlandı. "
            f"merged={int(merge_boot.get('merged_pair_count', 0) or 0)}, "
            f"skipped={int(merge_boot.get('already_or_skipped_pair_count', 0) or 0)}, "
            f"collapse={int(merge_boot.get('variant_collapse_count', 0) or 0)}, "
            f"rewrite={int(merge_boot.get('variant_key_rewrite_count', 0) or 0)}, "
            f"gp={int(merge_boot.get('global_product_count', 0) or 0)}, "
            f"variant={int(merge_boot.get('global_variant_count', 0) or 0)}."
        )
    except Exception as merge_error:
        print(
            "V23.63.48 atomic canonical convergence hata verdi; rollback uygulandı; "
            f"sunucu devam ediyor: {type(merge_error).__name__}: {merge_error}"
        )

    if settings.enable_scheduler:
        await start_scheduler()
    else:
        print("Kategori scheduler devre dışı (ENABLE_SCHEDULER=0).")

    await start_catalog_feed(
        enabled=settings.catalog_feed_enabled,
        interval_minutes=settings.catalog_feed_interval_minutes,
        initial_delay_seconds=settings.catalog_feed_initial_delay_seconds,
        batch_size=settings.catalog_feed_batch_size,
        stale_hours=settings.catalog_feed_stale_hours,
    )

    try:
        yield
    finally:
        record_operation_event(
            level="INFO",
            source="application",
            event_type="shutdown",
            message="Fırsat AI kapatılıyor.",
        )
        print("Fırsat AI kapatılıyor...")
        await stop_catalog_feed()
        if settings.enable_scheduler:
            await stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)


app.add_middleware(PublicApiCacheMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=700)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SameOriginCSRFMiddleware)
app.add_middleware(AdminAccessMiddleware)
app.add_middleware(RequestTimingMiddleware)
app.add_middleware(ProductionHeadersMiddleware)

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


from app.web.beta_readiness_routes import router as beta_readiness_router
from app.web.public_beta_routes import router as public_beta_router
from app.web.production_release_v14_routes import router as production_release_v14_router

from app.web.scraper_operations_routes import router as scraper_operations_router

from app.web.global_marketplace_v14_routes import router as global_marketplace_v14_router
from app.web.ai_comparison_v14_routes import router as ai_comparison_v14_router
from app.web.live_price_refresh_v14_routes import router as live_price_refresh_v14_router
from app.web.multi_store_offer_repair_v14_routes import router as multi_store_offer_repair_v14_router
from app.web.price_comparison_v21_routes import router as price_comparison_v21_router
from app.web.catalog_feed_v213_routes import router as catalog_feed_v213_router
from app.web.catalog_feed_v217_routes import router as catalog_feed_v217_router
from app.web.catalog_feed_v218_routes import router as catalog_feed_v218_router
from app.web.price_integrity_v219_routes import router as price_integrity_v219_router
from app.web.production_ingestion_v220_routes import router as production_ingestion_v220_router
from app.web.canonical_identity_convergence_v223_routes import router as canonical_identity_convergence_v223_router
from app.web.wearable_identity_v225_routes import router as wearable_identity_v225_router
from app.web.store_offer_reliability_v226_routes import router as store_offer_reliability_v226_router
from app.web.canonical_alias_v227_routes import router as canonical_alias_v227_router
from app.web.canonical_lifecycle_v230_routes import router as canonical_lifecycle_v230_router
from app.web.ingestion_observability_v224_routes import router as ingestion_observability_v224_router
from app.web.bulk_ingestion_v232_routes import router as bulk_ingestion_v232_router
from app.web.production_stress_v238_routes import router as production_stress_v238_router
from app.web.admin_module_center_v14_routes import router as admin_module_center_v14_router

# Routerlar
from app.web.api_cache_routes import router as api_cache_router
from app.web.image_optimization_routes import router as image_optimization_router
from app.web.smart_search_routes import router as smart_search_router
from app.web.campaign_center_routes import router as campaign_center_router
from app.web.coupon_center_routes import router as coupon_center_router
from app.web.stock_tracking_routes import router as stock_tracking_router
from app.web.new_products_routes import router as new_products_router
from app.web.sitemap_routes import router as sitemap_router
from app.web.landing_page_routes import router as landing_page_router
from app.web.performance_v13_routes import router as performance_v13_router
from app.web.catalog_scaling_routes import router as catalog_scaling_router
app.include_router(global_marketplace_v14_router)
app.include_router(ai_comparison_v14_router)
app.include_router(live_price_refresh_v14_router)
app.include_router(multi_store_offer_repair_v14_router)
app.include_router(price_comparison_v21_router)
app.include_router(catalog_feed_v213_router)
app.include_router(catalog_feed_v217_router)
app.include_router(catalog_feed_v218_router)
app.include_router(price_integrity_v219_router)
app.include_router(production_ingestion_v220_router)
app.include_router(canonical_identity_convergence_v223_router)
app.include_router(wearable_identity_v225_router)
app.include_router(store_offer_reliability_v226_router)
app.include_router(canonical_alias_v227_router)
app.include_router(canonical_lifecycle_v230_router)
app.include_router(ingestion_observability_v224_router)
app.include_router(bulk_ingestion_v232_router)
app.include_router(production_stress_v238_router)
app.include_router(admin_module_center_v14_router)
app.include_router(scraper_operations_router)
app.include_router(api_cache_router)
app.include_router(image_optimization_router)
app.include_router(smart_search_router)
app.include_router(campaign_center_router)
app.include_router(coupon_center_router)
app.include_router(stock_tracking_router)
app.include_router(new_products_router)
app.include_router(sitemap_router)
app.include_router(landing_page_router)
app.include_router(performance_v13_router)
app.include_router(catalog_scaling_router)
app.include_router(store_ecosystem_v13_router)
app.include_router(advanced_alert_router)
app.include_router(anonymous_analytics_router)
app.include_router(beta_readiness_router)
app.include_router(public_beta_router)
app.include_router(production_release_v14_router)
app.include_router(admin_router)
app.include_router(admin_category_router)
app.include_router(admin_catalog_scan_router)
app.include_router(admin_v9_catalog_router)
app.include_router(admin_v9_ingestion_router)
app.include_router(admin_v9_match_review_router)
app.include_router(admin_scraper_router)
app.include_router(admin_platform_router)
app.include_router(product_group_router)
app.include_router(global_product_router)
app.include_router(main_router)
app.include_router(brand_store_router)
app.include_router(data_quality_router)
app.include_router(identity_router)
app.include_router(account_router)
app.include_router(notification_router)
app.include_router(production_router)
app.include_router(community_router)
app.include_router(category_router)
app.include_router(category_center_router)
app.include_router(brand_center_router)
app.include_router(store_center_router)
app.include_router(dashboard_router)
app.include_router(product_router)
app.include_router(whatsapp_router)
app.include_router(scrape_router)
app.include_router(comparison_router)
app.include_router(search_router)
app.include_router(history_router)
app.include_router(whatsapp_admin_router)
app.include_router(favorites_router)
app.include_router(price_alerts_router)
app.include_router(devtools_router)
app.include_router(system_router)
app.include_router(admin_v9_performance_router)
app.include_router(admin_v10_release_router)
app.include_router(admin_v10_operations_router)
app.include_router(admin_v10_scraper_health_router)
app.include_router(admin_v10_security_router)
app.include_router(admin_v11_stable_router)
app.include_router(health_v12_router)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }

@app.get("/service-worker.js", include_in_schema=False)
def service_worker() -> Response:
    path = STATIC_DIR / "service-worker.js"
    return Response(path.read_text(encoding="utf-8"), media_type="application/javascript", headers={"Service-Worker-Allowed": "/"})




app.include_router(admin_bulk_catalog_router)

app.include_router(bulk_identity_router)



@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    from fastapi.responses import JSONResponse

    if request.url.path.startswith("/api/"):
        detail = getattr(exc, "detail", None) or "API endpoint bulunamadı."
        return JSONResponse(
            status_code=404,
            content={
                "detail": detail,
                "method": request.method,
                "path": request.url.path,
                "runtime_version": _runtime_version(),
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "request": request,
            "status_code": 404,
            "icon": "🔎",
            "heading": "Aradığın sayfa bulunamadı",
            "message": "Bağlantı değişmiş veya içerik kaldırılmış olabilir.",
        },
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    from fastapi.responses import JSONResponse

    record_operation_event(
        level="ERROR",
        source="http",
        event_type="unhandled_exception",
        message=f"{type(exc).__name__}: {exc}",
        details={"method": request.method, "path": request.url.path},
    )

    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Sunucu işlemi tamamlayamadı.",
                "error_type": type(exc).__name__,
                "method": request.method,
                "path": request.url.path,
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "request": request,
            "status_code": 500,
            "icon": "⚠️",
            "heading": "Geçici bir sorun oluştu",
            "message": "İşlemi tamamlayamadık. Biraz sonra tekrar deneyebilirsin.",
        },
        status_code=500,
    )


# V14_7_0_DIRECT_MODULE_CENTER_ROUTE
@app.get("/admin/module-center", include_in_schema=False)
def direct_admin_module_center(request: Request):
    from app.web.admin_module_center_v14_routes import discover_admin_modules

    groups = discover_admin_modules(request)
    module_count = sum(len(items) for items in groups.values())

    return templates.TemplateResponse(
        request=request,
        name="admin_module_center_v14.html",
        context={
            "groups": groups,
            "module_count": module_count,
        },
    )







# V14_9_2_DIRECT_GLOBAL_MARKETPLACE_ROUTE
@app.middleware("http")
async def legacy_global_product_slug_redirect(request, call_next):
    import re
    from fastapi.responses import RedirectResponse

    path = request.url.path
    match = re.fullmatch(r"/fiyat-karsilastirma/(\d+)-(.+)", path)
    if match:
        return RedirectResponse(
            url=f"/fiyat-karsilastirma/global/{match.group(1)}-{match.group(2)}",
            status_code=301,
        )

    return await call_next(request)


@app.get(
    "/fiyat-karsilastirma/global/{product_ref}",
    include_in_schema=False,
)
def direct_global_marketplace_product(request: Request, product_ref: str):
    import re
    from pathlib import Path
    from fastapi import HTTPException
    from fastapi.responses import RedirectResponse
    from fastapi.templating import Jinja2Templates

    from app.services.ai_comparison_v14_service import analyze_global_product
    from app.services.global_price_experience_v14_service import get_price_history
    from app.services.global_marketplace_v14_service import get_global_product

    match = re.match(r"^\s*(\d+)(?:-|$)", str(product_ref or ""))
    if not match:
        raise HTTPException(
            status_code=404,
            detail="Ürün adresinden geçerli global ürün kimliği çıkarılamadı",
        )

    product_id = int(match.group(1))
    product = get_global_product(product_id)
    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Global ürün veya aktif teklif bulunamadı",
        )

    canonical_path = (
        f"/fiyat-karsilastirma/global/{product_id}-{product['slug']}"
    )
    if request.url.path != canonical_path:
        return RedirectResponse(url=canonical_path, status_code=301)

    product["ai_insight"] = analyze_global_product(product_id)
    product["price_history"] = get_price_history(product_id, days=90)

    local_templates = Jinja2Templates(
        directory=str(Path(__file__).resolve().parent / "app" / "templates")
    )

    return local_templates.TemplateResponse(
        request=request,
        name="global_marketplace_product_v14.html",
        context={
            "product": product,
            "seo_title": (
                f"{product['canonical_name']} Fiyatları "
                "ve Mağaza Karşılaştırması"
            ),
            "seo_description": (
                f"{product['canonical_name']} için "
                f"{product['store_count']} mağazadaki fiyatları karşılaştırın."
            ),
            "canonical_url": (
                str(request.base_url).rstrip("/") + canonical_path
            ),
        },
    )

# V16_RUNTIME_IDENTITY
def _runtime_version() -> str:
    version_path = BASE_DIR / "VERSION"
    return (
        version_path.read_text(encoding="utf-8").strip()
        if version_path.exists()
        else "UNKNOWN"
    )


@app.get("/api/runtime-identity/v16", include_in_schema=False)
def runtime_identity_v16():
    target = "/api/multi-store-repair/v14/products/{global_product_id}"
    routes = [
        {
            "path": getattr(route, "path", None),
            "methods": sorted(getattr(route, "methods", set()) or set()),
            "name": getattr(route, "name", None),
        }
        for route in app.routes
        if getattr(route, "path", None) in {
            "/admin/multi-store-repair",
            target,
        }
    ]
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "project_root": str(BASE_DIR),
        "main_file": str(Path(__file__).resolve()),
        "multi_store_routes": routes,
    }



# V17_RUNTIME_IDENTITY_ALIAS
@app.get("/api/runtime-identity/v17", include_in_schema=False)
def runtime_identity_v17():
    return runtime_identity_v16()


@app.get("/api/runtime-identity/v18", include_in_schema=False)
def runtime_identity_v18():
    from pathlib import Path
    root = Path(__file__).resolve().parent
    return {
        "ok": True,
        "runtime_version": (root / "VERSION").read_text(encoding="utf-8").strip(),
        "project_root": str(root),
        "candidate_engine": "v18-search-result-prefilter",
    }


@app.get("/api/runtime-identity/v182", include_in_schema=False)
def runtime_identity_v181():
    from pathlib import Path
    project_root = Path(__file__).resolve().parent
    return {
        "ok": True,
        "runtime_version": (
            project_root / "VERSION"
        ).read_text(encoding="utf-8").strip(),
        "project_root": str(project_root),
        "candidate_engine": "v18.2-card-url-resolution-prefilter",
        "detail_candidate_limit_per_store": 1,
    }

@app.get("/api/runtime-identity/v183", include_in_schema=False)
def runtime_identity_v183():
    from pathlib import Path
    project_root = Path(__file__).resolve().parent
    return {
        "ok": True,
        "runtime_version": (project_root / "VERSION").read_text(encoding="utf-8").strip(),
        "project_root": str(project_root),
        "candidate_engine": "v18.3-prefilter-direct-handoff",
        "detail_candidate_limit_per_store": 1,
        "legacy_second_url_filter": False,
    }

# V18_4_RUNTIME_IDENTITY
@app.get("/api/runtime-identity/v184", include_in_schema=False)
def runtime_identity_v184():
    return {
        "ok": True,
        "runtime_version": "18.4.0",
        "candidate_engine": "v18.4-gaminggen-teknosa-normalization",
        "gaminggen_product_only": True,
        "teknosa_store_suffix_normalization": True,
    }

@app.get("/api/runtime-identity/v185", include_in_schema=False)
def runtime_identity_v185():
    return {
        "ok": True,
        "runtime_version": "18.5.0",
        "candidate_engine": "v18.5-teknosa-gaminggen-store-fix",
        "teknosa_a_suffix_digits": "1-3",
        "teknosa_storage_conflict_gate": True,
        "gaminggen_product_only": True,
    }

# V18_6_STORE_ADAPTER_RUNTIME
@app.get("/api/runtime-identity/v186", include_in_schema=False)
def runtime_identity_v186():
    from pathlib import Path
    from app.stores.adapters import StoreAdapterRegistry

    return {
        "ok": True,
        "runtime_version": (Path(__file__).resolve().parent / "VERSION").read_text(encoding="utf-8").strip(),
        "candidate_engine": "v18.6-store-adapter-registry",
        "registered_adapters": list(StoreAdapterRegistry.registered_codes()),
        "legacy_store_fallback": True,
    }
# V18_7_IDENTITY_V3_HEPSIBURADA_SESSION_RUNTIME
@app.get("/api/runtime-identity/v187", include_in_schema=False)
def runtime_identity_v187():
    from pathlib import Path
    return {
        "ok": True,
        "runtime_version": (Path(__file__).resolve().parent / "VERSION").read_text(encoding="utf-8").strip(),
        "identity_engine": "v3-brand-family-variant-hardware",
        "hepsiburada_security_strategy": "persistent-session-retry",
        "security_retry_attempts": 3,
    }

# V19_0_RUNTIME_IDENTITY
@app.get("/api/runtime-identity/v19", include_in_schema=False)
def runtime_identity_v19():
    return {
        "ok": True,
        "runtime_version": "19.0.0",
        "repair_strategy": "single-target-no-recursive-scan",
        "hepsiburada_strategy": "single-persistent-profile-fail-fast",
        "recursive_auto_scan": False,
    }

@app.get("/api/runtime-identity/v191", include_in_schema=False)
def runtime_identity_v191():
    return {
        "ok": True,
        "runtime_version": "19.1.0",
        "catalog_binding": "preferred-target-before-save",
        "duplicate_global_prevention": True,
        "canonical_test_product_id": 125,
    }

# V19_2_PRODUCT_GROUP_CANONICAL_RUNTIME
@app.get("/api/runtime-identity/v192", include_in_schema=False)
def runtime_identity_v192():
    return {
        "ok": True,
        "runtime_version": "19.2.0",
        "product_group_strategy": "single-identity-v3-canonical-group",
        "product_group_duplicate_prevention": True,
        "legacy_log_labels": False,
        "canonical_test_product_id": 125,
    }

# V19_3_STORE_ADAPTER_HTML_FALLBACK
@app.get("/api/runtime-identity/v193", include_in_schema=False)
def runtime_identity_v193():
    from app.stores.adapters import StoreAdapterRegistry
    return {
        "ok": True,
        "runtime_version": "19.3.0",
        "store_adapter_strategy": "dom-plus-html-hydration-fallback",
        "registered_adapters": list(StoreAdapterRegistry.registered_codes()),
        "target_stores": ["amazon", "teknosa", "mediamarkt", "n11"],
        "legacy_store_fallback": True,
    }



# V19_4_HTML_CONTEXT_ENRICHMENT
@app.get("/api/runtime-identity/v194", include_in_schema=False)
def runtime_identity_v194():
    from app.stores.adapters import StoreAdapterRegistry
    return {
        "ok": True,
        "runtime_version": "19.4.0",
        "store_adapter_strategy": "dom-plus-enriched-html-context",
        "html_context_fields": [
            "productName", "name", "title", "alt", "aria-label",
            "description", "model", "url-slug"
        ],
        "rejected_candidate_debug_limit": 5,
        "registered_adapters": list(StoreAdapterRegistry.registered_codes()),
        "target_stores": ["amazon", "teknosa", "mediamarkt", "n11"],
    }

# V20_IDENTITY_LEVELS
@app.get("/api/runtime-identity/v20", include_in_schema=False)
def runtime_identity_v20():
    return {
        "ok": True,
        "runtime_version": "20.0.0",
        "identity_engine": "v4-three-level-safe-matching",
        "level_1": "family-plus-exact-variant",
        "level_2": "family-plus-exact-cpu-ram-storage",
        "level_3": "same-family-different-configuration-rejected",
        "store_sku_is_identity": False,
    }



@app.get("/api/runtime-identity/v202", include_in_schema=False)
def runtime_identity_v202():
    return {
        "ok": True,
        "runtime_version": "20.2.0",
        "teknosa_suffix_strategy": "full-store-sku-not-single-letter",
        "hepsiburada_session_strategy": "locked-persistent-profile-metadata",
        "field_diagnostics": True,
        "storage_requires_storage_token": True,
        "security_bypass": False,
    }


@app.get("/api/runtime-identity/v203", include_in_schema=False)
def runtime_identity_v203():
    return {
        "ok": True,
        "runtime_version": "20.3.0",
        "identity_engine": "v4-level2-evidence-enhanced",
        "level2_evidence": ["family", "cpu", "ram", "storage"],
        "teknosa_detail_fallback": True,
        "field_diagnostics": True,
        "storage_requires_storage_token": True,
        "security_bypass": False,
    }


@app.get("/api/runtime-identity/v205", include_in_schema=False)
def runtime_identity_v204():
    return {
        "ok": True,
        "runtime_version": "20.5.0",
        "identity_engine": "v4-explicit-ram-storage-field-isolation",
        "teknosa_ram_storage_sources": ["json-ld", "hydration-json", "spec-table", "page-text", "url-slug"],
        "field_diagnostics": True,
        "storage_requires_storage_token": True,
        "security_bypass": False,
    }


@app.get("/api/runtime-identity/v207", include_in_schema=False)
def runtime_identity_v206():
    return {
        "ok": True,
        "runtime_version": "20.7.0",
        "identity_engine": "v4-central-store-sku-parser-v2",
        "similarity_basis": ["brand", "series", "family", "cpu", "ram", "storage"],
        "store_sku_parser": "central-family-suffix-split",
        "store_sku_excluded_from_similarity": True,
        "technical_conflict_rejection": True,
        "security_bypass": False,
    }


@app.get("/api/runtime-identity/v208")
def runtime_identity_v208():
    return {"ok": True, "runtime_version": "20.8.0"}


# V20_9_HEPSIBURADA_PERSISTENT_SESSION_MANAGER
@app.get("/api/runtime-identity/v209")
def runtime_identity_v209():
    return {
        "ok": True,
        "runtime_version": "20.9.0",
        "hepsiburada_session_strategy": "persistent-profile-short-challenge-check",
        "profile_directory": ".playwright-hepsiburada-profile",
        "security_result": "SECURITY_CHALLENGE",
        "security_bypass": False,
        "canonical_identity_pipeline": "v20.8-preserved",
        "canonical_test_product_id": 125,
    }


# V21_0_PRICE_COMPARISON_CORE
@app.get("/api/runtime-identity/v210")
def runtime_identity_v210():
    return {
        "ok": True,
        "runtime_version": "21.0.0",
        "architecture": "global-product-variant-store-offer-price-history",
        "serving_mode": "catalog-first-no-live-scrape",
        "production_read_api": "/api/price-comparison/v21/products/{global_product_id}",
        "catalog_search_api": "/api/price-comparison/v21/search?q=...",
        "repair_tool": "/api/multi-store-repair/v14/products/{global_product_id}",
        "canonical_identity_pipeline": "v20.8-preserved",
        "hepsiburada_session_manager": "v20.9-preserved",
        "canonical_test_product_id": 125,
    }


# V21_1_PRICE_COMPARISON_UI
@app.get("/api/runtime-identity/v211")
def runtime_identity_v211():
    return {
        "ok": True,
        "runtime_version": "21.1.0",
        "architecture": "global-product-variant-store-offer-price-history",
        "serving_mode": "catalog-first-no-live-scrape",
        "comparison_ui": "/fiyat-karsilastirma",
        "product_ui": "/fiyat-karsilastirma/urun/{global_product_id}",
        "production_read_api": "/api/price-comparison/v21/products/{global_product_id}",
        "catalog_search_api": "/api/price-comparison/v21/search?q=...",
        "repair_tool": "/api/multi-store-repair/v14/products/{global_product_id}",
        "canonical_identity_pipeline": "v20.8-preserved",
        "hepsiburada_session_manager": "v20.9-preserved",
        "canonical_test_product_id": 125,
    }


# V21_2_PRODUCT_DETAIL_PRICE_COMPARISON_CORE
@app.get("/api/runtime-identity/v212")
def runtime_identity_v212():
    return {
        "ok": True,
        "runtime_version": "21.2.0",
        "architecture": "global-product-variant-store-offer-price-history",
        "serving_mode": "catalog-first-no-live-scrape",
        "primary_ui": "/karsilastir/{identity_key}",
        "integration": "existing-product-detail-page",
        "offer_source": "GlobalOffer",
        "freshness_policy": "fresh-first-then-last-known-active",
        "repair_tool": "/api/multi-store-repair/v14/products/{global_product_id}",
        "canonical_identity_pipeline": "v20.8-preserved",
        "hepsiburada_session_manager": "v20.9-preserved",
        "canonical_test_product_id": 125,
    }


# V21_3_CATALOG_FEED_ENGINE
@app.get("/api/runtime-identity/v213")
def runtime_identity_v213():
    return {
        "ok": True,
        "runtime_version": "21.3.0",
        "architecture": "global-product-variant-store-offer-price-history",
        "serving_mode": "catalog-first-no-live-scrape",
        "primary_ui": "/karsilastir/{identity_key}",
        "catalog_feed_engine": "enabled",
        "catalog_feed_status": "/api/catalog-feed/v213/status",
        "catalog_feed_run": "/api/catalog-feed/v213/run",
        "catalog_feed_product_refresh": "/api/catalog-feed/v213/products/{global_product_id}/refresh",
        "feed_policy": "weak-coverage-and-stale-first",
        "failure_isolation": "per-product-and-per-store",
        "offer_source": "GlobalOffer",
        "canonical_identity_pipeline": "v20.8-preserved",
        "hepsiburada_session_manager": "v20.9-preserved",
        "canonical_test_product_id": 125,
    }

# V21_4_STORE_COVERAGE_ENGINE
@app.get("/api/runtime-identity/v214")
def runtime_identity_v214():
    return {
        "ok": True,
        "runtime_version": "21.4.0",
        "architecture": "global-product-variant-store-offer-price-history",
        "serving_mode": "catalog-first-no-live-scrape",
        "primary_ui": "/karsilastir/{identity_key}",
        "catalog_feed_engine": "v21.3-preserved",
        "store_coverage_engine": "enabled",
        "query_policy": "canonical-short-query-first-with-store-aware-fallback",
        "candidate_policy": "top-3-prefiltered-then-strict-technical-gates",
        "vatan_path_encoding": "percent-encoded",
        "registered_adapters": "amazon,n11,pazarama,idefix,teknosa,mediamarkt,vatan,itopya,incehesap,gaminggen",
        "catalog_feed_status": "/api/catalog-feed/v213/status",
        "catalog_feed_product_refresh": "/api/catalog-feed/v213/products/{global_product_id}/refresh",
        "canonical_identity_pipeline": "v20.8-preserved",
        "hepsiburada_session_manager": "v20.9-preserved",
        "canonical_test_product_id": 125,
    }



# V21_5_VARIANT_FIRST_STORE_DISCOVERY
@app.get("/api/runtime-identity/v215")
def runtime_identity_v215():
    return {
        "ok": True,
        "runtime_version": "21.5.0",
        "architecture": "global-product-variant-store-offer-price-history",
        "serving_mode": "catalog-first-no-live-scrape",
        "primary_ui": "/karsilastir/{identity_key}",
        "catalog_feed_engine": "v21.3-preserved",
        "store_coverage_engine": "v21.4-preserved",
        "variant_first_discovery": "enabled",
        "variant_policy": "explicit-url-or-title-variant-wins-over-card-context",
        "candidate_policy": "different-explicit-variant-rejected-before-detail-scrape",
        "n11_security_policy": "persistent-profile-single-short-check-then-security-challenge",
        "n11_verification_wait_seconds": 3,
        "catalog_feed_status": "/api/catalog-feed/v213/status",
        "catalog_feed_product_refresh": "/api/catalog-feed/v213/products/{global_product_id}/refresh",
        "canonical_identity_pipeline": "v20.8-preserved",
        "hepsiburada_session_manager": "v20.9-preserved",
        "canonical_test_product_id": 125,
    }


# V21_6_PRODUCT_TYPE_DISCOVERY_QUALITY_GATES
@app.get("/api/runtime-identity/v216")
def runtime_identity_v216():
    return {
        "ok": True,
        "runtime_version": "21.6.0",
        "architecture": "global-product-variant-store-offer-price-history",
        "serving_mode": "catalog-first-no-live-scrape",
        "primary_ui": "/karsilastir/{identity_key}",
        "catalog_feed_engine": "v21.3-preserved",
        "store_coverage_engine": "v21.4-preserved",
        "variant_first_discovery": "v21.5-preserved",
        "discovery_quality_gates": "enabled",
        "product_type_gate": "accessories-rejected-before-detail-scrape",
        "family_gate": "explicit-different-family-rejected-before-detail-scrape",
        "candidate_budget": "quality-gated-top-3",
        "pazarama_security_policy": "persistent-profile-single-short-check-then-security-challenge",
        "pazarama_verification_wait_seconds": 3,
        "n11_security_policy": "v21.5-preserved",
        "catalog_feed_status": "/api/catalog-feed/v213/status",
        "catalog_feed_product_refresh": "/api/catalog-feed/v213/products/{global_product_id}/refresh",
        "canonical_identity_pipeline": "v20.8-preserved",
        "hepsiburada_session_manager": "v20.9-preserved",
        "canonical_test_product_id": 125,
    }


# V21_7_SMART_CATALOG_REFRESH_OFFER_RETENTION
@app.get("/api/runtime-identity/v217")
def runtime_identity_v217():
    return {
        "ok": True,
        "runtime_version": "21.7.0",
        "architecture": "global-product-variant-store-offer-price-history",
        "serving_mode": "catalog-first-no-live-scrape",
        "primary_ui": "/karsilastir/{identity_key}",
        "catalog_feed_engine": "v21.3-preserved",
        "store_coverage_engine": "v21.4-preserved",
        "variant_first_discovery": "v21.5-preserved",
        "discovery_quality_gates": "v21.6-preserved",
        "smart_catalog_refresh": "enabled",
        "store_backoff_policy": "success-30m,product-not-found-12h,security-challenge-6h,error-2h",
        "offer_retention": "existing-active-offers-preserved-on-refresh-failure",
        "smart_feed_status": "/api/catalog-feed/v217/status?global_product_id=125",
        "smart_product_refresh": "/api/catalog-feed/v217/products/{global_product_id}/refresh",
        "force_refresh": "/api/catalog-feed/v217/products/{global_product_id}/refresh?force=true",
        "legacy_feed_api": "/api/catalog-feed/v213",
        "canonical_identity_pipeline": "v20.8-preserved",
        "canonical_test_product_id": 125,
    }


# V21_8_OFFER_LIFECYCLE_STORE_STATE_CONSISTENCY
@app.get("/api/runtime-identity/v218")
def runtime_identity_v218():
    return {
        "ok": True,
        "runtime_version": "21.8.0",
        "architecture": "global-product-variant-store-offer-price-history",
        "serving_mode": "catalog-first-no-live-scrape",
        "primary_ui": "/karsilastir/{identity_key}",
        "smart_catalog_refresh": "v21.7-preserved-and-lifecycle-hardened",
        "offer_lifecycle_store_state_consistency": "enabled",
        "crawler_state_separation": "crawler-failure-does-not-deactivate-last-known-active-offer",
        "data_continuity": "auto-import-richer-previous-version-sqlite-before-startup",
        "legacy_offer_recovery": "existing-raw-and-active-productoffer-can-rebuild-missing-globaloffer",
        "tracked_vs_searchable_stores": "separate",
        "smart_feed_status": "/api/catalog-feed/v218/status?global_product_id=125",
        "smart_product_refresh": "/api/catalog-feed/v218/products/{global_product_id}/refresh",
        "force_refresh": "/api/catalog-feed/v218/products/{global_product_id}/refresh?force=true",
        "legacy_v217_api": "/api/catalog-feed/v217",
        "canonical_identity_pipeline": "v20.8-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v219", tags=["Runtime Identity"])
def runtime_identity_v219():
    return {
        "ok": True,
        "runtime_version": "21.9.0",
        "architecture": "global-product-variant-store-offer-price-history",
        "serving_mode": "catalog-first-no-live-scrape",
        "primary_ui": "/karsilastir/{identity_key}",
        "offer_lifecycle_store_state_consistency": "v21.8-preserved",
        "price_integrity_quarantine_engine": "enabled",
        "price_policy": "peer-median-conservative-quarantine",
        "quarantine_policy": "suspect-offer-retained-in-db-but-excluded-from-serving-best-price-and-ai",
        "teknosa_price_parser_guard": "laptop-low-price-dominant-page-price-recheck",
        "price_integrity_status": "/api/price-integrity/v219/products/{global_product_id}",
        "price_integrity_audit": "/api/price-integrity/v219/products/{global_product_id}/audit",
        "smart_feed_status": "/api/catalog-feed/v218/status?global_product_id=125",
        "canonical_identity_pipeline": "v20.8-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v220")
def runtime_identity_v220():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "production-product-ingestion-pipeline",
        "serving_mode": "catalog-first-no-live-scrape",
        "production_product_ingestion": "enabled",
        "source_pipeline": "scrape-canonical-identity-global-product-source-offer",
        "store_pipeline": "smart-refresh-strict-match-global-offer",
        "price_integrity": "v21.9-preserved-and-final-audit",
        "offer_lifecycle": "v21.8-preserved",
        "legacy_auto_repair_during_ingestion": "disabled-to-prevent-duplicate-store-scans",
        "ingestion_api": "/api/product-ingestion/v220/products",
        "ingestion_task": "/api/product-ingestion/v220/tasks/{task_id}",
        "canonical_identity_pipeline": "v20.8-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v221")
def runtime_identity_v221():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "production-product-ingestion-category-aware-matching",
        "serving_mode": "catalog-first-no-live-scrape",
        "production_product_ingestion": "v22.0-preserved",
        "category_aware_identity_matching": "enabled",
        "phone_query_policy": "brand-family-variant-storage-no-ram-no-ssd-wording",
        "phone_match_policy": "brand-family-variant-storage-strict",
        "phone_ram_policy": "not-a-required-cross-store-match-gate",
        "laptop_match_policy": "v17-strict-matcher-preserved",
        "discovery_quality_gates": "v21.6-preserved",
        "price_integrity": "v21.9-preserved",
        "offer_lifecycle": "v21.8-preserved",
        "ingestion_api": "/api/product-ingestion/v220/products",
        "canonical_identity_pipeline": "v20.8-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v222")
def runtime_identity_v222():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "production-ingestion-semantic-price-challenge-classifier",
        "serving_mode": "catalog-first-no-live-scrape",
        "production_product_ingestion": "v22.0-preserved",
        "category_aware_identity_matching": "v22.1-preserved",
        "semantic_price_parser": "enabled",
        "price_context_policy": "installment-credit-monthly-values-not-sale-price",
        "teknosa_price_policy": "semantic-page-price-recheck-before-catalog-save",
        "challenge_classifier": "strong-product-evidence-overrides-script-marker-false-positive",
        "mediamarkt_vatan_policy": "real-product-html-does-not-enter-verification-wait",
        "hepsiburada_security_policy": "v20.9-preserved",
        "price_integrity": "v21.9-preserved-conservative-final-gate",
        "offer_lifecycle": "v21.8-preserved",
        "canonical_identity_pipeline": "v20.8-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v223")
def runtime_identity_v223():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "production-ingestion-canonical-identity-convergence",
        "serving_mode": "catalog-first-no-live-scrape",
        "production_product_ingestion": "v22.0-preserved",
        "category_aware_identity_matching": "v22.1-preserved",
        "semantic_price_parser": "v22.2-preserved",
        "canonical_identity_convergence": "enabled",
        "phone_identity_policy": "brand-family-variant-storage;ram-kept-as-technical-attribute-not-key",
        "phone_group_convergence": "startup-safe-merge-with-related-record-migration",
        "global_product_convergence": "canonical-key-normalization-and-duplicate-merge",
        "laptop_identity_policy": "ram-and-storage-remain-in-canonical-key",
        "manual_convergence_audit": "/api/identity-convergence/v223/audit",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v224")
def runtime_identity_v224():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "production-ingestion-stress-test-observability",
        "serving_mode": "catalog-first-no-live-scrape",
        "production_product_ingestion": "v22.0-preserved-and-observed",
        "category_aware_identity_matching": "v22.1-preserved",
        "semantic_price_parser": "v22.2-preserved",
        "canonical_identity_convergence": "v22.3-preserved",
        "ingestion_observability": "enabled-persistent-json-last-500",
        "controlled_stress_test": "enabled-sequential-max-10-products",
        "metrics": "duration-store-success-offers-quarantine-duplicates-errors",
        "observability_summary": "/api/ingestion-observability/v224/summary",
        "observability_tasks": "/api/ingestion-observability/v224/tasks",
        "stress_run": "/api/ingestion-observability/v224/stress/run",
        "stress_status": "/api/ingestion-observability/v224/stress/{run_id}",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v225")
def runtime_identity_v225():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "production-ingestion-category-aware-canonical-identity-v2",
        "serving_mode": "catalog-first-no-live-scrape",
        "production_product_ingestion": "v22.0-preserved",
        "phone_identity_matching": "v22.1-v22.3-preserved",
        "semantic_price_parser": "v22.2-preserved",
        "ingestion_observability": "v22.4-preserved",
        "wearable_identity": "enabled",
        "wearable_identity_policy": "brand-family-variant;marketing-color-health-features-warranty-excluded",
        "wearable_query_policy": "brand-family-variant-only",
        "wearable_match_policy": "brand-family-variant-strict",
        "wearable_migration": "startup-convergence-existing-long-title-identities",
        "laptop_identity_policy": "v17-strict-and-ram-storage-preserved",
        "wearable_status": "/api/wearable-identity/v225/status",
        "wearable_audit": "/api/wearable-identity/v225/audit",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v226")
def runtime_identity_v226():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "production-ingestion-store-offer-reliability-amazon-price-recovery",
        "serving_mode": "catalog-first-no-live-scrape",
        "production_product_ingestion": "v22.0-v22.5-preserved-and-reliability-audited",
        "amazon_price_recovery": "buybox-missing-buying-options-semantic-fallback",
        "amazon_price_policy": "installment-coupon-saving-context-rejected",
        "store_offer_reliability": "enabled-globaloffer-is-serving-source",
        "store_offer_policy": "one-active-globaloffer-per-store-different-stores-independent",
        "legacy_productoffer_policy": "legacy-comparison-count-not-serving-store-count",
        "hepsiburada_security_policy": "persistent-session-challenge-detection-preserved-no-bypass",
        "price_integrity": "v21.9-preserved",
        "wearable_identity": "v22.5-preserved",
        "offer_reliability_status": "/api/store-offer-reliability/v226/products/{global_product_id}",
        "offer_reliability_audit": "/api/store-offer-reliability/v226/products/{global_product_id}/audit",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v227")
def runtime_identity_v227():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "production-ingestion-amazon-structured-offer-canonical-alias-reliability",
        "serving_mode": "catalog-first-no-live-scrape",
        "amazon_structured_offer_extraction": "enabled-json-js-state-first",
        "amazon_offer_policy": "try-offer-price-positive-installment-coupon-listprice-negative",
        "amazon_dom_fallback": "v22.6-preserved-after-structured-extraction",
        "canonical_alias_reliability": "enabled-exact-identity-source-only",
        "stale_global_offer_count_repair": "enabled",
        "store_offer_reliability": "v22.6-preserved",
        "wearable_identity": "v22.5-preserved",
        "phone_identity": "v22.3-preserved",
        "price_integrity": "v21.9-preserved",
        "hepsiburada_security_policy": "persistent-session-challenge-detection-preserved-no-bypass",
        "canonical_alias_status": "/api/canonical-alias/v227/status",
        "canonical_alias_audit": "/api/canonical-alias/v227/audit",
        "offer_reliability_status": "/api/store-offer-reliability/v226/products/{global_product_id}",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v228")
def runtime_identity_v228():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "amazon-exact-asin-price-recovery-canonical-key-stabilization",
        "serving_mode": "catalog-first-no-live-scrape",
        "amazon_detail_parser": "v22.7-structured-offer-preserved",
        "amazon_exact_asin_search_price_recovery": "enabled-as-last-safe-fallback",
        "amazon_fallback_policy": "exact-asin-card-only-no-cross-asin-price",
        "amazon_installment_coupon_policy": "not-used-as-sale-price",
        "canonical_alias_reliability": "v22.8-key-stabilized",
        "canonical_key_policy": "sha256(identity_source)-first-32",
        "store_offer_reliability": "v22.6-preserved",
        "wearable_identity": "v22.5-preserved",
        "phone_identity": "v22.3-preserved",
        "price_integrity": "v21.9-preserved",
        "hepsiburada_security_policy": "persistent-session-challenge-detection-preserved-no-bypass",
        "canonical_alias_status": "/api/canonical-alias/v227/status",
        "offer_reliability_status": "/api/store-offer-reliability/v226/products/{global_product_id}",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v229")
def runtime_identity_v229():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "amazon-buyable-offer-resolution-canonical-lookup-before-create",
        "serving_mode": "catalog-first-no-live-scrape",
        "amazon_detail_parser": "v22.7-structured-offer-preserved",
        "amazon_buyable_offer_resolution": "target-asin-offer-listing-first-then-exact-asin-search",
        "amazon_no_offer_status": "NO_BUYABLE_OFFER",
        "amazon_ad_price_policy": "sponsored-recommended-price-never-used-for-target-product",
        "canonical_lookup_before_create": "enabled-exact-identity-source-before-productgroup-and-globalproduct-create",
        "canonical_alias_reliability": "v22.8-preserved-and-v22.9-reported",
        "store_offer_reliability": "v22.6-preserved",
        "wearable_identity": "v22.5-preserved",
        "phone_identity": "v22.3-preserved",
        "price_integrity": "v21.9-preserved",
        "hepsiburada_security_policy": "persistent-session-challenge-detection-preserved-no-bypass",
        "canonical_alias_status": "/api/canonical-alias/v227/status",
        "offer_reliability_status": "/api/store-offer-reliability/v226/products/{global_product_id}",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v230")
def runtime_identity_v230():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "canonical-lifecycle-single-source-of-truth",
        "serving_mode": "catalog-first-no-live-scrape",
        "canonical_resolver": "shared-productgroup-globalproduct-resolver",
        "canonical_database_guards": "unique-identity-source-productgroup-and-active-globalproduct",
        "canonical_create_policy": "lookup-before-create-plus-db-race-guard",
        "canonical_key_policy": "sha256(identity_source)-first-32",
        "amazon_buyable_offer_resolution": "v22.9-preserved",
        "amazon_no_offer_status": "NO_BUYABLE_OFFER",
        "store_offer_reliability": "v22.6-preserved",
        "wearable_identity": "v22.5-preserved",
        "phone_identity": "v22.3-preserved",
        "price_integrity": "v21.9-preserved",
        "canonical_lifecycle_status": "/api/canonical-lifecycle/v230/status",
        "canonical_lifecycle_audit": "/api/canonical-lifecycle/v230/audit",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v231")
def runtime_identity_v231():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "canonical-lifecycle-identity-contract-enforcement",
        "serving_mode": "catalog-first-no-live-scrape",
        "canonical_resolver": "v23.0-shared-resolver-preserved",
        "wearable_identity_contract": "strongest-evidence-family-plus-explicit-variant",
        "wearable_variant_policy": "active-lite-pro-ultra-classic-never-dropped-when-explicit",
        "wearable_base_identity_promotion": "enabled-only-with-single-explicit-metadata-evidence",
        "identity_contract_diagnostics": "enabled",
        "canonical_database_guards": "v23.0-preserved",
        "amazon_buyable_offer_resolution": "v22.9-preserved",
        "amazon_no_offer_status": "NO_BUYABLE_OFFER",
        "store_offer_reliability": "v22.6-preserved",
        "phone_identity": "v22.3-preserved",
        "price_integrity": "v21.9-preserved",
        "canonical_lifecycle_status": "/api/canonical-lifecycle/v230/status",
        "canonical_lifecycle_audit": "/api/canonical-lifecycle/v230/audit",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v232")
def runtime_identity_v232():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "bulk-catalog-growth-production-ingestion-orchestrator",
        "serving_mode": "catalog-first-no-live-scrape",
        "single_product_ingestion": "v23.1-preserved",
        "bulk_ingestion": "enabled-sequential-max-100-unique-urls",
        "bulk_failure_isolation": "per-product",
        "bulk_state": "persistent-json-last-100-runs",
        "bulk_canonical_guard": "v23.1-single-source-and-contract-check-at-batch-end",
        "bulk_run_api": "/api/bulk-ingestion/v232/runs",
        "bulk_status_api": "/api/bulk-ingestion/v232/runs/{run_id}",
        "bulk_runtime_api": "/api/bulk-ingestion/v232/runtime",
        "ingestion_observability": "v22.4-preserved",
        "amazon_buyable_offer_resolution": "v22.9-preserved",
        "amazon_no_offer_status": "NO_BUYABLE_OFFER",
        "store_offer_reliability": "v22.6-preserved",
        "canonical_lifecycle": "v23.1-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v233")
def runtime_identity_v233():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "cross-store-identity-normalization-strict-variant-matcher",
        "serving_mode": "catalog-first-no-live-scrape",
        "bulk_ingestion": "v23.2-preserved",
        "phone_discovery_normalization": "redmi-poco-galaxy-xiaomi-iphone-enabled",
        "phone_query_policy": "brand-family-variant-explicit-5g-storage-no-ram-no-ssd",
        "phone_network_policy": "explicit-marketed-5g-is-canonical-and-strict",
        "phone_variant_policy": "pro-pro-plus-and-base-5g-separated",
        "accessory_part_code_matching": "exact-normalized-manufacturer-code",
        "accessory_code_examples": "MD3J4TU/A=MD3J4TUA=MD3J4TU-A",
        "laptop_strict_matcher": "preserved",
        "wearable_identity": "v23.1-preserved",
        "amazon_buyable_offer_resolution": "v22.9-preserved",
        "store_offer_reliability": "v22.6-preserved",
        "price_integrity": "v21.9-preserved",
        "canonical_lifecycle": "v23.1-preserved-with-v23.3-network-discriminator",
        "bulk_run_api": "/api/bulk-ingestion/v232/runs",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v234")
def runtime_identity_v234():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "canonical-source-identity-bridge-category-leaf-routing",
        "serving_mode": "catalog-first-no-live-scrape",
        "bulk_ingestion": "v23.2-preserved",
        "cross_store_discovery": "v23.3-preserved",
        "canonical_matcher_bridge": "globalproduct-identity-source-to-category-aware-matcher",
        "source_reconstruction": "raw-category-plus-global-category-preserved",
        "phone_category_policy": "leaf-aware-parent-accessory-token-does-not-demote-real-phone",
        "phone_query_policy": "brand-family-variant-explicit-5g-storage-no-ram-no-ssd",
        "phone_network_policy": "explicit-5g-preserved-by-startup-convergence",
        "accessory_part_code_matching": "v23.3-preserved-and-leaf-aware",
        "candidate_save_identity": "target-global-canonical-identity-is-authoritative",
        "laptop_strict_matcher": "v17-preserved",
        "wearable_identity": "v23.1-preserved",
        "amazon_buyable_offer_resolution": "v22.9-preserved",
        "store_offer_reliability": "v22.6-preserved",
        "price_integrity": "v21.9-preserved",
        "bulk_run_api": "/api/bulk-ingestion/v232/runs",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v235")
def runtime_identity_v235():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "fk-safe-canonical-cleanup-and-reference-preservation",
        "serving_mode": "catalog-first-no-live-scrape",
        "bulk_ingestion": "v23.2-preserved",
        "cross_store_matching": "v23.4-preserved",
        "canonical_cleanup": "fk-aware-relink-archive-delete-only-when-zero-references",
        "cleanup_dependencies": "raw-offer-history-alert-and-variant-children",
        "price_history_migration": "linked-offer-target-global-relink",
        "price_alert_migration": "canonical-target-relink-with-duplicate-merge",
        "legacy_global_policy": "archive-if-any-reference-remains",
        "orphan_delete_policy": "delete-variants-and-global-only-after-zero-direct-and-variant-references",
        "phone_query_policy": "v23.4-preserved-no-ram-no-ssd",
        "phone_variant_policy": "v23.4-preserved-base-vs-5g-pro-vs-pro-plus",
        "accessory_part_code_matching": "v23.4-preserved",
        "amazon_buyable_offer_resolution": "v22.9-preserved",
        "store_offer_reliability": "v22.6-preserved",
        "price_integrity": "v21.9-preserved",
        "bulk_run_api": "/api/bulk-ingestion/v232/runs",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v236")
def runtime_identity_v236():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "original-vs-compatible-accessory-guard-and-accessory-price-integrity",
        "serving_mode": "catalog-first-no-live-scrape",
        "bulk_ingestion": "v23.2-preserved",
        "cross_store_matching": "v23.5-preserved-plus-aftermarket-guard",
        "accessory_originality_guard": "uyumlu-muadil-compatible-for-apple-aftermarket-rejected",
        "accessory_part_code_policy": "exact-code-not-sufficient-when-aftermarket-language-present",
        "accessory_price_integrity": "peer-median-low-ratio-0.55-min-2-peers",
        "canonical_cleanup": "v23.5-fk-safe-preserved",
        "phone_query_policy": "v23.4-preserved-no-ram-no-ssd",
        "phone_variant_policy": "v23.4-preserved-base-vs-5g-pro-vs-pro-plus",
        "amazon_buyable_offer_resolution": "v22.9-preserved",
        "store_offer_reliability": "v22.6-preserved",
        "price_integrity_engine": "v23.6-accessory-aware",
        "bulk_run_api": "/api/bulk-ingestion/v232/runs",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v237")
def runtime_identity_v237():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "category-aware-price-integrity-lifecycle-final-serving-audit",
        "serving_mode": "catalog-first-no-live-scrape",
        "bulk_ingestion": "v23.7-final-price-audit-enabled",
        "cross_store_matching": "v23.6-preserved",
        "price_integrity_category_routing": "breadcrumb-leaf-phone-accessory-generic",
        "accessory_low_price_policy": "peer-median-ratio-0.55-min-2-peers",
        "phone_low_price_policy": "peer-median-ratio-0.55-min-2-peers",
        "price_quarantine_recovery": "price-integrity-quarantines-reaudited-and-reactivated-when-trusted",
        "per_peer_price_audit": "enabled-after-every-attached-store-offer",
        "production_final_price_audit": "enabled-before-task-ready",
        "bulk_final_price_audit": "enabled-after-all-products-before-batch-ready",
        "serving_policy": "active-nonhidden-lifecycle-active-only",
        "serving_snapshot": "best-highest-store-count-and-quarantine-count",
        "canonical_cleanup": "v23.5-fk-safe-preserved",
        "accessory_originality_guard": "v23.6-preserved",
        "phone_query_policy": "v23.4-preserved-no-ram-no-ssd",
        "amazon_buyable_offer_resolution": "v22.9-preserved",
        "store_offer_reliability": "v22.6-preserved",
        "bulk_run_api": "/api/bulk-ingestion/v232/runs",
        "price_integrity_status": "/api/price-integrity/v219/products/{global_product_id}",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2311")
def runtime_identity_v2311():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "detail-stage-canonical-matcher-bridge",
        "serving_mode": "catalog-first-no-live-scrape",
        "search_card_bridge": "v23.10-preserved",
        "detail_stage_bridge": "canonical-family-first-v23.11",
        "lenovo_detail_match": "exact-mtm-sku-plus-capacity",
        "macbook_detail_match": "family-plus-storage",
        "tablet_detail_match": "family-plus-storage-ram-if-explicit",
        "audio_detail_match": "family-plus-accessory-guard",
        "wearable_matcher": "v22.5-preserved",
        "phone_variant_network_guards": "v23.3-preserved",
        "accessory_originality_guard": "v23.6-preserved",
        "production_stress_v238": "preserved",
        "stress_run_api": "/api/production-stress/v238/runs",
        "price_integrity_lifecycle": "v23.9-routing-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2310")
def runtime_identity_v2310():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "cross-store-matcher-canonical-family-bridge",
        "serving_mode": "catalog-first-no-live-scrape",
        "cross_store_discovery": "canonical-family-first-v23.10",
        "lenovo_numeric_mtm": "supported-exact-code",
        "macbook_family_bridge": "enabled",
        "wearable_se_ultra_bridge": "enabled",
        "tablet_family_bridge": "enabled",
        "audio_family_bridge": "enabled",
        "wrong_variant_guards": "preserved",
        "production_stress_v238": "preserved",
        "stress_run_api": "/api/production-stress/v238/runs",
        "price_integrity_lifecycle": "v23.9-routing-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v239")
def runtime_identity_v239():
    return {
        "ok": True, "runtime_version": _runtime_version(),
        "architecture": "multi-category-identity-price-routing-hardening",
        "serving_mode": "catalog-first-no-live-scrape",
        "identity_routing": "phone-laptop-tablet-wearable-audio-accessory-generic",
        "iphone_cross_store_matching": "canonical-family-normalized",
        "tablet_identity": "galaxy-tab-family-clean-storage-separated",
        "wearable_price_kind": "enabled",
        "audio_price_kind": "enabled",
        "production_stress_v238": "preserved",
        "stress_run_api": "/api/production-stress/v238/runs",
        "price_integrity_lifecycle": "v23.7-preserved-with-v23.9-routing",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v238")
def runtime_identity_v238():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "ten-product-multicategory-production-stress-readiness",
        "serving_mode": "catalog-first-no-live-scrape",
        "production_stress": "enabled-exactly-10-unique-products",
        "stress_execution": "v23.7-bulk-sequential-products-store-parallelism-preserved",
        "stress_final_gates": "ingestion-canonical-serving-price-integrity-duplicate",
        "stress_readiness": "READY>=90,WATCH>=75,NOT_READY<75",
        "stress_run_api": "/api/production-stress/v238/runs",
        "stress_status_api": "/api/production-stress/v238/runs/{stress_run_id}",
        "stress_runtime_api": "/api/production-stress/v238/runtime",
        "bulk_ingestion": "v23.7-preserved",
        "price_integrity_lifecycle": "v23.7-preserved",
        "canonical_cleanup": "v23.5-preserved",
        "accessory_originality_guard": "v23.6-preserved",
        "cross_store_matching": "v23.4-preserved",
        "amazon_buyable_offer_resolution": "v22.9-preserved",
        "canonical_test_product_id": 125,
    }

@app.get("/api/runtime-identity/v2312")
def runtime_identity_v2312():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "scraper-evidence-preservation-source-reliability-hardening",
        "serving_mode": "catalog-first-no-live-scrape",
        "search_card_bridge": "v23.10-preserved",
        "detail_stage_bridge": "v23.11-preserved",
        "search_card_evidence": "score-label-url-preserved-v23.12",
        "evidence_use_policy": "match-only-copy-no-catalog-pollution",
        "high_confidence_threshold": 300,
        "lenovo_url_sku_recovery": "enabled",
        "macbook_family_evidence_recovery": "enabled",
        "tablet_family_evidence_recovery": "enabled",
        "audio_family_evidence_recovery": "enabled",
        "wrong_variant_guards": "preserved",
        "production_stress_v238": "preserved",
        "stress_run_api": "/api/production-stress/v238/runs",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2313")
def runtime_identity_v2313():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "canonical-convergence-conflict-safe-merge",
        "serving_mode": "catalog-first-no-live-scrape",
        "v223_scope_guard": "phone-only-tablet-wearable-audio-laptop-excluded",
        "product_group_conflict_policy": "vacate-same-bucket-owner-then-merge",
        "global_product_conflict_policy": "vacate-same-bucket-active-owner-then-merge",
        "unsafe_cross_bucket_collision": "fail-closed-no-silent-merge",
        "fk_reference_merge": "offers-features-favorites-alerts-recent-reviews-preserved",
        "v2312_search_card_evidence": "preserved",
        "detail_stage_bridge": "v23.11-preserved",
        "price_integrity_quarantine": "preserved",
        "production_stress_v238": "preserved",
        "stress_run_api": "/api/production-stress/v238/runs",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2314")
def runtime_identity_v2314():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "generic-accessory-cross-store-discovery",
        "serving_mode": "catalog-first-no-live-scrape",
        "generic_identity": "brand-product-type-distinctive-tokens-measure",
        "accessory_identity": "brand-product-type-capacity-spec",
        "room_fragrance_bridge": "enabled",
        "perfume_bridge": "enabled",
        "powerbank_bridge": "enabled",
        "jump_starter_inflator_bridge": "enabled",
        "fail_closed_mismatch_guards": "brand-type-measure-capacity-spec",
        "v2313_convergence": "preserved",
        "v2312_search_card_evidence": "preserved",
        "detail_stage_bridge": "v23.11-preserved-plus-v23.14-natural",
        "price_integrity_quarantine": "preserved",
        "production_stress_v238": "preserved",
        "stress_run_api": "/api/production-stress/v238/runs",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2315")
def runtime_identity_v2315():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "product-kind-contract-category-routing-hardening",
        "serving_mode": "catalog-first-no-live-scrape",
        "product_kind_precedence": "strong-type-category-before-brand-family",
        "powerbank_contract": "accessory/powerbank",
        "room_fragrance_contract": "generic/room_fragrance",
        "perfume_contract": "generic/perfume",
        "jump_starter_inflator_contract": "accessory/jump_starter_inflator",
        "phone_family_fallback": "only-after-strong-type-and-accessory-gates",
        "stress_report_subkind": "enabled",
        "v2314_natural_matcher": "preserved",
        "v2313_convergence": "preserved",
        "v2312_search_card_evidence": "preserved",
        "v2311_detail_stage_bridge": "preserved",
        "price_integrity_quarantine": "preserved",
        "production_stress_v238": "preserved",
        "stress_run_api": "/api/production-stress/v238/runs",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2316")
def runtime_identity_v2316():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "fast-ingest-adaptive-store-scheduler",
        "serving_mode": "catalog-first-fast-ready-deep-refresh",
        "fast_ingest": "enabled",
        "fast_store_tier": ["pazarama", "teknosa", "mediamarkt", "n11", "vatan"],
        "fast_store_workers": 6,
        "fast_search_mode": "reduced-navigation-settle-timeouts",
        "deep_refresh": "background-non-blocking",
        "slow_store_circuit_breaker": "security-challenge-10m",
        "production_ingestion_default": "fast",
        "production_stress_mode": "full-deep-preserved",
        "v2315_product_kind_contract": "preserved",
        "v2314_natural_matcher": "preserved",
        "v2313_convergence": "preserved",
        "price_integrity_quarantine": "preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23161")
def runtime_identity_v23161():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "fast-ingest-circuit-scope-hotfix",
        "serving_mode": "catalog-first-fast-ready-deep-refresh",
        "fast_ingest": "enabled",
        "fast_store_tier": ["pazarama", "teknosa", "mediamarkt", "n11", "vatan"],
        "fast_store_workers": 6,
        "deep_refresh": "background-non-blocking",
        "slow_store_circuit_breaker": "security-challenge-10m",
        "circuit_skipped_scope": "smart-refresh-local-initialized",
        "lifecycle_status_scope": "refresh-vars-removed",
        "production_ingestion_default": "fast",
        "production_stress_mode": "full-deep-preserved",
        "v2316_fast_ingest": "preserved",
        "v2315_product_kind_contract": "preserved",
        "price_integrity_quarantine": "preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2317")
def runtime_identity_v2317():
    return {
        "ok": True,
        "runtime_version": _runtime_version(),
        "architecture": "early-ready-first-offer-latency",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "fast_ingest": "enabled",
        "early_ready_store_tier": ["pazarama", "teknosa"],
        "deferred_fast_store_tier": ["mediamarkt", "n11", "vatan"],
        "fast_store_workers": 6,
        "ready_policy": "primary-tier-then-background",
        "deep_refresh": "background-non-blocking-all-remaining-stores",
        "slow_store_circuit_breaker": "security-challenge-10m",
        "production_stress_mode": "full-deep-preserved",
        "v23161_circuit_hotfix": "preserved",
        "v2315_product_kind_contract": "preserved",
        "price_integrity_quarantine": "preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2318")
def runtime_identity_v2318():
    return {"ok": True, "runtime_version": "23.18.0", "architecture": "generic-coverage-safe-price-fallback", "serving_mode": "catalog-first-primary-tier-ready-deep-refresh", "generic_safe_price_fallback": "high-confidence-search-card-single-tl-price", "fallback_min_score": 300, "fallback_scope": "generic-accessory-only", "fallback_ambiguity_policy": "fail-closed", "price_integrity_quarantine": "preserved", "v2317_early_ready": "preserved", "production_stress_mode": "full-deep-preserved", "canonical_test_product_id": 125}


@app.get("/api/runtime-identity/v2319")
def runtime_identity_v2319():
    return {
        "ok": True,
        "runtime_version": "23.19.0",
        "architecture": "verified-search-card-offer-generic-candidate-precision",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "generic_candidate_brand_gate": "candidate-url-or-card-head",
        "verified_search_card_offer": "generic-only-brand-type-variant-single-price",
        "security_challenge_policy": "no-bypass-verified-card-only",
        "fallback_min_score": 300,
        "ambiguity_policy": "fail-closed",
        "price_integrity_quarantine": "preserved",
        "v2318_safe_price_fallback": "preserved",
        "v2317_early_ready": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2320")
def runtime_identity_v2320():
    return {
        "ok": True,
        "runtime_version": "23.20.0",
        "architecture": "dom-search-card-price-capture-verified-offer",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "search_card_price_capture": "same-dom-card-only",
        "verified_offer_source": "dom-card-only",
        "html_fallback_price_use": "disabled",
        "verified_offer_price_policy": "exactly-one-explicit-tl-price",
        "generic_candidate_brand_gate": "v23.19-preserved",
        "security_challenge_policy": "no-bypass-verified-card-only",
        "price_integrity_quarantine": "preserved",
        "v2319_generic_precision": "preserved",
        "v2317_early_ready": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2321")
def runtime_identity_v2321():
    return {
        "ok": True,
        "runtime_version": "23.21.0",
        "architecture": "hepsiburada-structured-product-card-price-adapter",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "hepsiburada_store_adapter": "registered",
        "hepsiburada_card_binding": "same-card-url-title-price",
        "hepsiburada_current_price_priority": "semantic-current-price-first",
        "ambiguous_card_price_policy": "fail-closed",
        "html_fallback_verified_price": "disabled",
        "security_challenge_policy": "no-bypass-verified-card-only",
        "v2320_dom_price_capture": "preserved",
        "v2319_generic_precision": "preserved",
        "price_integrity_quarantine": "preserved",
        "v2317_early_ready": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2322")
def runtime_identity_v2322():
    return {
        "ok": True,
        "runtime_version": "23.22.0",
        "architecture": "hepsiburada-semantic-price-role-resolver",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "hepsiburada_price_role_resolver": "enabled",
        "currency_required_for_card_price": True,
        "non_currency_numeric_policy": "reject",
        "discount_coupon_rating_installment_roles": "reject",
        "old_list_price_role": "reject-for-verified-current-offer",
        "verified_current_price_source": "same-card-semantic-current-price",
        "ambiguous_card_price_policy": "fail-closed",
        "security_challenge_policy": "no-bypass-verified-card-only",
        "v2321_hepsiburada_card_adapter": "preserved",
        "v2320_dom_price_capture": "preserved",
        "v2319_generic_precision": "preserved",
        "price_integrity_quarantine": "preserved",
        "v2317_early_ready": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2323")
def runtime_identity_v2323():
    return {
        "ok": True,
        "runtime_version": "23.23.0",
        "architecture": "hepsiburada-leaf-price-node-resolver",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "hepsiburada_leaf_price_node_resolver": "enabled",
        "container_price_parse": "disabled-for-verified-offer",
        "leaf_currency_required": True,
        "leaf_multi_currency_policy": "fail-closed",
        "discount_coupon_rating_installment_roles": "reject",
        "old_list_price_role": "reject-for-verified-current-offer",
        "verified_current_price_source": "same-card-leaf-current-price",
        "ambiguous_card_price_policy": "fail-closed",
        "security_challenge_policy": "no-bypass-verified-card-only",
        "v2322_semantic_role_resolver": "preserved",
        "v2321_hepsiburada_card_adapter": "preserved",
        "v2320_dom_price_capture": "preserved",
        "v2319_generic_precision": "preserved",
        "price_integrity_quarantine": "preserved",
        "v2317_early_ready": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2324")
def runtime_identity_v2324():
    return {
        "ok": True,
        "runtime_version": "23.24.0",
        "architecture": "hepsiburada-structured-price-attribute-resolver",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "hepsiburada_structured_price_attribute_resolver": "enabled",
        "text_node_price_primary_source": "disabled",
        "same_card_data_attribute_price": "enabled",
        "same_card_json_state_price": "enabled",
        "broad_page_html_price_use": "disabled",
        "structured_price_cardinality": "exactly-one",
        "ambiguous_structured_price_policy": "fail-closed",
        "security_challenge_policy": "no-bypass-verified-card-only",
        "v2321_hepsiburada_card_adapter": "preserved",
        "v2319_generic_precision": "preserved",
        "price_integrity_quarantine": "preserved",
        "v2317_early_ready": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2325")
def runtime_identity_v2325():
    return {
        "ok": True,
        "runtime_version": "23.25.0",
        "architecture": "hepsiburada-structured-price-provenance-semantic-role-resolver",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "price_provenance": "enabled",
        "generic_data_price_trust": "disabled-unless-current-role",
        "trusted_attribute_roles": "current-sale-selling-final-itemprop-price",
        "trusted_json_keys": "currentPrice-salePrice-sellingPrice-finalPrice",
        "generic_json_price": "diagnostic-only",
        "hepsiburada_verified_price_source": "accepted-provenance-marker-only",
        "card_inner_text_price_use_for_hepsiburada": "disabled",
        "ambiguous_trusted_price_policy": "fail-closed",
        "security_challenge_policy": "no-bypass-verified-card-only",
        "v2324_structured_attribute_resolver": "preserved-and-hardened",
        "v2319_generic_precision": "preserved",
        "price_integrity_quarantine": "preserved",
        "v2317_early_ready": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2326")
def runtime_identity_v2326():
    return {
        "ok": True,
        "runtime_version": "23.26.0",
        "architecture": "hepsiburada-search-card-direct-verified-offer-path",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "hb_direct_search_card_offer": "enabled",
        "hb_direct_offer_min_score": 300,
        "hb_direct_offer_evidence_source": "same-dom-card-only",
        "hb_direct_offer_price_source": "trusted-provenance-accepted-price-only",
        "evidence_marker_position": "before-verbose-card-text",
        "detail_page_requirement_for_verified_hb_card": "not-required",
        "security_challenge_bypass": "disabled",
        "ambiguity_policy": "fail-closed",
        "price_integrity_quarantine": "preserved",
        "v2325_price_provenance": "preserved-and-marker-order-fixed",
        "v2319_generic_precision": "preserved",
        "v2317_early_ready": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2327")
def runtime_identity_v2327():
    return {
        "ok": True,
        "runtime_version": "23.27.0",
        "architecture": "hepsiburada-candidate-provenance-propagation-direct-short-circuit",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "hb_candidate_structured_fields": "accepted-price-provenance-direct-evidence",
        "hb_label_marker_dependency": "removed-for-direct-offer",
        "hb_direct_pre_scrape_short_circuit": "enabled",
        "hb_direct_offer_min_score": 300,
        "hb_direct_offer_evidence_source": "same-dom-card-only",
        "hb_direct_offer_price_cardinality": "exactly-one",
        "security_challenge_bypass": "disabled",
        "ambiguity_policy": "fail-closed",
        "price_integrity_quarantine": "preserved",
        "v2326_direct_path": "preserved-and-structured-field-hardened",
        "v2325_price_provenance": "preserved",
        "v2319_generic_precision": "preserved",
        "v2317_early_ready": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2328")
def runtime_identity_v2328():
    return {
        "ok": True,
        "runtime_version": "23.28.0",
        "architecture": "hepsiburada-dom-price-role-classification",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "hb_exact_current_price_selector": "required-for-text-fallback",
        "hb_explicit_currency_token": "required",
        "hb_generic_price_container_trust": "disabled",
        "hb_current_price_leaf_cardinality": "exactly-one",
        "hb_ambiguous_current_price_leaf": "diagnostic-only-fail-closed",
        "hb_direct_pre_scrape_short_circuit": "enabled",
        "hb_direct_offer_min_score": 300,
        "hb_direct_offer_evidence_source": "same-dom-card-only",
        "security_challenge_bypass": "disabled",
        "ambiguity_policy": "fail-closed",
        "price_integrity_quarantine": "preserved",
        "v2327_structured_propagation": "preserved",
        "v2319_generic_precision": "preserved",
        "v2317_early_ready": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2329")
def runtime_identity_v2329():
    return {
        "ok": True,
        "runtime_version": "23.29.0",
        "architecture": "hepsiburada-price-node-diagnostic",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "hb_price_node_diagnostic": "enabled",
        "hb_diagnostic_scope": "same-product-card-only",
        "hb_diagnostic_fields": "value-tag-class-data-test-id-aria-text-parent",
        "hb_trust_policy_change": "none",
        "hb_direct_pre_scrape_short_circuit": "preserved",
        "security_challenge_bypass": "disabled",
        "ambiguity_policy": "fail-closed",
        "price_integrity_quarantine": "preserved",
        "v2328_dom_price_role_classification": "preserved",
        "v2327_structured_propagation": "preserved",
        "v2319_generic_precision": "preserved",
        "v2317_early_ready": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2330")
def runtime_identity_v2330():
    return {
        "ok": True,
        "runtime_version": "23.30.0",
        "architecture": "hepsiburada-final-price-direct-trust",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "hb_final_price_selector": "data-test-id-final-price-or-class-finalPrice",
        "hb_final_price_full_text_required": True,
        "hb_fraction_node_policy": "reject",
        "hb_coupon_discount_context_policy": "reject",
        "hb_final_price_cardinality": "exactly-one",
        "hb_direct_pre_scrape_short_circuit": "enabled",
        "hb_direct_offer_min_score": 300,
        "hb_direct_offer_evidence_source": "same-dom-card-only",
        "security_challenge_bypass": "disabled",
        "ambiguity_policy": "fail-closed",
        "price_integrity_quarantine": "preserved",
        "v2329_price_node_diagnostic": "preserved",
        "v2328_dom_price_role_classification": "preserved",
        "v2327_structured_propagation": "preserved",
        "v2319_generic_precision": "preserved",
        "v2317_early_ready": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2331")
def runtime_identity_v2331():
    return {"ok":True,"runtime_version":"23.31.0","architecture":"generic-strong-model-family-bridge","serving_mode":"catalog-first-primary-tier-ready-deep-refresh","generic_model_signatures":"haf01-p1200-kvc4108-freebuds-se2-air-purifier4-thermochef-xl","search_card_generic_model_bridge":"enabled","detail_stage_generic_model_bridge":"enabled","manufacturer_model_code_precedence":"required-when-source-has-code","marketing_color_warranty_tokens":"non-identity","brand_guard":"preserved","wrong_variant_guards":"preserved","hb_final_price_direct_trust":"v23.30-preserved","price_integrity_quarantine":"preserved","security_challenge_bypass":"disabled","production_stress_mode":"full-deep-preserved","canonical_test_product_id":125}


@app.get("/api/runtime-identity/v2332")
def runtime_identity_v2332():
    return {
        "ok": True,
        "runtime_version": "23.32.0",
        "architecture": "audio-strong-family-brand-normalization-bridge",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "audio_strong_family_bridge": "freebuds-redmi-buds-galaxy-buds-airpods",
        "audio_color_guard": "explicit-color-mismatch-reject",
        "brand_prefix_normalization": "marka-brand-prefix-stripped",
        "freebuds_se2_vs_se3_se4": "fail-closed",
        "v2331_generic_model_bridge": "preserved",
        "v2330_hb_final_price": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "wrong_variant_guards": "preserved",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2333")
def runtime_identity_v2333():
    return {
        "ok": True,
        "runtime_version": "23.33.0",
        "architecture": "raw-candidate-identity-revalidation",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "strong_identity_raw_candidate_gate": "enabled",
        "search_card_evidence_role": "ranking-selection-not-identity-injection",
        "generic_model_evidence_rescue": "disabled",
        "audio_family_evidence_rescue": "disabled",
        "thermochef_vs_fit_fry": "fail-closed",
        "v2332_audio_strong_family": "preserved",
        "v2331_generic_model_bridge": "preserved",
        "v2330_hb_final_price": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2334")
def runtime_identity_v2334():
    return {
        "ok": True,
        "runtime_version": "23.34.0",
        "architecture": "generic-strong-model-color-variant-guard",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "generic_explicit_color_guard": "enabled",
        "generic_color_policy": "reject-only-when-both-explicit-and-different",
        "kvc4108_gri_vs_kirmizi_beyaz": "fail-closed",
        "p1200_antrasit_vs_kirmizi_gri": "fail-closed",
        "v2333_raw_candidate_identity_gate": "preserved",
        "v2332_audio_color_guard": "preserved",
        "v2331_generic_model_bridge": "preserved",
        "v2330_hb_final_price": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2335")
def runtime_identity_v2335():
    return {
        "ok": True,
        "runtime_version": "23.35.0",
        "architecture": "detail-authoritative-color-revalidation",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "detail_color_authority": "scraped-product-name-model-before-evidence",
        "search_card_color_role": "ranking-only-not-final-identity",
        "detail_color_mismatch_policy": "fail-closed",
        "generic_color_gate": "v23.34-preserved",
        "raw_candidate_identity_gate": "v23.33-preserved",
        "audio_color_guard": "v23.32-preserved",
        "generic_model_bridge": "v23.31-preserved",
        "hb_final_price": "v23.30-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2336")
def runtime_identity_v2336():
    return {
        "ok": True,
        "runtime_version": "23.36.0",
        "architecture": "post-scrape-authoritative-variant-revalidation",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "post_scrape_color_gate": "enabled-before-persistence",
        "post_scrape_color_authority": "final-scraped-candidate-object",
        "search_card_color_role": "ranking-only",
        "rejection_reasons_scope": "fixed-use-existing-errors-list",
        "v2335_detail_color_gate": "preserved-and-scope-fixed",
        "v2334_generic_color_guard": "preserved",
        "v2333_raw_candidate_identity_gate": "preserved",
        "v2332_audio_color_guard": "preserved",
        "v2331_generic_model_bridge": "preserved",
        "v2330_hb_final_price": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2337")
def runtime_identity_v2337():
    return {
        "ok": True,
        "runtime_version": "23.37.0",
        "architecture": "pre-canonical-transfer-scraped-variant-guard",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "central_pre_canonical_variant_guard": "enabled",
        "central_guard_position": "before-v23.7-canonical-transfer-and-save-product",
        "candidate_authority": "final-candidate-object-about-to-be-persisted",
        "color_mismatch_policy": "hard-reject-before-persistence",
        "v2336_post_scrape_guard": "preserved",
        "v2335_detail_color_gate": "preserved",
        "v2334_generic_color_guard": "preserved",
        "v2333_raw_candidate_identity_gate": "preserved",
        "v2332_audio_color_guard": "preserved",
        "v2331_generic_model_bridge": "preserved",
        "v2330_hb_final_price": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2338")
def runtime_identity_v2338():
    return {
        "ok": True,
        "runtime_version": "23.38.0",
        "architecture": "true-final-object-pre-persistence-variant-gate",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "final_object_enrichment": "same-productidentityservice-enrich-as-save-product",
        "final_object_variant_gate": "enabled-after-enrichment-before-canonical-transfer",
        "persisted_object_contract": "same-enriched-object-validated-and-saved",
        "mediamarkt_gray-url_black-product": "fail-closed",
        "v2337_precanonical_guard": "superseded-by-enriched-final-object-gate",
        "v2336_post_scrape_guard": "preserved",
        "v2335_detail_color_gate": "preserved",
        "v2334_generic_color_guard": "preserved",
        "v2333_raw_candidate_identity_gate": "preserved",
        "v2332_audio_color_guard": "preserved",
        "v2331_generic_model_bridge": "preserved",
        "v2330_hb_final_price": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2339")
def runtime_identity_v2339():
    return {
        "ok": True,
        "runtime_version": "23.39.0",
        "architecture": "final-name-explicit-color-authority",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "final_name_color_authority": "enabled",
        "carried_candidate_color_role": "diagnostic-fallback-only",
        "explicit_final_name_color_precedence": "highest",
        "mediamarkt_gray-url_black-name": "fail-closed",
        "v2338_final_object_enrichment": "preserved",
        "v2337_precanonical_guard": "preserved",
        "v2336_post_scrape_guard": "preserved",
        "v2335_detail_color_gate": "preserved",
        "v2334_generic_color_guard": "preserved",
        "v2333_raw_candidate_identity_gate": "preserved",
        "v2332_audio_color_guard": "preserved",
        "v2331_generic_model_bridge": "preserved",
        "v2330_hb_final_price": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2340")
def runtime_identity_v2340():
    return {
        "ok": True,
        "runtime_version": "23.40.0",
        "architecture": "final-name-color-scope-fix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "final_name_fold_scope": "local-dependency-free-v2340",
        "final_name_color_authority": "v23.39-preserved",
        "explicit_final_name_color_precedence": "highest",
        "mediamarkt_gray-url_black-name": "fail-closed-after-scope-fix",
        "v2339_final_name_gate": "preserved",
        "v2338_final_object_enrichment": "preserved",
        "v2337_precanonical_guard": "preserved",
        "v2336_post_scrape_guard": "preserved",
        "v2335_detail_color_gate": "preserved",
        "v2334_generic_color_guard": "preserved",
        "v2333_raw_candidate_identity_gate": "preserved",
        "v2332_audio_color_guard": "preserved",
        "v2331_generic_model_bridge": "preserved",
        "v2330_hb_final_price": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2341")
def runtime_identity_v2341():
    return {
        "ok": True,
        "runtime_version": "23.41.0",
        "architecture": "token-aware-color-and-fresh-source-selection",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "color_token_boundary": "enabled-red-does-not-match-redmi",
        "final_name_color_token_boundary": "enabled",
        "global_source_selection": "latest-updated-raw-first",
        "historical_variant_source_policy": "oldest-direct-raw-disabled",
        "v2340_scope_fix": "preserved",
        "v2339_final_name_authority": "preserved",
        "v2332_audio_guard": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2342")
def runtime_identity_v2342():
    return {
        "ok": True,
        "runtime_version": "23.42.0",
        "architecture": "token-aware-color-regex-runtime-fix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "regex_runtime_dependency": "explicit-top-level-import-re",
        "color_token_boundary": "v23.41-preserved",
        "final_name_color_token_boundary": "v23.41-preserved",
        "global_source_selection": "v23.41-latest-updated-raw-first",
        "historical_variant_source_policy": "oldest-direct-raw-disabled",
        "v2341_token_aware_color": "preserved",
        "v2340_scope_fix": "preserved",
        "v2339_final_name_authority": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2343")
def runtime_identity_v2343():
    return {"ok": True, "runtime_version": "23.43.0", "architecture": "generic-main-product-vs-accessory-role-guard", "serving_mode": "catalog-first-primary-tier-ready-deep-refresh", "generic_accessory_role_guard": "enabled", "guard_positions": "generic-strong-model-and-final-object-pre-persistence", "spare_part_roles": "motor-filter-case-basket-mop-battery-brush-charger-bag-hose-spare-part", "bare_compatible_token_policy": "not-sufficient-alone", "p1200_motor_vs_vacuum": "fail-closed", "v2342_regex_runtime_fix": "preserved", "v2341_token_aware_color": "preserved", "v2340_scope_fix": "preserved", "v2339_final_name_authority": "preserved", "price_integrity_quarantine": "preserved", "security_challenge_bypass": "disabled", "production_stress_mode": "full-deep-preserved", "canonical_test_product_id": 125}


@app.get("/api/runtime-identity/v2344")
def runtime_identity_v2344():
    return {
        "ok": True,
        "runtime_version": "23.44.0",
        "architecture": "generic-consumable-bag-accessory-hard-reject",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "generic_accessory_role_guard": "v23.43-preserved-and-expanded",
        "bag_role_markers": "toz-torbasi-supurge-torbasi-bez-torba-dust-bag-vacuum-bag-filter-bag",
        "p1200_motor_vs_vacuum": "v23.43-preserved-fail-closed",
        "p1200_bag_vs_vacuum": "fail-closed",
        "guard_positions": "generic-strong-model-and-final-object-pre-persistence",
        "v2343_product_vs_accessory": "preserved",
        "v2342_regex_runtime_fix": "preserved",
        "v2341_token_aware_color": "preserved",
        "v2340_scope_fix": "preserved",
        "v2339_final_name_authority": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2345")
def runtime_identity_v2345():
    return {
        "ok": True,
        "runtime_version": "23.45.0",
        "architecture": "category-independent-accessory-role-hardening",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "generic_accessory_role_guard": "v23.43-v23.44-preserved-and-hardened",
        "cross_category_roles": "filter-case-basket-mop-battery-brush-charger-bag-hose-maintenance-spare-part",
        "charging_case_policy": "accessory-not-main-audio-product",
        "airfryer_basket_policy": "accessory-not-main-appliance",
        "air_purifier_filter_policy": "accessory-not-main-appliance",
        "vacuum_spare_policy": "motor-bag-filter-brush-hose-spare-part-fail-closed",
        "bare_compatible_token_policy": "not-sufficient-alone",
        "guard_positions": "generic-strong-model-and-final-object-pre-persistence",
        "v2344_bag_guard": "preserved",
        "v2343_product_vs_accessory": "preserved",
        "v2342_regex_runtime_fix": "preserved",
        "v2341_token_aware_color": "preserved",
        "v2340_scope_fix": "preserved",
        "v2339_final_name_authority": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2346")
def runtime_identity_v2346():
    return {
        "ok": True,
        "runtime_version": "23.46.0",
        "architecture": "deep-refresh-task-lifecycle-observability",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "deep_refresh_task_link": "task-id-propagated-to-background-worker",
        "deep_refresh_lifecycle": "QUEUED-RUNNING-COMPLETED-FAILED",
        "deep_refresh_post_audit": "price-integrity-and-offer-reliability",
        "deep_refresh_serving_snapshot": "refreshed-after-background-completion",
        "ready_response_policy": "non-blocking-preserved",
        "v2345_accessory_hardening": "preserved",
        "v2344_bag_guard": "preserved",
        "v2343_product_vs_accessory": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2347")
def runtime_identity_v2347():
    return {"ok":True,"runtime_version":"23.47.0","architecture":"deep-refresh-store-quality-telemetry","serving_mode":"catalog-first-primary-tier-ready-deep-refresh","store_duration_observability":"enabled","store_outcome_telemetry":"success-failure-offer-found-candidate-rejected","failure_classification":"security-no-candidate-identity-price-timeout-scrape-other","slowest_store_detection":"enabled","deep_refresh_failure_breakdown":"enabled","deep_refresh_lifecycle":"v23.46-preserved","v2346_task_lifecycle":"preserved","v2345_accessory_hardening":"preserved","price_integrity_quarantine":"preserved","security_challenge_bypass":"disabled","production_stress_mode":"full-deep-preserved","canonical_test_product_id":125}


@app.get("/api/runtime-identity/v23471")
def runtime_identity_v23471():
    return {
        "ok": True,
        "runtime_version": "23.47.1",
        "architecture": "deep-refresh-store-quality-telemetry-smoke-utf8-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "smoke_test_encoding": "explicit-utf-8",
        "v2347_store_quality_telemetry": "preserved",
        "v2346_deep_refresh_lifecycle": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2348")
def runtime_identity_v2348():
    return {
        "ok": True,
        "runtime_version": "23.48.0",
        "architecture": "deep-refresh-telemetry-integrity-and-success-message-normalization",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "telemetry_count": "explicit",
        "telemetry_success_message": "OFFER_SAVED",
        "telemetry_raw_message": "preserved",
        "telemetry_store_code_lists": "success-and-failure-explicit",
        "v23471_utf8_hotfix": "preserved",
        "v2347_store_quality_telemetry": "preserved-and-hardened",
        "v2346_deep_refresh_lifecycle": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2349")
def runtime_identity_v2349():
    return {
        "ok": True,
        "runtime_version": "23.49.0",
        "architecture": "store-latency-budget-fast-fail-low-yield-stores",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "latency_sensitive_stores": "gaminggen-itopya-incehesap",
        "latency_navigation_timeout_ms": 15000,
        "latency_settle_timeout_ms": 700,
        "latency_network_timeout_ms": 1500,
        "latency_max_query_variants": 1,
        "successful_store_path_policy": "unchanged",
        "candidate_identity_and_price_integrity": "preserved",
        "v2348_telemetry_integrity": "preserved",
        "v2347_store_quality_telemetry": "preserved",
        "v2346_deep_refresh_lifecycle": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2350")
def runtime_identity_v2350():
    return {
        "ok": True,
        "runtime_version": "23.50.0",
        "architecture": "http-first-search-fast-fail-low-yield-stores",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "http_first_stores": "gaminggen-itopya-incehesap",
        "http_first_timeout_seconds": 8,
        "healthy_http_no_candidate_policy": "skip-browser-search",
        "http_candidate_found_policy": "normal-detail-scrape-and-identity-validation",
        "browser_fallback_policy": "only-unhealthy-http-or-request-error",
        "successful_store_paths": "unchanged",
        "v2349_latency_budget": "preserved-as-browser-fallback",
        "v2348_telemetry_integrity": "preserved",
        "candidate_identity_and_price_integrity": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2351")
def runtime_identity_v2351():
    return {
        "ok": True,
        "runtime_version": "23.51.0",
        "architecture": "adaptive-store-search-scheduler",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "scheduler_policy": "category-aware-priority-no-permanent-store-disable",
        "scheduler_priority_fields": "scheduler-priority-reason-search-path",
        "low_yield_store_policy": "deprioritize-and-http-first-not-disable",
        "successful_store_policy": "prioritize-existing-high-yield-paths",
        "v2350_http_first": "preserved",
        "v2349_latency_budget": "preserved",
        "v2348_telemetry_integrity": "preserved",
        "candidate_identity_and_price_integrity": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2352")
def runtime_identity_v2352():
    return {
        "ok": True,
        "runtime_version": "23.52.0",
        "architecture": "wave-scheduler-and-execution-vs-queue-telemetry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "scheduler_waves": "3",
        "wave_policy": "priority>=90-wave1-priority>=47-wave2-rest-wave3",
        "telemetry_duration_split": "queue-wait-execution-total",
        "wave_execution_policy": "waves-run-sequentially-stores-within-wave-parallel",
        "v2351_adaptive_scheduler": "preserved",
        "v2350_http_first": "preserved",
        "v2349_latency_budget": "preserved",
        "v2348_telemetry_integrity": "preserved",
        "candidate_identity_and_price_integrity": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2353")
def runtime_identity_v2353():
    return {
        "ok": True,
        "runtime_version": "23.53.0",
        "architecture": "rolling-hybrid-priority-scheduler-and-telemetry-serialization-fix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "scheduler_policy": "rolling-priority-no-wave-barrier",
        "scheduler_slot_policy": "submit-next-when-worker-frees",
        "n11_policy": "sequential-preserved",
        "telemetry_serialization": "queue-wait-execution-wave-propagated",
        "v2352_duration_split": "preserved-and-fixed-end-to-end",
        "v2351_adaptive_priority": "preserved",
        "v2350_http_first": "preserved",
        "candidate_identity_and_price_integrity": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2354")
def runtime_identity_v2354():
    return {
        "ok": True,
        "runtime_version": "23.54.0",
        "architecture": "hybrid-priority-with-dedicated-concurrent-n11-lane",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "n11_lane": "single-worker-dedicated-overlapped-with-main-hybrid-pool",
        "n11_profile_parallelism": "one-within-scan",
        "scheduler_priority_telemetry": "actual-category-aware-score-propagated",
        "scheduler_reason_telemetry": "actual-reason-propagated",
        "v2353_rolling_priority": "preserved",
        "v2352_queue_execution_telemetry": "preserved",
        "v2350_http_first": "preserved",
        "candidate_identity_and_price_integrity": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2355")
def runtime_identity_v2355():
    return {
        "ok": True,
        "runtime_version": "23.55.0",
        "architecture": "audio-main-product-vs-bundle-mixed-product-guard",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "audio_mixed_main_product_guard": "enabled-detail-stage-before-strong-family-accept",
        "watch_plus_freebuds_policy": "fail-closed",
        "bundle_markers": "diagnostic-not-required-when-second-main-family-explicit",
        "price_integrity_quarantine": "v23.54-preserved-last-line-defense",
        "v2354_dedicated_n11_lane": "preserved",
        "v2353_rolling_priority": "preserved",
        "v2350_http_first": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2356")
def runtime_identity_v2356():
    return {
        "ok": True,
        "runtime_version": "23.56.0",
        "architecture": "search-card-bundle-pre-filter",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "search_card_bundle_pre_filter": "enabled-before-candidate-score-and-detail-scrape",
        "audio_bundle_policy": "second-main-product-with-target-audio-family-fail-closed",
        "v2355_detail_mixed_main_guard": "preserved",
        "v2354_dedicated_n11_lane": "preserved",
        "v2353_rolling_priority": "preserved",
        "v2350_http_first": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2357")
def runtime_identity_v2357():
    return {
        "ok": True,
        "runtime_version": "23.57.0",
        "architecture": "audio-family-search-card-bundle-prefilter-enforcement",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "audio_search_card_bundle_gate": "hard-reject-before-canonical-card-score",
        "watch_fit_plus_freebuds": "fail-closed-before-detail-scrape",
        "v2356_helper": "preserved-and-wired-into-audio-family-path",
        "v2355_detail_guard": "preserved-second-line-defense",
        "v2354_dedicated_n11_lane": "preserved",
        "v2353_rolling_priority": "preserved",
        "price_integrity_quarantine": "preserved-last-line-defense",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2358")
def runtime_identity_v2358():
    return {
        "ok": True,
        "runtime_version": "23.58.0",
        "architecture": "bundle-prefilter-observability-and-task-telemetry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "bundle_prefilter_event_log": "V23.58-BUNDLE-PREFILTER-REJECT",
        "bundle_prefilter_store_telemetry": "count-and-samples",
        "bundle_prefilter_task_telemetry": "aggregate-count-store-codes-samples",
        "duplicate_reject_policy": "same-store-url-counted-once",
        "v2357_audio_search_card_gate": "preserved-and-observed",
        "v2355_detail_guard": "preserved-second-line-defense",
        "v2354_dedicated_n11_lane": "preserved",
        "price_integrity_quarantine": "preserved-last-line-defense",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2359")
def runtime_identity_v2359():
    return {
        "ok": True,
        "runtime_version": "23.59.0",
        "architecture": "category-independent-early-search-card-bundle-prefilter",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "early_bundle_gate": "before-search-result-score-and-before-card-price-evidence",
        "category_mode_dependency": "removed-for-bundle-prefilter",
        "bundle_reject_event": "V23.59-EARLY-BUNDLE-PREFILTER-REJECT",
        "v2358_observability": "preserved",
        "v2357_score_gate": "preserved-second-line-defense",
        "v2355_detail_guard": "preserved-third-line-defense",
        "price_integrity_quarantine": "preserved-last-line-defense",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2360")
def runtime_identity_v2360():
    return {
        "ok": True,
        "runtime_version": "23.60.0",
        "architecture": "store-reliability-and-retry-intelligence",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "retry_policy": "advisory-no-immediate-same-run-retry",
        "retry_classes": "transient-deferred-context-change-only-none",
        "store_reliability_score": "0-100-per-attempt",
        "security_challenge_policy": "deferred-retry-no-bypass",
        "identity_reject_policy": "no-retry-until-query-or-variant-context-changes",
        "v2359_early_bundle_prefilter": "preserved",
        "v2358_bundle_observability": "preserved",
        "v2354_scheduler_and_n11_lane": "preserved",
        "price_integrity_quarantine": "preserved-last-line-defense",
        "security_challenge_bypass": "disabled",
        "production_stress_mode": "full-deep-preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v2361")
def runtime_identity_v2361():
    return {
        "ok": True,
        "runtime_version": "23.61.0",
        "architecture": "reliability-aware-adaptive-retry-scheduler",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "scheduler_state": "in-memory-per-runtime-store-and-product-context",
        "security_challenge_cooldown": "store-global-1800-seconds",
        "no_candidate_cooldown": "product-context-21600-seconds",
        "no_buyable_offer_cooldown": "product-context-21600-seconds",
        "identity_reject_policy": "same-context-skip-until-context-changes",
        "scheduler_skip_telemetry": "count-codes-details-and-state-snapshot",
        "immediate_same_run_retry": "disabled",
        "v2360_reliability_intelligence": "preserved-and-consumed-by-scheduler",
        "v2359_early_bundle_prefilter": "preserved",
        "price_integrity_quarantine": "preserved-last-line-defense",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23611")
def runtime_identity_v23611():
    return {
        "ok": True,
        "runtime_version": "23.61.1",
        "architecture": "unified-smart-refresh-reliability-backoff-observability",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "smart_refresh_backoff": "v23.60-reliability-aware",
        "context_change_only": "enforced-at-upper-smart-refresh-layer",
        "deferred_retry": "retry-after-seconds-drives-next-check-at",
        "success_freshness": "30-minute-existing-policy-preserved",
        "upper_skip_telemetry": "count-codes-details",
        "lower_retry_scheduler": "v23.61-preserved-second-line-defense",
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23612")
def runtime_identity_v23612():
    return {
        "ok": True,
        "runtime_version": "23.61.2",
        "architecture": "user-ingestion-priority-over-background-catalog-feed",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "priority_policy": "user-deep-refresh-before-new-background-catalog-products",
        "background_batch_yield": "stop-before-next-product-when-user-priority-active",
        "catalog_feed_yield": "do-not-start-new-batch-while-user-priority-active",
        "inflight_background_policy": "current-product-finishes-no-unsafe-preemption",
        "deep_refresh_queue_telemetry": "queue-reason-wait-seconds-priority",
        "v23611_reliability_backoff": "preserved",
        "v2361_lower_retry_scheduler": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23613")
def runtime_identity_v23613():
    return {
        "ok": True,
        "runtime_version": "23.61.3",
        "architecture": "full-ingestion-lifecycle-user-priority-lease",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "priority_lease_start": "immediately-after-task-id-before-source-scrape",
        "priority_lease_scope": "source-scrape-primary-tier-through-deep-refresh-finish",
        "priority_lease_idempotency": "first-queued-time-preserved",
        "background_catalog_policy": "cannot-start-new-product-while-user-ingestion-lease-active",
        "queue_wait_semantics": "measured-from-user-task-arrival-to-deep-worker-start",
        "safe_preemption": "no-mid-product-cancel-current-background-product-may-finish",
        "v23612_queue_fairness": "preserved-and-fixed-lease-timing",
        "v23611_reliability_backoff": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23614")
def runtime_identity_v23614():
    return {
        "ok": True,
        "runtime_version": "23.61.4",
        "architecture": "central-workload-aware-background-scan-priority-gate",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "workload_classes": "USER_INGESTION-BACKGROUND",
        "central_smart_refresh_gate": "background-yields-while-user-lease-active",
        "central_repair_gate": "background-full-store-scan-yields-while-user-lease-active",
        "production_ingestion_workload": "explicit-USER_INGESTION",
        "legacy_catalog_feed_workload": "BACKGROUND",
        "category_scheduler_gate": "enabled",
        "v9_catalog_scheduler_gate": "enabled",
        "safe_preemption": "existing-inflight-call-may-finish-no-mid-scrape-cancel",
        "v23613_full_lifecycle_priority_lease": "preserved",
        "v23611_reliability_backoff": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23615")
def runtime_identity_v23615():
    return {
        "ok": True,
        "runtime_version": "23.61.5",
        "architecture": "lowest-layer-cross-store-priority-recheck",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "lowest_layer_gate": "scan-other-stores-rechecks-user-priority-before-store-work",
        "rolling_slot_gate": "background-does-not-open-new-store-slot-after-user-priority-activates",
        "n11_lane_gate": "background-n11-lane-rechecks-before-submit",
        "stale_background_job_policy": "jobs-that-passed-old-gates-before-user-arrival-yield-at-scan-layer",
        "production_ingestion_workload": "USER_INGESTION-bypasses-background-yield",
        "v23614_central_gates": "preserved",
        "v23613_full_lifecycle_priority_lease": "preserved",
        "v23611_reliability_backoff": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23616")
def runtime_identity_v23616():
    return {
        "ok": True,
        "runtime_version": "23.61.6",
        "architecture": "sqlite-cross-process-user-ingestion-priority-lease",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "priority_backend": "sqlite-wal-cross-thread-cross-process",
        "lease_scope": "task-id-source-through-deep-refresh",
        "stale_lease_ttl_seconds": 3600,
        "priority_failure_policy": "fail-safe-background-yield",
        "lowest_layer_recheck": "v23.61.5-preserved",
        "central_workload_gates": "v23.61.4-preserved",
        "reliability_backoff": "v23.61.1-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }

@app.get("/api/runtime-workload-priority/v23616")
def runtime_workload_priority_v23616():
    return user_deep_priority_snapshot_v23612()


@app.get("/api/runtime-identity/v23617")
def runtime_identity_v23617():
    return {
        "ok": True,
        "runtime_version": "23.61.7",
        "architecture": "background-batch-priority-generation-barrier",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "priority_generation": "sqlite-monotonic-generation-per-new-user-ingestion-task",
        "catalog_feed_barrier": "generation-recheck-after-candidate-selection",
        "batch_barrier": "generation-recheck-before-and-after-each-background-product",
        "inflight_background_policy": "current-product-may-finish-next-products-deferred-on-generation-change",
        "sqlite_priority_lease": "v23.61.6-preserved",
        "lowest_layer_recheck": "v23.61.5-preserved",
        "central_workload_gates": "v23.61.4-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }

@app.get("/api/runtime-priority-generation/v23617")
def runtime_priority_generation_v23617():
    return {
        "priority_generation": user_priority_generation_v23617(),
        "priority": user_deep_priority_snapshot_v23612(),
    }


@app.get("/api/runtime-identity/v23618")
def runtime_identity_v23618():
    return {
        "ok": True,
        "runtime_version": "23.61.8",
        "architecture": "process-crash-diagnostics-and-faulthandler",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "behavioral_change": "none-diagnostics-only",
        "python_unhandled_exception_log": "enabled",
        "thread_unhandled_exception_log": "enabled",
        "faulthandler_all_threads": "enabled",
        "atexit_marker": "enabled",
        "v23617_priority_generation_barrier": "preserved",
        "v23616_sqlite_priority_lease": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }

@app.get("/api/runtime-crash-diagnostics/v23618")
def runtime_crash_diagnostics_v23618():
    return crash_diagnostics_status_v23618()


@app.get("/api/runtime-identity/v23619")
def runtime_identity_v23619():
    return {
        "ok": True,
        "runtime_version": "23.61.9",
        "architecture": "foreground-ready-vs-preemptible-background-deep-refresh",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "foreground_priority_scope": "source-and-primary-tier-until-ready-only",
        "deep_refresh_workload": "BACKGROUND_DEEP_REFRESH",
        "deep_refresh_foreground_policy": "defer-and-resubmit-while-user-ingestion-active",
        "deep_refresh_executor_workers": 2,
        "old_user_deep_refresh_priority_inversion": "fixed",
        "v23618_crash_diagnostics": "preserved",
        "v23617_generation_barrier": "preserved",
        "v23616_sqlite_priority_lease": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v236110")
def runtime_identity_v236110():
    return {
        "ok": True,
        "runtime_version": "23.61.10",
        "architecture": "read-only-foreground-ready-background-final-integrity-audit",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "foreground_finalization": "read-only-serving-snapshot-no-sqlite-writer",
        "ready_policy": "primary-tier-complete-then-ready-immediately",
        "mutating_final_price_audit": "post-ready-background",
        "mutating_offer_reliability_audit": "post-ready-background",
        "peer_price_integrity": "preserved-during-offer-save",
        "deep_refresh_workload": "BACKGROUND_DEEP_REFRESH",
        "v23619_priority_inversion_fix": "preserved",
        "v23618_crash_diagnostics": "preserved",
        "v23617_generation_barrier": "preserved",
        "v23616_sqlite_priority_lease": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v236111")
def runtime_identity_v236111():
    return {
        "ok": True,
        "runtime_version": "23.61.11",
        "architecture": "retry-backoff-hours-nameerror-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "root_cause": "undefined-hours-in-smart-refresh-state-persistence",
        "backoff_hours_source": "retry-after-seconds-divided-by-3600",
        "success_backoff_hours": "none",
        "retry_intelligence": "v23.60-v23.61-preserved",
        "foreground_ready_policy": "v23.61.10-preserved",
        "background_deep_refresh": "v23.61.9-preserved",
        "priority_generation_barrier": "v23.61.7-preserved",
        "sqlite_priority_lease": "v23.61.6-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23620")
def runtime_identity_v23620():
    return {
        "ok": True,
        "runtime_version": "23.62.0",
        "architecture": "generic-strong-model-query-synthesis",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "generic_model_query_policy": "strong-signature-before-brand-only",
        "audio_example": "huawei-freebuds-se-2-before-huawei",
        "target_stores": "amazon-n11-mediamarkt-vatan-idefix",
        "broad_brand_query": "fallback-only",
        "identity_and_color_gates": "preserved",
        "bundle_prefilter": "preserved",
        "foreground_ready": "v23.61.10-preserved",
        "retry_backoff_hotfix": "v23.61.11-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23621")
def runtime_identity_v23621():
    return {
        "ok": True,
        "runtime_version": "23.62.1",
        "architecture": "color-aware-pre-detail-candidate-ordering",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "candidate_order_policy": "same-family-source-color-first-before-detail-scrape",
        "acceptance_policy": "unchanged-fail-closed-color-and-identity-gates",
        "amazon_goal": "avoid-black-blue-detail-before-white-when-source-is-white",
        "n11_card_price_policy": "detail-authoritative-preserved",
        "v23620_model_first_query": "preserved",
        "v236111_retry_backoff_hotfix": "preserved",
        "foreground_ready": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23622")
def runtime_identity_v23622():
    return {
        "ok": True,
        "runtime_version": "23.62.2",
        "architecture": "search-card-source-color-priority-before-detail",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "source_color_extraction": "db-product-name-model-direct",
        "candidate_color_signal": "same-color-plus-two-other-color-minus-one-order-only",
        "detail_acceptance_policy": "unchanged-fail-closed",
        "amazon_target": "white-before-black-blue-for-white-source",
        "v23620_model_first_query": "preserved",
        "foreground_ready": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23623")
def runtime_identity_v23623():
    return {
        "ok": True,
        "runtime_version": "23.62.3",
        "architecture": "explicit-source-color-carry-from-scan-store-to-candidate-order",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "source_color_origin": "scan-store-source-name-and-model-text",
        "source_color_transport": "explicit-string-argument",
        "object_reparse_dependency": "removed-from-primary-path",
        "candidate_order_policy": "same-color-first-other-color-last-order-only",
        "detail_acceptance_policy": "unchanged-fail-closed",
        "amazon_target": "white-before-black-blue-for-white-source",
        "v23622_card_color_priority": "preserved-and-fixed-source-signal",
        "v23620_model_first_query": "preserved",
        "foreground_ready": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23624")
def runtime_identity_v23624():
    return {
        "ok": True,
        "runtime_version": "23.62.4",
        "architecture": "binding-production-scan-source-color-wiring-fix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "root_cause": "BindingCrossStoreSearchService-override-bypassed-base-source-color-carry",
        "production_scan_path": "binding-cross-store-override",
        "source_color_transport": "explicit-from-binding-scan-to-find-candidate-urls",
        "expected_white_source": "beyaz",
        "candidate_order_policy": "same-color-first-other-color-last-order-only",
        "detail_acceptance_policy": "unchanged-fail-closed",
        "v23623_text-color-parser": "preserved-and-now-consumed-by-production-path",
        "v23620_model_first_query": "preserved",
        "foreground_ready": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23625")
def runtime_identity_v23625():
    return {
        "ok": True,
        "runtime_version": "23.62.5",
        "architecture": "audio-accessory-prefilter-and-amazon-verified-card-offer",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "audio_accessory_prefilter": "before-score-color-and-detail",
        "color_priority": "url-authoritative-label-fallback",
        "amazon_price_fallback": "same-url-dom-card-exact-family-exact-color-single-price",
        "amazon_browser_fallback": "retained-when-card-evidence-not-safe",
        "n11_accessory_policy": "obvious-case-silicone-not-detail-candidate",
        "detail_identity_gates": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "v23624_binding_source_color": "preserved",
        "foreground_ready": "preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23626")
def runtime_identity_v23626():
    return {
        "ok": True,
        "runtime_version": "23.62.6",
        "architecture": "boundary-aware-color-and-n11-single-card-detail-order",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "color_matching": "token-boundary-blue-does-not-match-bluetooth",
        "color_priority": "url-authoritative-label-fallback",
        "n11_detail_order": "single-card-price-evidence-before-multi-price-color-only",
        "n11_price_authority": "detail-authoritative-preserved",
        "amazon_verified_card_offer": "v23.62.5-preserved",
        "audio_accessory_prefilter": "v23.62.5-preserved",
        "identity_gates": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "foreground_ready": "preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23627")
def runtime_identity_v23627():
    return {
        "ok": True,
        "runtime_version": "23.62.7",
        "architecture": "n11-detail-network-latency-budget-and-phase-telemetry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "n11_detail_http_timeout_seconds": 8,
        "n11_detail_http_retries": 0,
        "n11_detail_fallback": "existing-browser-path",
        "detail_phase_telemetry": "http-and-browser-elapsed-seconds",
        "n11_candidate_order": "v23.62.6-preserved",
        "n11_price_authority": "detail-authoritative-preserved",
        "amazon_verified_card_offer": "v23.62.5-preserved",
        "audio_accessory_prefilter": "preserved",
        "identity_gates": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "foreground_ready": "preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23628")
def runtime_identity_v23628():
    return {
        "ok": True,
        "runtime_version": "23.62.8",
        "architecture": "n11-search-browser-latency-budget-and-phase-telemetry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "n11_search_navigation_timeout_ms": 12000,
        "n11_search_settle_ms": 700,
        "n11_search_scroll_count": 1,
        "n11_search_networkidle_timeout_ms": 1200,
        "n11_search_phase_telemetry": "goto-settle-scroll-network-total",
        "n11_detail_http_budget": "v23.62.7-preserved",
        "n11_candidate_order": "v23.62.6-preserved",
        "n11_price_authority": "detail-authoritative-preserved",
        "amazon_verified_card_offer": "v23.62.5-preserved",
        "identity_gates": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "foreground_ready": "preserved",
        "canonical_test_product_id": 125,
    }


@app.get("/api/runtime-identity/v23629")
def runtime_identity_v23629():
    return {
        "ok": True,
        "runtime_version": "23.62.9",
        "architecture": "localhost-test-only-forced-smart-refresh-endpoint",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_scope": "localhost-test-only",
        "force_refresh_policy": "bypass-smart-backoff-and-circuit-breaker-for-one-explicit-test-call",
        "production_ingestion_backoff": "unchanged",
        "persistent_retry_state": "not-cleared-or-mutated-for-test-bypass",
        "n11_search_latency_budget": "v23.62.8-preserved",
        "n11_detail_latency_budget": "v23.62.7-preserved",
        "n11_candidate_order": "v23.62.6-preserved",
        "amazon_verified_card_offer": "v23.62.5-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
        "canonical_test_global_product_id": 160,
    }


# V23.62.25 localhost force-refresh single-flight / cooldown guard.
# This affects only the explicit developer test endpoint; production refresh
# scheduling and ingestion behavior remain unchanged.
_FORCE_REFRESH_V236225_LOCK = __import__("threading").Lock()
_FORCE_REFRESH_V236225_STATE = {
    "active": False,
    "started_at_monotonic": None,
    "finished_at_monotonic": None,
    "last_duration_seconds": None,
    "last_global_product_id": None,
    "last_status": "NEVER_RUN",
}
_FORCE_REFRESH_V236225_COOLDOWN_SECONDS = 5.0

# V23.62.48 production soak/stability telemetry.
# Observation-only: never influences scraper ordering, candidate acceptance,
# retry policy, persistence, or production ingestion behavior.
_SOAK_V236248_LOCK = __import__("threading").Lock()
_SOAK_V236248_MAX_RUNS = 50
_SOAK_V236248_RUNS = []
_SOAK_V236248_EXPECTED_OFFERS = 6
_SOAK_V236248_EXPECTED_SUCCESS_STORES = 6

def _record_soak_run_v236248(*, duration_seconds, telemetry, newly_saved_offer_count, scanned_store_count):
    now_ts = __import__("time").time()
    stores = {}
    for row in list(telemetry or []):
        code = str(row.get("store_code") or "unknown").strip().lower()
        stores[code] = {
            "status": str(row.get("status") or ("SUCCESS" if row.get("success") else "FAILED")),
            "success": bool(row.get("success")),
            "execution_seconds": float(row.get("execution_seconds") or row.get("duration_seconds") or 0.0),
            "failure_class": str(row.get("failure_class") or ""),
        }
    success_count = sum(1 for row in stores.values() if row["success"])
    run = {
        "timestamp_epoch": round(now_ts, 3),
        "duration_seconds": float(duration_seconds or 0.0),
        "scanned_store_count": int(scanned_store_count or 0),
        "newly_saved_offer_count": int(newly_saved_offer_count or 0),
        "store_success_count": int(success_count),
        "store_failure_count": int(max(0, len(stores) - success_count)),
        "stores": stores,
    }
    with _SOAK_V236248_LOCK:
        _SOAK_V236248_RUNS.append(run)
        del _SOAK_V236248_RUNS[:-_SOAK_V236248_MAX_RUNS]

def _soak_snapshot_v236248():
    with _SOAK_V236248_LOCK:
        runs = [dict(r, stores={k: dict(v) for k, v in r.get("stores", {}).items()}) for r in _SOAK_V236248_RUNS]
    store_codes = sorted({code for run in runs for code in run.get("stores", {})})
    store_summary = {}
    for code in store_codes:
        rows = [run["stores"][code] for run in runs if code in run.get("stores", {})]
        latencies = [float(row.get("execution_seconds") or 0.0) for row in rows]
        failures = {}
        success_count = sum(1 for row in rows if row.get("success"))
        for row in rows:
            failure_class = str(row.get("failure_class") or "")
            if failure_class:
                failures[failure_class] = failures.get(failure_class, 0) + 1
        success_timestamps = [
            float(run.get("timestamp_epoch") or 0.0)
            for run in runs
            if code in run.get("stores", {}) and run["stores"][code].get("success")
        ]
        store_summary[code] = {
            "observations": len(rows),
            "success_count": success_count,
            "failure_count": len(rows) - success_count,
            "success_rate_percent": round((100.0 * success_count / len(rows)), 2) if rows else None,
            "latency_avg_seconds": round(sum(latencies) / len(latencies), 3) if latencies else None,
            "latency_min_seconds": round(min(latencies), 3) if latencies else None,
            "latency_max_seconds": round(max(latencies), 3) if latencies else None,
            "last_success_timestamp_epoch": round(max(success_timestamps), 3) if success_timestamps else None,
            "failure_classes": failures,
        }
    durations = [float(run.get("duration_seconds") or 0.0) for run in runs]
    offers = [int(run.get("newly_saved_offer_count") or 0) for run in runs]
    success_counts = [int(run.get("store_success_count") or 0) for run in runs]
    last = runs[-1] if runs else None
    alarms = []
    if last:
        if last["newly_saved_offer_count"] < _SOAK_V236248_EXPECTED_OFFERS:
            alarms.append("OFFER_COUNT_DEVIATION")
        if last["store_success_count"] < _SOAK_V236248_EXPECTED_SUCCESS_STORES:
            alarms.append("STORE_SUCCESS_COUNT_DEVIATION")
        n11 = last.get("stores", {}).get("n11")
        if not n11 or not n11.get("success"):
            alarms.append("N11_NOT_SUCCESS")
    if len(runs) >= 5:
        last5 = runs[-5:]
        if any(int(r.get("newly_saved_offer_count") or 0) < _SOAK_V236248_EXPECTED_OFFERS for r in last5):
            alarms.append("LAST5_OFFER_REGRESSION")
        if any(int(r.get("store_success_count") or 0) < _SOAK_V236248_EXPECTED_SUCCESS_STORES for r in last5):
            alarms.append("LAST5_SUCCESS_COUNT_REGRESSION")
        if any(not r.get("stores", {}).get("n11", {}).get("success") for r in last5):
            alarms.append("LAST5_N11_REGRESSION")

    # V23.62.49: PASS is a rolling-window contract, not only a last/last5 check.
    # A regression remains visible until that run naturally ages out of the 50-run window.
    violating_runs = []
    for index, run in enumerate(runs, start=1):
        reasons = []
        if int(run.get("newly_saved_offer_count") or 0) < _SOAK_V236248_EXPECTED_OFFERS:
            reasons.append("OFFER_COUNT_DEVIATION")
        if int(run.get("store_success_count") or 0) < _SOAK_V236248_EXPECTED_SUCCESS_STORES:
            reasons.append("STORE_SUCCESS_COUNT_DEVIATION")
        if not run.get("stores", {}).get("n11", {}).get("success"):
            reasons.append("N11_NOT_SUCCESS")
        if reasons:
            violating_runs.append({
                "window_index": index,
                "timestamp_epoch": run.get("timestamp_epoch"),
                "reasons": reasons,
                "newly_saved_offer_count": run.get("newly_saved_offer_count"),
                "store_success_count": run.get("store_success_count"),
                "n11_status": run.get("stores", {}).get("n11", {}).get("status"),
                "n11_failure_class": run.get("stores", {}).get("n11", {}).get("failure_class"),
            })
    if any("OFFER_COUNT_DEVIATION" in item["reasons"] for item in violating_runs):
        alarms.append("WINDOW_OFFER_REGRESSION")
    if any("STORE_SUCCESS_COUNT_DEVIATION" in item["reasons"] for item in violating_runs):
        alarms.append("WINDOW_SUCCESS_COUNT_REGRESSION")
    if any("N11_NOT_SUCCESS" in item["reasons"] for item in violating_runs):
        alarms.append("WINDOW_N11_REGRESSION")
    alarms = list(dict.fromkeys(alarms))
    return {
        "window_max_runs": _SOAK_V236248_MAX_RUNS,
        "observed_run_count": len(runs),
        "contract_pass_run_count": len(runs) - len(violating_runs),
        "contract_violation_run_count": len(violating_runs),
        "contract_violation_runs": violating_runs[-10:],
        "expected_offer_count": _SOAK_V236248_EXPECTED_OFFERS,
        "expected_store_success_count": _SOAK_V236248_EXPECTED_SUCCESS_STORES,
        "minimum_offer_count": _SOAK_V236248_EXPECTED_OFFERS,
        "minimum_store_success_count": _SOAK_V236248_EXPECTED_SUCCESS_STORES,
        "count_contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "stability_status": "PASS" if runs and not alarms else ("NO_DATA" if not runs else "ALERT"),
        "regression_alarms": alarms,
        "total_latency_avg_seconds": round(sum(durations) / len(durations), 3) if durations else None,
        "total_latency_min_seconds": round(min(durations), 3) if durations else None,
        "total_latency_max_seconds": round(max(durations), 3) if durations else None,
        "offer_count_min": min(offers) if offers else None,
        "offer_count_max": max(offers) if offers else None,
        "store_success_count_min": min(success_counts) if success_counts else None,
        "store_success_count_max": max(success_counts) if success_counts else None,
        "last_run": last,
        "recent_runs": [
            {
                "timestamp_epoch": run.get("timestamp_epoch"),
                "duration_seconds": run.get("duration_seconds"),
                "newly_saved_offer_count": run.get("newly_saved_offer_count"),
                "store_success_count": run.get("store_success_count"),
                "store_failure_count": run.get("store_failure_count"),
                "n11_status": run.get("stores", {}).get("n11", {}).get("status"),
                "n11_seconds": run.get("stores", {}).get("n11", {}).get("execution_seconds"),
                "hepsiburada_status": run.get("stores", {}).get("hepsiburada", {}).get("status"),
                "hepsiburada_seconds": run.get("stores", {}).get("hepsiburada", {}).get("execution_seconds"),
            }
            for run in runs[-10:]
        ],
        "stores": store_summary,
    }


@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")
def force_deep_refresh_v23629(global_product_id: int, request: Request):
    from fastapi import HTTPException

    client_host = str(getattr(getattr(request, "client", None), "host", "") or "")
    if client_host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="Localhost-only test endpoint.")

    now_v236225 = __import__("time").perf_counter()

    # Do not queue another heavy browser/SQLite force scan behind an active one.
    if not _FORCE_REFRESH_V236225_LOCK.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "FORCE_REFRESH_ALREADY_RUNNING",
                "message": "Bir force deep refresh zaten çalışıyor.",
                "retry_after_seconds": 5,
            },
            headers={"Retry-After": "5"},
        )

    try:
        finished_v236225 = _FORCE_REFRESH_V236225_STATE.get("finished_at_monotonic")
        if finished_v236225 is not None:
            elapsed_since_finish_v236225 = max(0.0, now_v236225 - float(finished_v236225))
            remaining_v236225 = max(
                0.0,
                _FORCE_REFRESH_V236225_COOLDOWN_SECONDS - elapsed_since_finish_v236225,
            )
            if remaining_v236225 > 0:
                retry_after_v236225 = max(1, int(__import__("math").ceil(remaining_v236225)))
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": "FORCE_REFRESH_COOLDOWN",
                        "message": "Önceki force scan sonrası kaynakların temizlenmesi bekleniyor.",
                        "retry_after_seconds": retry_after_v236225,
                    },
                    headers={"Retry-After": str(retry_after_v236225)},
                )

        started = __import__("time").perf_counter()
        _FORCE_REFRESH_V236225_STATE.update({
            "active": True,
            "started_at_monotonic": started,
            "last_global_product_id": int(global_product_id),
            "last_status": "RUNNING",
        })

        try:
            refresh = smart_refresh_product(
                global_product_id=int(global_product_id),
                candidate_limit=50,
                parallel_workers=4,
                force=True,
                allowed_store_codes=None,
                fast_mode=False,
                workload_class="USER_INGESTION",
            )
            store_results = list(refresh.get("store_results") or [])
            telemetry = _deep_refresh_store_telemetry_v2347(store_results)
            duration = round(__import__("time").perf_counter() - started, 3)
            _FORCE_REFRESH_V236225_STATE["last_status"] = "COMPLETED"
        except BaseException:
            _FORCE_REFRESH_V236225_STATE["last_status"] = "FAILED"
            raise
        finally:
            finished_now_v236225 = __import__("time").perf_counter()
            _FORCE_REFRESH_V236225_STATE.update({
                "active": False,
                "finished_at_monotonic": finished_now_v236225,
                "last_duration_seconds": round(finished_now_v236225 - started, 3),
            })

        _record_soak_run_v236248(
            duration_seconds=duration,
            telemetry=telemetry,
            newly_saved_offer_count=int(refresh.get("newly_saved_offer_count", 0) or 0),
            scanned_store_count=int(refresh.get("scanned_store_count", 0) or 0),
        )

        return {
            "ok": True,
            "runtime_version": _RUNTIME_VERSION_V236323,
            "test_only": True,
            "forced": True,
            "global_product_id": int(global_product_id),
            "duration_seconds": duration,
            "scanned_store_count": int(refresh.get("scanned_store_count", 0) or 0),
            "skipped_store_count": int(refresh.get("skipped_store_count", 0) or 0),
            "newly_saved_offer_count": int(refresh.get("newly_saved_offer_count", 0) or 0),
            "store_success_count": sum(1 for row in telemetry if bool(row.get("success"))),
            "store_failure_count": sum(1 for row in telemetry if not bool(row.get("success"))),
            "store_telemetry_count": len(telemetry),
            "store_telemetry": telemetry,
            "smart_backoff_bypassed": True,
            "production_backoff_state_cleared": False,
        }
    finally:
        _FORCE_REFRESH_V236225_LOCK.release()



@app.get("/api/runtime-identity/v236210")
def runtime_identity_v236210():
    return {
        "ok": True,
        "runtime_version": "23.62.10",
        "architecture": "n11-model-first-query-order-after-latency-telemetry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "n11_query_order": "model-only-then-brand-model-then-fallbacks",
        "n11_expected_first_query": "freebuds se 2",
        "n11_brand_model_timeout_avoidance": "enabled",
        "n11_search_latency_budget": "v23.62.8-preserved",
        "n11_detail_latency_budget": "v23.62.7-preserved",
        "n11_candidate_order": "v23.62.6-preserved",
        "amazon_verified_card_offer": "v23.62.5-preserved",
        "force_refresh_test_endpoint": "v23.62.9-preserved",
        "identity_gates": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_product_id": 125,
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236211")
def runtime_identity_v236211():
    return {
        "ok": True,
        "runtime_version": "23.62.11",
        "architecture": "n11-binding-post-search-phase-telemetry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "behavioral_change": "none-telemetry-only",
        "n11_phase_telemetry": "search-scrape-detail-canonical-match-attach-save-total",
        "n11_model_first_query": "v23.62.10-preserved",
        "n11_search_latency_budget": "v23.62.8-preserved",
        "n11_detail_latency_budget": "v23.62.7-preserved",
        "force_refresh_test_endpoint": "v23.62.9-preserved",
        "identity_gates": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236212")
def runtime_identity_v236212():
    return {
        "ok": True,
        "runtime_version": "23.62.12",
        "architecture": "n11-dedicated-lane-actual-completion-timestamp",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "root_cause": "n11-future-collected-after-parallel-jobs-inflated-execution-seconds",
        "n11_completion_time": "captured-by-future-done-callback",
        "n11_collection_lag": "reported-separately-not-counted-as-execution",
        "behavioral_change": "telemetry-correction-only",
        "n11_binding_phase_telemetry": "v23.62.11-preserved",
        "n11_model_first_query": "v23.62.10-preserved",
        "force_refresh_test_endpoint": "v23.62.9-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236213")
def runtime_identity_v236213():
    return {
        "ok": True,
        "runtime_version": "23.62.13",
        "architecture": "hepsiburada-challenge-latency-budget-and-phase-telemetry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "hepsiburada_challenge_recheck_ms": [1000, 2000],
        "hepsiburada_product_settle_ms": 1000,
        "hepsiburada_phase_telemetry": "browser-launch-goto-settle-challenge-recheck-total",
        "security_challenge_policy": "fail-closed-no-bypass",
        "n11_actual_completion_timing": "v23.62.12-preserved",
        "n11_binding_telemetry": "v23.62.11-preserved",
        "n11_model_first_query": "v23.62.10-preserved",
        "force_refresh_test_endpoint": "v23.62.9-preserved",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236214")
def runtime_identity_v236214():
    return {
        "ok": True,
        "runtime_version": "23.62.14",
        "architecture": "hepsiburada-selector-early-stop-and-url-dedupe",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "hepsiburada_selector_policy": "stop-after-first-productive-selector-with-at-least-8-cards",
        "hepsiburada_raw_candidate_dedupe": "by-clean-product-url-before-scoring",
        "hepsiburada_search_telemetry": "per-selector-raw-dedupe-total",
        "hepsiburada_challenge_latency": "v23.62.13-preserved",
        "security_challenge_policy": "fail-closed-no-bypass",
        "n11_actual_completion_timing": "v23.62.12-preserved",
        "force_refresh_test_endpoint": "v23.62.9-preserved",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236215")
def runtime_identity_v236215():
    return {
        "ok": True,
        "runtime_version": "23.62.15",
        "architecture": "idefix-strong-query-cap-and-search-phase-telemetry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "idefix_query_policy": "two-strong-model-queries-no-third-brand-only-fallback",
        "idefix_search_telemetry": "per-query-total",
        "identity_and_detail_gates": "preserved-fail-closed",
        "hepsiburada_selector_optimization": "v23.62.14-preserved",
        "hepsiburada_challenge_latency": "v23.62.13-preserved",
        "n11_actual_completion_timing": "v23.62.12-preserved",
        "force_refresh_test_endpoint": "v23.62.9-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236216")
def runtime_identity_v236216():
    return {
        "ok": True,
        "runtime_version": "23.62.16",
        "architecture": "sqlite-integrity-gate-quarantine-and-verified-recovery",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "startup_db_gate": "full-integrity-check-before-api-start",
        "corrupt_db_policy": "raw-quarantine-before-recovery",
        "recovery_source_policy": "richest-previous-db-that-passes-quick-check",
        "recovery_copy_policy": "sqlite-backup-to-temp-full-integrity-check-atomic-replace",
        "continuity_import_policy": "malformed-candidates-excluded",
        "write_on_failed_integrity": "blocked-api-does-not-start",
        "v236215_idefix_query_cap": "preserved",
        "v236214_hepsiburada_selector": "preserved",
        "v236212_n11_actual_timing": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-db-integrity/v236216")
def runtime_db_integrity_v236216():
    import json as _json
    from pathlib import Path as _Path
    state = _Path(__file__).resolve().parent / ".runtime" / "database_integrity_v23616.json"
    if not state.exists():
        return {
            "ok": False,
            "runtime_version": "23.62.16",
            "state": "NOT_RUN",
        }
    payload = _json.loads(state.read_text(encoding="utf-8"))
    return {
        "ok": bool(payload.get("startup_allowed")),
        "runtime_version": "23.62.16",
        **payload,
    }


@app.get("/api/runtime-identity/v236217")
def runtime_identity_v236217():
    return {
        "ok": True,
        "runtime_version": "23.62.17",
        "architecture": "continuity-first-full-integrity-gate-and-runtime-db-write-guard",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "startup_order": "continuity-then-full-integrity-then-api",
        "continuity_candidate_policy": "full-integrity-only",
        "continuity_copy_policy": "sqlite-backup-temp-full-check-atomic-replace-post-check",
        "sqlite_journal_mode": "WAL",
        "sqlite_synchronous": "FULL",
        "sqlite_busy_timeout_ms": 60000,
        "sqlite_mmap": "disabled-conservative-windows-safety",
        "runtime_write_guard": "trip-on-malformed-database-and-block-future-commits",
        "v236216_recovery": "preserved-as-post-continuity-gate",
        "v236215_idefix_query_cap": "preserved",
        "v236214_hepsiburada_selector": "preserved",
        "v236212_n11_actual_timing": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-db-write-guard/v236217")
def runtime_db_write_guard_v236217():
    from app.database.database import db_write_guard_snapshot_v23617
    snapshot = db_write_guard_snapshot_v23617()
    return {
        "ok": not bool(snapshot.get("tripped")),
        **snapshot,
    }


@app.get("/api/runtime-db-integrity-live/v236219")
def runtime_db_integrity_live_v236219(full: bool = True):
    import sqlite3 as _sqlite3
    import time as _time
    from app.core.config import settings as _settings

    db_path = _settings.database_path
    started = _time.perf_counter()
    conn = None
    try:
        conn = _sqlite3.connect(
            f"file:{db_path.as_posix()}?mode=ro",
            uri=True,
            timeout=20,
        )
        quick_rows = [str(row[0]) for row in conn.execute("PRAGMA quick_check(1)").fetchall()]
        quick_ok = bool(quick_rows) and all(row.lower() == "ok" for row in quick_rows)

        full_rows = []
        full_ok = None
        if full:
            full_rows = [str(row[0]) for row in conn.execute("PRAGMA integrity_check").fetchall()]
            full_ok = bool(full_rows) and all(row.lower() == "ok" for row in full_rows)

        return {
            "ok": bool(quick_ok and (full_ok is not False)),
            "runtime_version": "23.62.19",
            "live": True,
            "database_path": str(db_path),
            "database_size": db_path.stat().st_size if db_path.exists() else 0,
            "quick_check_ok": quick_ok,
            "quick_check_rows": quick_rows[:20],
            "full_check_requested": bool(full),
            "integrity_check_ok": full_ok,
            "integrity_check_rows": full_rows[:20],
            "elapsed_seconds": round(_time.perf_counter() - started, 3),
        }
    except _sqlite3.Error as exc:
        return {
            "ok": False,
            "runtime_version": "23.62.19",
            "live": True,
            "database_path": str(db_path),
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(_time.perf_counter() - started, 3),
        }
    finally:
        if conn is not None:
            conn.close()


@app.get("/api/runtime-identity/v236218")
def runtime_identity_v236218():
    return {
        "ok": True,
        "runtime_version": "23.62.18",
        "architecture": "live-post-write-sqlite-integrity-verification",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "live_integrity_endpoint": "/api/runtime-db-integrity-live/v236218",
        "live_integrity_policy": "read-only-quick-check-plus-optional-full-integrity-check",
        "startup_integrity_gate": "v23.62.17-preserved",
        "runtime_write_guard": "v23.62.17-preserved",
        "continuity_full_integrity": "v23.62.17-preserved",
        "v236215_idefix_query_cap": "preserved",
        "v236214_hepsiburada_selector": "preserved",
        "v236212_n11_actual_timing": "preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236219")
def runtime_identity_v236219():
    return {
        "ok": True,
        "runtime_version": "23.62.19",
        "architecture": "live-sqlite-integrity-endpoint-config-import-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "root_cause": "v236218-imported-app-config-instead-of-app-core-config",
        "live_integrity_endpoint": "/api/runtime-db-integrity-live/v236219",
        "settings_source": "app.core.config.settings",
        "live_integrity_policy": "read-only-quick-check-plus-full-integrity-check",
        "force_refresh_behavior": "unchanged",
        "startup_integrity_gate": "v23.62.17-preserved",
        "runtime_write_guard": "v23.62.17-preserved",
        "continuity_full_integrity": "v23.62.17-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236220")
def runtime_identity_v236220():
    return {
        "ok": True,
        "runtime_version": "23.62.20",
        "architecture": "hepsiburada-search-navigation-latency-budget",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "hepsiburada_search_navigation_timeout_ms": 10000,
        "hepsiburada_search_settle_ms": 650,
        "hepsiburada_search_scroll_count": 0,
        "hepsiburada_search_networkidle_timeout_ms": 650,
        "hepsiburada_search_phase_telemetry": "goto-settle-network-total",
        "candidate_and_detail_identity_gates": "preserved-fail-closed",
        "security_challenge_policy": "preserved-no-bypass",
        "live_db_integrity": "v23.62.19-preserved",
        "runtime_write_guard": "v23.62.17-preserved",
        "idefix_query_cap": "v23.62.15-preserved",
        "n11_actual_completion_timing": "v23.62.12-preserved",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236221")
def runtime_identity_v236221():
    return {
        "ok": True,
        "runtime_version": "23.62.21",
        "architecture": "n11-commit-plus-product-selector-ready-search-navigation",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "n11_navigation_wait_until": "commit",
        "n11_product_ready_selector": "a[href*=\'/urun/\']",
        "n11_product_ready_timeout_ms": 6000,
        "n11_search_navigation_timeout_ms": 10000,
        "n11_search_settle_ms": 350,
        "n11_search_scroll_count": 0,
        "n11_search_networkidle_timeout_ms": 300,
        "n11_detail_http_budget": "v23.62.7-preserved",
        "n11_identity_and_detail_gates": "preserved-fail-closed",
        "hepsiburada_search_latency": "v23.62.20-preserved",
        "live_db_integrity": "v23.62.19-preserved",
        "runtime_write_guard": "v23.62.17-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236222")
def runtime_identity_v236222():
    return {
        "ok": True,
        "runtime_version": "23.62.22",
        "architecture": "mediamarkt-commit-plus-product-selector-ready-search-navigation",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "mediamarkt_navigation_wait_until": "commit",
        "mediamarkt_product_ready_selector": "a[href*=\'/tr/product/\']",
        "mediamarkt_product_ready_timeout_ms": 6000,
        "mediamarkt_search_navigation_timeout_ms": 10000,
        "mediamarkt_search_settle_ms": 350,
        "mediamarkt_search_scroll_count": 0,
        "mediamarkt_search_networkidle_timeout_ms": 350,
        "mediamarkt_detail_identity_gates": "preserved-fail-closed",
        "n11_selector_ready_search": "v23.62.21-preserved",
        "hepsiburada_search_latency": "v23.62.20-preserved",
        "live_db_integrity": "v23.62.19-preserved",
        "runtime_write_guard": "v23.62.17-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236223")
def runtime_identity_v236223():
    return {
        "ok": True,
        "runtime_version": "23.62.23",
        "architecture": "teknosa-commit-plus-product-selector-ready-search-navigation",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "teknosa_navigation_wait_until": "commit",
        "teknosa_product_ready_selector": "a[href*=\'-p-\']",
        "teknosa_product_ready_timeout_ms": 6000,
        "teknosa_search_navigation_timeout_ms": 10000,
        "teknosa_search_settle_ms": 350,
        "teknosa_search_scroll_count": 0,
        "teknosa_search_networkidle_timeout_ms": 350,
        "teknosa_detail_path": "requests-preserved",
        "teknosa_identity_and_price_gates": "preserved-fail-closed",
        "mediamarkt_selector_ready_search": "v23.62.22-preserved",
        "n11_selector_ready_search": "v23.62.21-preserved",
        "hepsiburada_search_latency": "v23.62.20-preserved",
        "live_db_integrity": "v23.62.19-preserved",
        "runtime_write_guard": "v23.62.17-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236224")
def runtime_identity_v236224():
    return {
        "ok": True,
        "runtime_version": "23.62.24",
        "architecture": "idefix-strong-query-only-zero-candidate-fast-fail",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "idefix_query_policy": "single-strong-brand-model-query-only",
        "idefix_removed_fallback": "model-only-second-browser-cycle",
        "idefix_fail_closed_policy": "preserved-no-candidate-on-zero-safe-result",
        "teknosa_selector_ready_search": "v23.62.23-preserved",
        "mediamarkt_selector_ready_search": "v23.62.22-preserved",
        "n11_selector_ready_search": "v23.62.21-preserved",
        "hepsiburada_search_latency": "v23.62.20-preserved",
        "live_db_integrity": "v23.62.19-preserved",
        "runtime_write_guard": "v23.62.17-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-force-refresh-guard/v236225")
def runtime_force_refresh_guard_v236225():
    now = __import__("time").perf_counter()
    finished = _FORCE_REFRESH_V236225_STATE.get("finished_at_monotonic")
    cooldown_remaining = 0.0
    if finished is not None:
        cooldown_remaining = max(
            0.0,
            _FORCE_REFRESH_V236225_COOLDOWN_SECONDS - (now - float(finished)),
        )
    return {
        "ok": True,
        "runtime_version": "23.62.25",
        "active": bool(_FORCE_REFRESH_V236225_STATE.get("active")),
        "last_status": _FORCE_REFRESH_V236225_STATE.get("last_status"),
        "last_duration_seconds": _FORCE_REFRESH_V236225_STATE.get("last_duration_seconds"),
        "last_global_product_id": _FORCE_REFRESH_V236225_STATE.get("last_global_product_id"),
        "cooldown_seconds": _FORCE_REFRESH_V236225_COOLDOWN_SECONDS,
        "cooldown_remaining_seconds": round(cooldown_remaining, 3),
    }


@app.get("/api/runtime-identity/v236225")
def runtime_identity_v236225():
    return {
        "ok": True,
        "runtime_version": "23.62.25",
        "architecture": "localhost-force-refresh-single-flight-and-cooldown-guard",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_single_flight": "enabled-localhost-test-endpoint-only",
        "force_refresh_concurrent_policy": "409-force-refresh-already-running",
        "force_refresh_post_completion_cooldown_seconds": 5,
        "force_refresh_cooldown_policy": "429-with-retry-after",
        "production_ingestion_behavior": "unchanged",
        "idefix_strong_query_only": "v23.62.24-preserved",
        "teknosa_selector_ready_search": "v23.62.23-preserved",
        "mediamarkt_selector_ready_search": "v23.62.22-preserved",
        "n11_selector_ready_search": "v23.62.21-preserved",
        "hepsiburada_search_latency": "v23.62.20-preserved",
        "live_db_integrity": "v23.62.19-preserved",
        "runtime_write_guard": "v23.62.17-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236226")
def runtime_identity_v236226():
    return {
        "ok": True,
        "runtime_version": "23.62.26",
        "architecture": "n11-selector-ready-post-wait-fast-path-and-runtime-metadata-consistency",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.26",
        "n11_selector_ready_fast_path": "150ms-settle-skip-networkidle-when-selector-ready",
        "n11_selector_not_ready_policy": "v23.62.21-existing-settle-network-path-preserved",
        "n11_identity_and_detail_gates": "preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "idefix_strong_query_only": "v23.62.24-preserved",
        "teknosa_selector_ready_search": "v23.62.23-preserved",
        "mediamarkt_selector_ready_search": "v23.62.22-preserved",
        "hepsiburada_search_latency": "v23.62.20-preserved",
        "live_db_integrity": "v23.62.19-preserved",
        "runtime_write_guard": "v23.62.17-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236227")
def runtime_identity_v236227():
    return {
        "ok": True,
        "runtime_version": "23.62.27",
        "architecture": "vatan-selector-ready-search-fast-path",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.27",
        "vatan_selector_ready_fast_path": "product-container-selector-150ms-settle-skip-networkidle",
        "vatan_selector_not_ready_policy": "existing-settle-network-path-preserved",
        "vatan_identity_detail_price_gates": "preserved",
        "n11_selector_ready_fast_path": "v23.62.26-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "idefix_strong_query_only": "v23.62.24-preserved",
        "teknosa_selector_ready_search": "v23.62.23-preserved",
        "mediamarkt_selector_ready_search": "v23.62.22-preserved",
        "hepsiburada_search_latency": "v23.62.20-preserved",
        "live_db_integrity": "v23.62.19-preserved",
        "runtime_write_guard": "v23.62.17-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236228")
def runtime_identity_v236228():
    return {
        "ok": True,
        "runtime_version": "23.62.28",
        "architecture": "n11-first-query-navigation-variance-guard",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.28",
        "n11_first_query_navigation_budget_ms": 4500,
        "n11_first_query_timeout_policy": "fail-closed-continue-to-existing-stronger-query",
        "n11_subsequent_query_navigation_budget": "v23.62.21-full-budget-preserved",
        "n11_selector_ready_fast_path": "v23.62.26-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "idefix_strong_query_only": "v23.62.24-preserved",
        "teknosa_selector_ready_search": "v23.62.23-preserved",
        "mediamarkt_selector_ready_search": "v23.62.22-preserved",
        "hepsiburada_search_latency": "v23.62.20-preserved",
        "live_db_integrity": "v23.62.19-preserved",
        "runtime_write_guard": "v23.62.17-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236229")
def runtime_identity_v236229():
    return {
        "ok": True,
        "runtime_version": "23.62.29",
        "architecture": "trendyol-selector-ready-search-fast-path-and-phase-telemetry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.29",
        "trendyol_selector_ready_fast_path": "canonical-product-path-selector-150ms-settle-skip-networkidle",
        "trendyol_selector_not_ready_policy": "existing-domcontentloaded-settle-network-path-preserved",
        "trendyol_identity_detail_price_gates": "preserved",
        "n11_first_query_navigation_variance_guard": "v23.62.28-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "n11_selector_ready_fast_path": "v23.62.26-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "idefix_strong_query_only": "v23.62.24-preserved",
        "teknosa_selector_ready_search": "v23.62.23-preserved",
        "mediamarkt_selector_ready_search": "v23.62.22-preserved",
        "hepsiburada_search_latency": "v23.62.20-preserved",
        "live_db_integrity": "v23.62.19-preserved",
        "runtime_write_guard": "v23.62.17-preserved",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }



@app.get("/api/runtime-identity/v236236")
def runtime_identity_v236236():
    return {
        "ok": True,
        "runtime_version": "23.62.36",
        "architecture": "idefix-bounded-no-candidate-search-budget",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.36",
        "idefix_query_policy": "v23.62.24-single-strong-brand-model-query-preserved",
        "idefix_navigation_budget_ms": 5500,
        "idefix_anchor_probe_max_ms": 1500,
        "idefix_no_anchor_policy": "fail-closed-no-candidate-within-bounded-budget",
        "idefix_explicit_zero_marker_probe": "v23.62.32-retired-no-reliable-marker",
        "n11_scope_safety_hotfix": "v23.62.35-preserved",
        "n11_strong_first_navigation_budget_ms": 6500,
        "n11_weak_first_navigation_budget_ms": 4500,
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-identity/v236235")
def runtime_identity_v236235():
    return {
        "ok": True,
        "runtime_version": "23.62.35",
        "architecture": "n11-adaptive-budget-scope-safety-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.35",
        "n11_scope_safety_hotfix": "strong-brand-model-signal-recomputed-inside-search-function",
        "n11_strong_brand_model_query_order": "v23.62.33-preserved",
        "n11_strong_first_navigation_budget_ms": 6500,
        "n11_weak_first_navigation_budget_ms": 4500,
        "n11_subsequent_query_navigation_budget": "v23.62.21-full-budget-preserved",
        "n11_timeout_selector_recovery": "v23.62.30-preserved",
        "idefix_zero_result_policy": "v23.62.32-preserved-fail-safe",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-identity/v236234")
def runtime_identity_v236234():
    return {
        "ok": True,
        "runtime_version": "23.62.34",
        "architecture": "n11-adaptive-strong-first-navigation-budget",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.34",
        "n11_strong_brand_model_query_order": "v23.62.33-preserved",
        "n11_strong_first_navigation_budget_ms": 6500,
        "n11_weak_first_navigation_budget_ms": 4500,
        "n11_subsequent_query_navigation_budget": "v23.62.21-full-budget-preserved",
        "n11_timeout_selector_recovery": "v23.62.30-preserved",
        "idefix_zero_result_policy": "v23.62.32-preserved-fail-safe",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236233")
def runtime_identity_v236233():
    return {
        "ok": True,
        "runtime_version": "23.62.33",
        "architecture": "n11-strong-brand-model-first-query-order",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.33",
        "n11_strong_brand_model_policy": "brand-present-plus-multi-token-model-start-brand-model-first",
        "n11_weak_identity_policy": "v23.62.10-model-first-order-preserved",
        "n11_timeout_selector_recovery": "v23.62.30-preserved",
        "idefix_zero_result_policy": "v23.62.32-preserved-fail-safe",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236232")
def runtime_identity_v236232():
    return {
        "ok": True,
        "runtime_version": "23.62.32",
        "architecture": "idefix-explicit-zero-result-early-exit",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.32",
        "idefix_query_policy": "v23.62.24-single-strong-brand-model-query-preserved",
        "idefix_zero_result_early_exit": "no-product-anchor-plus-explicit-zero-result-marker",
        "idefix_zero_result_probe_window": "bounded-8x150ms-visible-body-check",
        "idefix_ambiguous_empty_policy": "preserve-existing-full-search-path",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "n11_timeout_selector_recovery": "v23.62.30-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "n11_first_query_navigation_variance_guard": "v23.62.28-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236231")
def runtime_identity_v236231():
    return {
        "ok": True,
        "runtime_version": "23.62.31",
        "architecture": "pazarama-selector-ready-search-fast-path-and-phase-telemetry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.31",
        "pazarama_selector_ready_fast_path": "canonical-product-path-selector-150ms-settle-skip-networkidle",
        "pazarama_selector_not_ready_policy": "existing-domcontentloaded-settle-network-path-preserved",
        "pazarama_identity_detail_price_gates": "preserved",
        "n11_timeout_selector_recovery": "v23.62.30-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "n11_first_query_navigation_variance_guard": "v23.62.28-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236230")
def runtime_identity_v236230():
    return {
        "ok": True,
        "runtime_version": "23.62.30",
        "architecture": "n11-first-query-timeout-selector-recovery-probe",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.30",
        "n11_first_query_navigation_budget_ms": 4500,
        "n11_timeout_selector_recovery_probe_ms": 350,
        "n11_timeout_selector_recovery_settle_ms": 150,
        "n11_timeout_recovery_policy": "use-existing-dom-only-if-product-anchor-attached-else-existing-stronger-query-fallback",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "n11_first_query_navigation_variance_guard": "v23.62.28-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "n11_selector_ready_fast_path": "v23.62.26-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236237")
def runtime_identity_v236237():
    return {
        "ok": True,
        "runtime_version": "23.62.37",
        "architecture": "n11-strong-first-early-fallback-trigger",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.37",
        "n11_strong_brand_model_query_order": "v23.62.33-preserved",
        "n11_strong_first_early_fallback_ms": 3250,
        "n11_weak_first_navigation_budget_ms": 4500,
        "n11_subsequent_query_navigation_budget": "v23.62.21-full-budget-preserved",
        "n11_scope_safety_hotfix": "v23.62.35-preserved",
        "idefix_bounded_no_candidate_search": "v23.62.36-preserved",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236238")
def runtime_identity_v236238():
    return {
        "ok": True,
        "runtime_version": "23.62.38",
        "architecture": "itopya-bounded-browser-fallback-after-unhealthy-http-first",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.38",
        "itopya_http_first_policy": "v23.50-unhealthy-response-does-not-prove-no-candidate",
        "itopya_browser_navigation_budget_ms": 5000,
        "itopya_product_anchor_probe_max_ms": 1000,
        "itopya_no_anchor_policy": "fail-closed-no-candidate-after-bounded-browser-fallback",
        "n11_strong_first_early_fallback_ms": 3250,
        "n11_scope_safety_hotfix": "v23.62.35-preserved",
        "idefix_bounded_no_candidate_search": "v23.62.36-preserved",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236239")
def runtime_identity_v236239():
    return {
        "ok": True,
        "runtime_version": "23.62.39",
        "architecture": "n11-detail-http-soft-cap-and-light-browser-fallback",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.39",
        "n11_detail_http_timeout_seconds": 4.5,
        "n11_detail_browser_initial_wait_seconds": 1.0,
        "n11_detail_browser_navigation_budget_ms": 12000,
        "n11_detail_browser_scroll": "disabled",
        "n11_detail_security_and_strong_evidence_gates": "preserved",
        "n11_strong_first_early_fallback_ms": 3250,
        "itopya_bounded_browser_fallback": "v23.62.38-preserved",
        "idefix_bounded_no_candidate_search": "v23.62.36-preserved",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236240")
def runtime_identity_v236240():
    return {
        "ok": True,
        "runtime_version": "23.62.40",
        "architecture": "n11-strong-first-hysteresis-guard",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": "23.62.40",
        "n11_strong_brand_model_query_order": "v23.62.33-preserved",
        "n11_strong_first_hysteresis_ms": 3750,
        "n11_weak_first_navigation_budget_ms": 4500,
        "n11_detail_http_timeout_seconds": 4.5,
        "n11_detail_browser_initial_wait_seconds": 1.0,
        "n11_detail_browser_navigation_budget_ms": 12000,
        "n11_detail_browser_scroll": "disabled",
        "itopya_bounded_browser_fallback": "v23.62.38-preserved",
        "idefix_bounded_no_candidate_search": "v23.62.36-preserved",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236241")
def runtime_identity_v236241():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236242,
        "architecture": "force-refresh-runtime-version-single-source-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236242,
        "runtime_version_source": "single-source-v236241",
        "n11_strong_first_hysteresis_ms": 3750,
        "n11_weak_first_navigation_budget_ms": 4500,
        "n11_detail_http_timeout_seconds": 4.5,
        "n11_detail_browser_initial_wait_seconds": 1.0,
        "n11_detail_browser_navigation_budget_ms": 12000,
        "n11_detail_browser_scroll": "disabled",
        "itopya_bounded_browser_fallback": "v23.62.38-preserved",
        "idefix_bounded_no_candidate_search": "v23.62.36-preserved",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236242")
def runtime_identity_v236242():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236242,
        "architecture": "hepsiburada-persistent-security-challenge-early-fail-closed",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236242,
        "runtime_version_source": "single-source-v236242",
        "hepsiburada_challenge_recheck_ms": [1000],
        "hepsiburada_challenge_policy": "single-bounded-recheck-then-fail-closed",
        "security_challenge_bypass": "disabled",
        "n11_strong_first_hysteresis_ms": 3750,
        "n11_detail_http_timeout_seconds": 4.5,
        "itopya_bounded_browser_fallback": "v23.62.38-preserved",
        "idefix_bounded_no_candidate_search": "v23.62.36-preserved",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-identity/v236243")
def runtime_identity_v236243():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236243,
        "architecture": "n11-strong-first-4000ms-hysteresis-deadband",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236243,
        "runtime_version_source": "single-source-v236243",
        "n11_strong_brand_model_query_order": "v23.62.33-preserved",
        "n11_strong_first_hysteresis_ms": 4000,
        "n11_weak_first_navigation_budget_ms": 4500,
        "n11_detail_http_timeout_seconds": 4.5,
        "hepsiburada_challenge_recheck_ms": [1000],
        "hepsiburada_challenge_policy": "v23.62.42-preserved-single-bounded-recheck",
        "security_challenge_bypass": "disabled",
        "itopya_bounded_browser_fallback": "v23.62.38-preserved",
        "idefix_bounded_no_candidate_search": "v23.62.36-preserved",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }



@app.get("/api/runtime-identity/v236245")
def runtime_identity_v236244():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236245,
        "architecture": "hepsiburada-selector-ready-search-fast-path",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236245,
        "runtime_version_source": "single-source-v236244",
        "hepsiburada_challenge_path_phase_telemetry": "search-candidate-extraction-detail-goto-challenge-detection-recheck-cleanup-total",
        "hepsiburada_selector_ready_fast_path": "product-card-selector-150ms-settle-skip-networkidle",
        "hepsiburada_challenge_recheck_ms": [1000],
        "hepsiburada_challenge_policy": "v23.62.42-preserved-single-bounded-recheck",
        "security_challenge_bypass": "disabled",
        "n11_strong_first_hysteresis_ms": 4000,
        "n11_weak_first_navigation_budget_ms": 4500,
        "n11_detail_http_timeout_seconds": 4.5,
        "itopya_bounded_browser_fallback": "v23.62.38-preserved",
        "idefix_bounded_no_candidate_search": "v23.62.36-preserved",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236246")
def runtime_identity_v236246():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236246,
        "architecture": "n11-4250ms-hysteresis-and-detail-challenge-fail-fast",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236246,
        "runtime_version_source": "single-source-v236246",
        "n11_strong_brand_model_query_order": "v23.62.33-preserved",
        "n11_strong_first_hysteresis_ms": 4250,
        "n11_weak_first_navigation_budget_ms": 4500,
        "n11_detail_http_timeout_seconds": 4.5,
        "n11_detail_browser_initial_wait_seconds": 1.0,
        "n11_detail_browser_navigation_budget_ms": 12000,
        "n11_detail_browser_challenge_recheck_seconds": 0.5,
        "n11_detail_browser_scroll": "disabled",
        "n11_security_challenge_policy": "fail-closed-no-bypass",
        "hepsiburada_selector_ready_fast_path": "v23.62.45-preserved",
        "hepsiburada_challenge_recheck_ms": [1000],
        "security_challenge_bypass": "disabled",
        "itopya_bounded_browser_fallback": "v23.62.38-preserved",
        "idefix_bounded_no_candidate_search": "v23.62.36-preserved",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236247")
def runtime_identity_v236247():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236247,
        "architecture": "production-stability-baseline-regression-lock",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236247,
        "runtime_version_source": "single-source-v236247",
        "baseline_policy": "v23.62.46-behavior-frozen-no-performance-tweak",
        "n11_strong_first_hysteresis_ms": 4250,
        "n11_weak_first_navigation_budget_ms": 4500,
        "n11_detail_http_timeout_seconds": 4.5,
        "n11_detail_browser_challenge_recheck_seconds": 0.5,
        "n11_security_challenge_policy": "fail-closed-no-bypass",
        "hepsiburada_selector_ready_fast_path": "v23.62.45-preserved",
        "hepsiburada_challenge_recheck_ms": [1000],
        "itopya_bounded_browser_fallback": "v23.62.38-preserved",
        "idefix_bounded_no_candidate_search": "v23.62.36-preserved",
        "pazarama_selector_ready_fast_path": "v23.62.31-preserved",
        "trendyol_selector_ready_fast_path": "v23.62.29-preserved",
        "vatan_selector_ready_fast_path": "v23.62.27-preserved",
        "force_refresh_single_flight": "v23.62.25-preserved",
        "force_refresh_cooldown": "v23.62.25-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-identity/v236249")
def runtime_identity_v236249():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236249,
        "architecture": "rolling-window-regression-alarm-correctness-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236249,
        "runtime_version_source": "single-source-v236249",
        "behavior_policy": "v23.62.48-soak-observation-preserved-alarm-correctness-only",
        "soak_telemetry": "rolling-in-memory-observation-only",
        "soak_window_max_runs": _SOAK_V236248_MAX_RUNS,
        "regression_contract": {
            "expected_offer_count": _SOAK_V236248_EXPECTED_OFFERS,
            "expected_store_success_count": _SOAK_V236248_EXPECTED_SUCCESS_STORES,
            "n11_expected_status": "SUCCESS",
        },
        "n11_strong_first_hysteresis_ms": 4250,
        "n11_weak_first_navigation_budget_ms": 4500,
        "n11_detail_http_timeout_seconds": 4.5,
        "n11_detail_browser_challenge_recheck_seconds": 0.5,
        "hepsiburada_selector_ready_fast_path": "v23.62.45-preserved",
        "hepsiburada_challenge_recheck_ms": [1000],
        "itopya_bounded_browser_fallback": "v23.62.38-preserved",
        "idefix_bounded_no_candidate_search": "v23.62.36-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236249")
def runtime_soak_stability_v236249():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236249,
        "telemetry_scope": "localhost-force-refresh-process-lifetime-rolling-window-contract",
        "persistence": "in-memory-reset-on-process-restart",
        **snapshot,
    }


@app.get("/api/runtime-identity/v236250")
def runtime_identity_v236250():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236250,
        "architecture": "n11-verified-search-card-recovery-after-detail-exhaustion",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236250,
        "runtime_version_source": "single-source-v236250",
        "behavior_policy": "v23.62.49-soak-alarm-correctness-preserved-n11-recovery-only",
        "n11_verified_search_card_recovery": "post-detail-exhaustion-dom-card-single-price-score300-color2-exact-family",
        "n11_recovery_security_policy": "no-challenge-bypass-search-card-evidence-is-independent",
        "soak_telemetry": "v23.62.49-rolling-window-contract-preserved",
        "soak_window_max_runs": _SOAK_V236248_MAX_RUNS,
        "n11_strong_first_hysteresis_ms": 4250,
        "n11_weak_first_navigation_budget_ms": 4500,
        "n11_detail_http_timeout_seconds": 4.5,
        "n11_detail_browser_challenge_recheck_seconds": 0.5,
        "hepsiburada_selector_ready_fast_path": "v23.62.45-preserved",
        "hepsiburada_challenge_recheck_ms": [1000],
        "itopya_bounded_browser_fallback": "v23.62.38-preserved",
        "idefix_bounded_no_candidate_search": "v23.62.36-preserved",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "security_challenge_bypass": "disabled",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236250")
def runtime_soak_stability_v236250():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236250,
        "telemetry_scope": "localhost-force-refresh-process-lifetime-rolling-window-contract",
        "persistence": "in-memory-reset-on-process-restart",
        **snapshot,
    }


@app.get("/api/runtime-identity/v236257")
def runtime_identity_v236257():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236257,
        "architecture": "n11-browser-startup-timing-attribution-and-bat-bom-cleanup",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236256,
        "runtime_version_source": "single-source-v236257",
        "behavior_policy": "v23.62.56-behavior-preserved-browser-startup-timing-attribution-only",
        "n11_strong_first_navigation_budget_ms": 4500,
        "n11_timeout_selector_probe_ms": 350,
        "n11_detail_http_connection_pool": "v23.62.59-persistent-session-keepalive-dedicated-lane-only",
        "n11_detail_http_connection_pool_size": 2,
        "n11_query_recovery_flag_scope": "v23.62.56-initialize-false-per-query-before-navigation",
        "n11_browser_startup_telemetry": "v23.62.57-launch-plus-new-page-separated",
        "launcher_bat_bom": "removed-v23.62.57",
        "n11_near_miss_extra_selector_probe": "retired-v23.62.52",
        "n11_search_consolidation_policy": "single-4500ms-strong-first-plus-existing-350ms-selector-recovery",
        "n11_verified_search_card_recovery": "v23.62.50-preserved",
        "n11_challenge_to_recovery_wiring": "v23.62.53-n11-only-no-early-return",
        "n11_search_phase_telemetry": "v23.62.57-browser-startup-query-recovery-cleanup-postprocess",
        "n11_detail_http_timeout_seconds": 4.5,
        "n11_detail_browser_challenge_recheck_seconds": 0.5,
        "soak_telemetry": "v23.62.49-rolling-window-contract-preserved",
        "hepsiburada_selector_ready_fast_path": "v23.62.45-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236257")
def runtime_soak_stability_v236257():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236257,
        "telemetry_scope": "localhost-force-refresh-process-lifetime-rolling-window-contract",
        "persistence": "in-memory-reset-on-process-restart",
        **snapshot,
    }


@app.get("/api/runtime-identity/v236259")
def runtime_identity_v236259():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236259,
        "architecture": "n11-persistent-detail-http-connection-pool",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236259,
        "runtime_version_source": "single-source-v236259",
        "behavior_policy": "v23.62.58-preserved-n11-detail-transport-keepalive-only",
        "n11_strong_first_navigation_budget_ms": 4500,
        "n11_timeout_selector_probe_ms": 350,
        "n11_query_recovery_flag_scope": "v23.62.56-initialize-false-per-query-before-navigation",
        "n11_browser_startup_telemetry": "v23.62.57-launch-plus-new-page-separated-preserved",
        "launcher_bat_bom": "removed-v23.62.57-preserved",
        "n11_near_miss_extra_selector_probe": "retired-v23.62.52",
        "n11_search_consolidation_policy": "single-4500ms-strong-first-plus-existing-350ms-selector-recovery",
        "n11_verified_search_card_recovery": "v23.62.50-preserved",
        "n11_challenge_to_recovery_wiring": "v23.62.53-n11-only-no-early-return",
        "n11_search_phase_telemetry": "v23.62.57-browser-startup-query-recovery-cleanup-postprocess-preserved",
        "n11_detail_http_timeout_seconds": 4.5,
        "n11_detail_browser_challenge_recheck_seconds": 0.5,
        "soak_telemetry": "v23.62.49-rolling-window-contract-preserved",
        "hepsiburada_selector_ready_fast_path": "v23.62.45-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236259")
def runtime_soak_stability_v236259():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236259,
        "telemetry_scope": "localhost-force-refresh-process-lifetime-rolling-window-contract",
        "persistence": "in-memory-reset-on-process-restart",
        **snapshot,
    }


@app.get("/api/runtime-identity/v236260")
def runtime_identity_v236260():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236260,
        "architecture": "n11-cross-force-process-wide-detail-http-session",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236260,
        "runtime_version_source": "single-source-v236260",
        "behavior_policy": "v23.62.59-preserved-cross-force-session-scope-hotfix-only",
        "n11_detail_http_connection_pool": "v23.62.60-process-wide-shared-session-dedicated-lane-only",
        "n11_detail_http_connection_pool_size": 2,
        "n11_detail_http_session_scope": "process-wide-cross-force",
        "n11_strong_first_navigation_budget_ms": 4500,
        "n11_timeout_selector_probe_ms": 350,
        "n11_query_recovery_flag_scope": "v23.62.56-initialize-false-per-query-before-navigation",
        "n11_browser_startup_telemetry": "v23.62.57-launch-plus-new-page-separated-preserved",
        "n11_verified_search_card_recovery": "v23.62.50-preserved",
        "n11_challenge_to_recovery_wiring": "v23.62.53-n11-only-no-early-return",
        "n11_detail_http_timeout_seconds": 4.5,
        "n11_detail_browser_challenge_recheck_seconds": 0.5,
        "soak_telemetry": "v23.62.49-rolling-window-contract-preserved",
        "hepsiburada_selector_ready_fast_path": "v23.62.45-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236260")
def runtime_soak_stability_v236260():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236260,
        "telemetry_scope": "localhost-force-refresh-process-lifetime-rolling-window-contract",
        "persistence": "in-memory-reset-on-process-restart",
        **snapshot,
    }


@app.get("/api/runtime-identity/v236262")
def runtime_identity_v236261():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236262,
        "architecture": "n11-recent-verified-detail-trust-bridge",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236262,
        "runtime_version_source": "single-source-v236262",
        "behavior_policy": "v23.62.61-preserved-recent-verified-detail-bridge-only",
        "n11_force_inclusion_invariant": "USER_INGESTION-source-n11-reinsert-and-drop-lowest-non-n11",
        "n11_recent_verified_detail_bridge": "v23.62.62-same-global-same-url-30min-process-memory",
        "n11_recent_verified_detail_bridge_security": "requires-prior-normal-detail-canonical-color-verification-plus-single-price-exact-family-brand",
        "n11_force_store_count_policy": "preserve-original-cross-store-count",
        "n11_detail_http_connection_pool": "v23.62.60-process-wide-shared-session-preserved",
        "n11_detail_http_session_scope": "process-wide-cross-force",
        "n11_strong_first_navigation_budget_ms": 4500,
        "n11_timeout_selector_probe_ms": 350,
        "n11_verified_search_card_recovery": "v23.62.50-preserved",
        "n11_challenge_to_recovery_wiring": "v23.62.53-preserved",
        "n11_detail_http_timeout_seconds": 4.5,
        "soak_telemetry": "v23.62.49-rolling-window-contract-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged-outside-user-ingestion-inclusion-contract",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236262")
def runtime_soak_stability_v236261():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236262,
        "telemetry_scope": "localhost-force-refresh-process-lifetime-rolling-window-contract",
        "persistence": "in-memory-reset-on-process-restart",
        **snapshot,
    }

@app.get("/api/runtime-identity/v236266")
def runtime_identity_v236266():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236266,
        "architecture": "n11-cold-start-persisted-trust-and-url-unique-convergence-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236266,
        "runtime_version_source": "single-source-v236266",
        "behavior_policy": "v23.62.65-preserved-cold-start-persisted-trust-and-url-unique-convergence-only",
        "n11_force_inclusion_invariant": "USER_INGESTION-force-due-set-plus-post-cap-final-slot",
        "n11_force_store_count_policy": "source-n11-restored-before-due-set-and-post-cap-pin-preserve-count",
        "offer_unique_key_convergence": "v23.62.65-store-sku-authoritative-preserved",
        "offer_url_unique_convergence": "v23.62.66-preserve-existing-url-owner-no-conflicting-url-rekey",
        "n11_cold_start_trust_bootstrap": "v23.62.66-active-canonical-exact-url-recent-persisted-offer",
        "n11_recent_verified_detail_bridge": "v23.62.62-preserved",
        "n11_detail_http_connection_pool": "v23.62.60-process-wide-shared-session-preserved",
        "n11_strong_first_navigation_budget_ms": 4500,
        "n11_timeout_selector_probe_ms": 350,
        "n11_verified_search_card_recovery": "v23.62.50-preserved",
        "n11_challenge_to_recovery_wiring": "v23.62.53-preserved",
        "n11_detail_http_timeout_seconds": 4.5,
        "soak_telemetry": "v23.62.49-rolling-window-contract-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged-outside-user-ingestion-inclusion-contract",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236266")
def runtime_soak_stability_v236266():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236266,
        "telemetry_scope": "localhost-force-refresh-process-lifetime-rolling-window-contract",
        "persistence": "in-memory-reset-on-process-restart",
        **snapshot,
    }



@app.get("/api/runtime-identity/v236267")
def runtime_identity_v236267():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236267,
        "architecture": "production-stability-baseline-lock",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236267,
        "runtime_version_source": "single-source-v236267",
        "behavior_policy": "v23.62.66-frozen-no-scraping-change",
        "baseline_source": "v23.62.66-15-of-15-soak-pass",
        "baseline_observed_run_count": 15,
        "baseline_contract_pass_run_count": 15,
        "baseline_contract_violation_run_count": 0,
        "baseline_offer_count": 6,
        "baseline_store_success_count": 6,
        "baseline_total_latency_avg_seconds": 12.533,
        "baseline_total_latency_min_seconds": 11.093,
        "baseline_total_latency_max_seconds": 13.321,
        "baseline_n11_observations": 15,
        "baseline_n11_success_count": 15,
        "baseline_n11_success_rate_percent": 100.0,
        "baseline_n11_latency_avg_seconds": 6.745,
        "baseline_n11_latency_min_seconds": 5.967,
        "baseline_n11_latency_max_seconds": 8.796,
        "n11_force_inclusion_invariant": "v23.62.65-preserved",
        "offer_unique_key_convergence": "v23.62.65-preserved",
        "offer_url_unique_convergence": "v23.62.66-preserved",
        "n11_cold_start_trust_bootstrap": "v23.62.66-preserved",
        "n11_recent_verified_detail_bridge": "v23.62.62-preserved",
        "n11_detail_http_connection_pool": "v23.62.60-preserved",
        "n11_strong_first_navigation_budget_ms": 4500,
        "n11_timeout_selector_probe_ms": 350,
        "n11_detail_http_timeout_seconds": 4.5,
        "soak_regression_contract": {
            "expected_offer_count": 6,
            "expected_store_success_count": 6,
            "n11_expected_status": "SUCCESS",
        },
        "scraping_behavior": "v23.62.66-frozen",
        "behavior_fingerprint_manifest": "V23_62_67_BASELINE_FINGERPRINTS.json",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }



@app.get("/api/runtime-identity/v236290")
def runtime_identity_v236290():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236290,
        "architecture": "amazon-color-aware-preflight-and-score280-verified-card-bridge",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236290,
        "runtime_version_source": "single-source-v236290",
        "behavior_policy": "v23.62.89-preserved-amazon-color-aware-preflight-and-score280-verified-card-correctness-only",
        "database_continuity": "v23.62.85-preserved",
        "parser_capacity_provenance_guard_v236360": "reject-throughput-and-gpu-memory-from-generic-ram-storage-fallback",
        "parser_model_code_guard_v236360": "reject-mb-s-gb-s-throughput-tokens",
        "legacy_v2_migration_v236360": "disabled-live-canonicals-preserved",
        "database_write_policy_v236360": "no-repair-no-migration-parser-source-only",
        "canonical_residue_delete_scope_v236359": "explicit-20-id-merged-retired-zero-reference-allowlist-only",
        "canonical_residue_precondition_v236359": "zero-raw-zero-offer-zero-variant-zero-history-and-nonactive",
        "active_canonical_policy_v236359": "no-write",
        "identity_rewrite_policy_v236359": "disabled-no-v2-v3-bulk-rewrite",
        "automatic_merge_policy_v236359": "disabled-no-merge-no-relink-no-history-rewrite",
        "history_reconstruction_scope_v236358": "h27-to-gp28-null-h175-to-gp29-v30-h244-to-gp127-v155-only",
        "stale_variant_delete_scope_v236358": "v27-v154-v188-after-zero-fk-refs",
        "preserve_variant_scope_v236358": "v155-exact-snapshot-no-write",
        "null_variant_policy_v236358": "allowed-only-for-h27-because-current-offer-and-raw-both-null",
        "automatic_merge_policy_v236358": "disabled-no-canonical-merge-no-new-variant-creation",
        "history_relink_scope_v236357": "v18-and-v170-offer-linked-row-by-row-only",
        "history_relink_target_policy_v236357": "current-offer-and-raw-must-agree-on-non-null-gp-variant",
        "orphan_delete_scope_v236357": "delete-v18-v170-after-zero-all-fk-refs",
        "preserve_variant_scope_v236357": "v27-v154-v155-v188-no-write",
        "automatic_merge_policy_v236357": "disabled-no-canonical-merge-no-none-variant-guess",
        "gp142_rewrite_scope_v236356": "gp142-v174-raw184-raw185-only",
        "gp142_target_identity_v236356": "samsung-galaxy-tab-a11plus-6gb-128gb",
        "gp142_identity_key_v236356": "7e647cdc7b2919f9bc6bcf7d011e4b28",
        "gp148_lock_policy_v236356": "exact-snapshot-no-write-no-merge",
        "variant_rewrite_policy_v236356": "v174-color-gumus-model-code-removed",
        "raw_identity_policy_v236356": "raw184-raw185-relinked-to-new-gp142-identity-key-only",
        "history_owner_repair_scope_v236355": "h208-h209-h212-gp142-to-gp148-variant183-preserved",
        "history_owner_evidence_policy_v236355": "history-variant-offer-raw-must-agree-on-gp148-v183",
        "preserve_variant_scope_v236355": "v18-v27-v154-v155-v170-v188-no-write",
        "gp142_gp148_canonical_policy_v236355": "no-canonical-merge-no-capacity-rewrite",
        "orphan_safe_relink_scope_v236354": "20-audited-variant-history-relinks-only",
        "orphan_safe_delete_scope_v236354": "v161-v165-v166-v167-v184-v208-only",
        "orphan_preserve_scope_v236354": "v18-v27-v154-v155-v170-v188-no-write",
        "stale_retire_scope_v236354": "gp77-gp129-gp130-gp131-gp170-after-zero-child-zero-history-ownership",
        "history_provenance_policy_v236354": "linked-offer-and-raw-must-agree-on-single-target",
        "capacity_repair_scope_v236353": "gp39-gp64-gp74-gp101-gp123-gp126-gp169-only",
        "variant_key_normalization_v236353": "v40-v115-v151-v210-collision-safe-id-preserving-or-relink",
        "fail_closed_scope_v236353": "gp18-gp120-gp134-gp142-gp162-no-automatic-repair",
        "counter_rebuild_policy_v236353": "authoritative-child-counts-before-integrity-gate",
        "history_relink_policy": "v23.63.52-linked-offer-current-offer-and-raw-must-agree-before-relink",
        "gp173_capacity_repair_policy": "v23.63.52-non-source-quarantined-raw-capacity-consensus-only",
        "orphan_variant_cleanup_policy": "v23.63.52-delete-only-after-all-global-variant-fk-references-zero",
        "gp170_retire_policy": "v23.63.52-zero-raw-zero-offer-zero-variant-status-retired",
        "xaser_merge_policy": "v23.63.52-gp28-gp173-no-merge-family-conflict-fail-closed",
        "existing_canonical_repair_policy": "v23.63.51-gp174-evidence-gated-capacity-repair-only",
        "stale_canonical_policy": "v23.63.51-gp170-zero-child-status-retired-no-delete",
        "xaser_conflict_policy": "v23.63.51-gp28-gp173-fail-closed-no-merge-no-rewrite",
        "m2_storage_context_policy": "v23.63.50-unitless-storage-context-below-32gb-rejected",
        "explicit_tb_gb_policy": "v23.63.50-explicit-capacity-unit-authoritative",
        "capacity_provenance_policy": "v23.63.49-primary-evidence-first-labeled-spec-fallback",
        "storage_unit_policy": "v23.63.49-tb-normalized-to-1024gb",
        "maximum_ram_policy": "v23.63.49-maximum-upgrade-memory-never-system-ram",
        "gpu_memory_policy": "v23.63.49-vram-never-system-ram-or-storage",
        "amazon_phone_search_card_offer": "v23.62.90-dom-card-score280-exact-asin-detail-title-family-variant-storage-color-verified",
        "amazon_phone_search_card_price_band": "45pct-to-175pct-source-price",
        "amazon_phone_detail_fallback": "v23.62.89-preserved",
        "amazon_phone_prefilter": "v23.62.88-preserved",
        "amazon_phone_preflight_identity": "v23.62.90-family-variant-storage-plus-explicit-color",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-plus-v23.62.68-budget-cap",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }












@app.get("/api/runtime-identity/v236332")
def runtime_identity_v236332():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "v236331-production-baseline-maintenance-warning-cleanup",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236332",
        "behavior_policy": "v23.63.31-production-baseline-preserved-no-runtime-behavior-change",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_huawei_freebuds_se2_discovery": "v23.63.29-preserved-exact-direct-product-url",
        "turkcell_pasaj_huawei_freebuds_se2_price_provenance": "v23.63.30-preserved-exact-structured-price",
        "turkcell_pasaj_huawei_freebuds_se2_color_identity": "v23.63.31-preserved-exact-url-two-labeled-white-specs-no-conflict",
        "mediamarkt_redmi_note15pro_price_retry": "v23.63.28-preserved-single-card-price-opt-in-detail-retry",
        "turkcell_pasaj_redmi_watch5_active_discovery": "v23.63.26-preserved-exact-direct-product-url",
        "turkcell_pasaj_redmi_watch5_active_price_provenance": "v23.63.27-preserved-exact-url-exact-identity-structured-price-equals-generic-only",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-preserved-compact-capacity-url-lock",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "maintenance_scope": "smoke-test-invalid-escape-warning-cleanup-and-runtime-version-metadata-only",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-identity/v236333")
def runtime_identity_v236333():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "mediamarkt-redmi-watch5-active-mat-gumus-authoritative-direct-discovery",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236333",
        "behavior_policy": "v23.63.32-preserved-mediamarkt-exact-wearable-discovery-only",
        "database_continuity": "v23.62.85-preserved",
        "mediamarkt_redmi_watch5_active_discovery": "v23.63.33-exact-xiaomi-redmi-watch5-active-mat-gumus-direct-detail-url",
        "turkcell_pasaj_huawei_freebuds_se2_discovery": "v23.63.29-preserved-exact-direct-product-url",
        "turkcell_pasaj_huawei_freebuds_se2_price_provenance": "v23.63.30-preserved-exact-structured-price",
        "turkcell_pasaj_huawei_freebuds_se2_color_identity": "v23.63.31-preserved-exact-url-two-labeled-white-specs-no-conflict",
        "mediamarkt_redmi_note15pro_price_retry": "v23.63.28-preserved-single-card-price-opt-in-detail-retry",
        "turkcell_pasaj_redmi_watch5_active_discovery": "v23.63.26-preserved-exact-direct-product-url",
        "turkcell_pasaj_redmi_watch5_active_price_provenance": "v23.63.27-preserved-exact-url-exact-identity-structured-price-equals-generic-only",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-preserved-compact-capacity-url-lock",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 137,
    }


@app.get("/api/runtime-identity/v236334")
def runtime_identity_v236334():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "turkcell-macbook-neo-8gb-256gb-authoritative-direct-discovery",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236334",
        "behavior_policy": "v23.63.33-preserved-turkcell-exact-macbook-neo-discovery-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_macbook_neo_discovery": "v23.63.34-exact-apple-macbook-neo-8gb-256gb-direct-detail-url",
        "mediamarkt_redmi_watch5_active_discovery": "v23.63.33-preserved-exact-mat-gumus-direct-detail-url",
        "turkcell_pasaj_huawei_freebuds_se2_discovery": "v23.63.29-preserved-exact-direct-product-url",
        "turkcell_pasaj_huawei_freebuds_se2_price_provenance": "v23.63.30-preserved-exact-structured-price",
        "turkcell_pasaj_huawei_freebuds_se2_color_identity": "v23.63.31-preserved-exact-url-two-labeled-white-specs-no-conflict",
        "mediamarkt_redmi_note15pro_price_retry": "v23.63.28-preserved-single-card-price-opt-in-detail-retry",
        "turkcell_pasaj_redmi_watch5_active_discovery": "v23.63.26-preserved-exact-direct-product-url",
        "turkcell_pasaj_redmi_watch5_active_price_provenance": "v23.63.27-preserved-exact-url-exact-identity-structured-price-equals-generic-only",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-preserved-compact-capacity-url-lock",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 124,
    }



@app.get("/api/runtime-identity/v236341")
def runtime_identity_v236341():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "global-variant-referential-convergence-and-raw-scoped-binding",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236341",
        "behavior_policy": "v23.63.40-preserved-variant-referential-integrity-only",
        "database_continuity": "v23.62.85-preserved",
        "global_marketplace_offer_metadata": "v23.63.40-preserved-raw-products-authoritative-title-image",
        "variant_referential_convergence": "v23.63.41-active-offer-raw-variant-safe-convergence",
        "variant_binding_policy": "raw-product-scoped-never-global-product-wide-overwrite",
        "variant_safety_policy": "same-global-product-model-no-conflict-no-color-network-loss-fail-closed",
        "price_history_variant_relink": "linked-offer-history-only",
        "price_alert_variant_policy": "unchanged-no-bulk-rewrite",
        "gaminggen_policy": "v23.63.35-general-discovery-fail-closed-no-product-specific-macbook-recovery",
        "amazon_redmi_watch5_active_silver_recovery": "v23.63.35-preserved-exact-silver-wearable-card",
        "turkcell_pasaj_macbook_neo_discovery": "v23.63.34-preserved-exact-apple-macbook-neo-8gb-256gb-direct-detail-url",
        "mediamarkt_redmi_watch5_active_discovery": "v23.63.33-preserved-exact-mat-gumus-direct-detail-url",
        "turkcell_pasaj_huawei_freebuds_se2_discovery": "v23.63.29-preserved-exact-direct-product-url",
        "turkcell_pasaj_huawei_freebuds_se2_price_provenance": "v23.63.30-preserved-exact-structured-price",
        "turkcell_pasaj_huawei_freebuds_se2_color_identity": "v23.63.31-preserved-exact-url-two-labeled-white-specs-no-conflict",
        "mediamarkt_redmi_note15pro_price_retry": "v23.63.28-preserved-single-card-price-opt-in-detail-retry",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 144,
    }



@app.get("/api/runtime-identity/v236360")
def runtime_identity_v236348():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "provenance-aware-capacity-and-throughput-identity-safety-gate",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236360",
        "behavior_policy": "v23.63.59-preserved-parser-safety-only-no-db-rewrite",
        "database_continuity": "v23.62.85-preserved",
        "canonical_merge_policy": "v23.63.48-raw-consensus-marketed-variant-hard-boundary-approved-plan-only",
        "canonical_merge_transaction": "single-transaction-post-health-gate-commit-otherwise-rollback",
        "approved_merge_pair_count": 9,
        "variant_collision_policy": "canonical-key-precompute-collapse-before-rewrite",
        "variant_reference_policy": "raw-offer-price-history-relinked-before-variant-delete",
        "external_reference_policy": "alerts-bulk-links-reviews-fail-closed-skip-pair",
        "survivor_enrichment_policy": "fill-missing-canonical-evidence-never-overwrite-existing",
        "automatic_future_merge_policy": "disabled-no-brand-family-auto-merge",
        "model_code_provenance_guard": "v23.63.51-supply-suresi-plus-v236350-pseudo-classes-rejected",
        "quarantine_lifecycle_policy": "v23.63.45-preserved",
        "source_identity_quarantine": "v23.63.44-preserved",
        "variant_referential_convergence": "v23.63.41-preserved",
        "global_counter_integrity": "v23.63.43-preserved-and-post-merge-rebuilt",
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved-and-lifecycle-normalized",
        "canonical_test_global_product_id": 134,
    }


@app.get("/api/runtime-identity/v236347")
def runtime_identity_v236347():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "model-code-provenance-residue-capacity-suffix-lock",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236347",
        "behavior_policy": "v23.63.46-preserved-kapasitesi-pseudo-residue-only",
        "database_continuity": "v23.62.85-preserved",
        "model_code_provenance_guard": "v23.63.47-kapasitesi-and-v236346-pseudo-classes-rejected-at-all-write-paths",
        "model_code_cleanup": "v23.63.47-global-and-variant-kapasitesi-residue-cleanup-no-variant-key-rewrite",
        "asin_model_code_policy": "b0-asin-codes-preserved-not-treated-as-pseudo",
        "duplicate_merge_policy": "v23.63.46-preserved-fail-closed-no-auto-merge",
        "network_identity_policy": "v23.63.46-preserved-missing-network-is-not-equality-proof",
        "quarantine_lifecycle_policy": "v23.63.45-preserved",
        "source_identity_quarantine": "v23.63.44-preserved",
        "variant_referential_convergence": "v23.63.41-preserved",
        "accessory_identity_guard": "v23.63.42-preserved",
        "global_counter_integrity": "v23.63.43-preserved",
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved-and-lifecycle-normalized",
        "canonical_test_global_product_id": 83,
    }


@app.get("/api/runtime-identity/v236346")
def runtime_identity_v236346():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "canonical-evidence-provenance-hardening-no-auto-merge",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236346",
        "behavior_policy": "v23.63.45-preserved-canonical-evidence-provenance-only",
        "database_continuity": "v23.62.85-preserved",
        "model_code_provenance_guard": "v23.63.46-range-capacity-display-spec-pseudo-codes-rejected-at-all-canonical-write-paths",
        "model_code_cleanup": "v23.63.46-global-and-variant-pseudo-residue-cleanup-no-variant-key-rewrite",
        "asin_model_code_policy": "b0-asin-codes-preserved-not-treated-as-pseudo",
        "duplicate_merge_policy": "fail-closed-no-auto-merge-without-raw-evidence-consensus",
        "network_identity_policy": "explicit-marketed-phone-network-preserved-as-identity-evidence-missing-network-is-not-equality-proof",
        "quarantine_lifecycle_policy": "v23.63.45-preserved",
        "source_identity_quarantine": "v23.63.44-preserved",
        "variant_referential_convergence": "v23.63.41-preserved",
        "accessory_identity_guard": "v23.63.42-preserved",
        "global_counter_integrity": "v23.63.43-preserved",
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved-and-lifecycle-normalized",
        "canonical_test_global_product_id": 59,
    }


@app.get("/api/runtime-identity/v236345")
def runtime_identity_v236345():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "unified-quarantine-lifecycle-and-counter-convergence",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236345",
        "behavior_policy": "v23.63.44-preserved-quarantine-state-integrity-only",
        "database_continuity": "v23.62.85-preserved",
        "quarantine_lifecycle_policy": "v23.63.45-quarantined-implies-inactive-hidden",
        "price_quarantine_visibility": "v23.63.45-price-integrity-quarantine-hidden-by-construction",
        "quarantine_counter_convergence": "v23.63.45-post-price-audit-serving-eligible-active-offer-recount",
        "source_identity_quarantine": "v23.63.44-preserved-strong-independent-contradiction-fail-closed",
        "variant_referential_convergence": "v23.63.41-preserved",
        "accessory_identity_guard": "v23.63.42-preserved",
        "model_code_provenance_guard": "v23.63.43-preserved",
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved-and-lifecycle-normalized",
        "canonical_test_global_product_id": 43,
    }


@app.get("/api/runtime-identity/v236344")
def runtime_identity_v236344():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "raw-source-canonical-contradiction-quarantine",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236344",
        "behavior_policy": "v23.63.43-preserved-source-canonical-integrity-only",
        "database_continuity": "v23.62.85-preserved",
        "source_identity_quarantine": "v23.63.44-strong-independent-contradiction-fail-closed",
        "semantic_url_policy": "v23.63.44-semantic-store-product-class-conflict-only",
        "opaque_url_policy": "amazon-asin-url-never-used-as-semantic-mismatch-evidence",
        "canonical_override_policy": "gpu-or-same-prefix-series-conflict-required-for-quarantine",
        "weak_conflict_policy": "single-brand-or-model-parser-conflict-never-quarantines",
        "quarantine_storage": "existing-raw-reconciliation-and-global-offer-lifecycle-fields-no-new-table",
        "global_marketplace_offer_metadata": "v23.63.40-preserved-raw-products-authoritative-title-image",
        "variant_referential_convergence": "v23.63.41-preserved-active-offer-raw-variant-safe-convergence",
        "accessory_identity_guard": "v23.63.42-preserved-explicit-raw-brand-authoritative",
        "model_code_provenance_guard": "v23.63.43-preserved-specification-label-pseudo-codes-rejected",
        "global_counter_integrity": "v23.63.43-preserved-authoritative-child-counts",
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 43,
    }


@app.get("/api/runtime-identity/v236343")
def runtime_identity_v236343():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "canonical-model-code-provenance-and-global-counter-integrity",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236343",
        "behavior_policy": "v23.63.42-preserved-model-code-counter-integrity-only",
        "database_continuity": "v23.62.85-preserved",
        "global_marketplace_offer_metadata": "v23.63.40-preserved-raw-products-authoritative-title-image",
        "variant_referential_convergence": "v23.63.41-active-offer-raw-variant-safe-convergence",
        "variant_binding_policy": "raw-product-scoped-never-global-product-wide-overwrite",
        "variant_safety_policy": "same-global-product-model-no-conflict-no-color-network-loss-fail-closed",
        "price_history_variant_relink": "linked-offer-history-only",
        "price_alert_variant_policy": "unchanged-no-bulk-rewrite",
        "accessory_identity_guard": "v23.63.42-explicit-raw-brand-authoritative-over-compatibility-target",
        "accessory_capability_guard": "v23.63.42-no-target-device-ram-storage-screen-inheritance",
        "accessory_identity_convergence": "v23.63.42-all-matched-raws-agree-no-collision-fail-closed",
        "model_code_provenance_guard": "v23.63.43-specification-label-pseudo-codes-rejected",
        "model_code_cleanup": "v23.63.43-global-and-variant-pseudo-payload-cleanup-no-variant-key-rewrite",
        "global_counter_integrity": "v23.63.43-authoritative-raw-products-and-active-global-offers",
        "bulk_identity_counter_policy": "v23.63.43-never-count-staging-links-as-raw-products",
        "gaminggen_policy": "v23.63.35-general-discovery-fail-closed-no-product-specific-macbook-recovery",
        "amazon_redmi_watch5_active_silver_recovery": "v23.63.35-preserved-exact-silver-wearable-card",
        "turkcell_pasaj_macbook_neo_discovery": "v23.63.34-preserved-exact-apple-macbook-neo-8gb-256gb-direct-detail-url",
        "mediamarkt_redmi_watch5_active_discovery": "v23.63.33-preserved-exact-mat-gumus-direct-detail-url",
        "turkcell_pasaj_huawei_freebuds_se2_discovery": "v23.63.29-preserved-exact-direct-product-url",
        "turkcell_pasaj_huawei_freebuds_se2_price_provenance": "v23.63.30-preserved-exact-structured-price",
        "turkcell_pasaj_huawei_freebuds_se2_color_identity": "v23.63.31-preserved-exact-url-two-labeled-white-specs-no-conflict",
        "mediamarkt_redmi_note15pro_price_retry": "v23.63.28-preserved-single-card-price-opt-in-detail-retry",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 144,
    }


@app.get("/api/runtime-identity/v236340")
def runtime_identity_v236340():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "global-marketplace-raw-product-join-integrity-lock",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236340",
        "behavior_policy": "v23.63.39-preserved-global-marketplace-serving-join-fix-only",
        "database_continuity": "v23.62.85-preserved",
        "global_marketplace_offer_metadata": "v23.63.40-raw-products-authoritative-title-image-with-global-product-guard",
        "global_marketplace_id_space_policy": "raw_product_id-never-joins-legacy-products-id",
        "variant_convergence": "deferred-v23.63.41-no-change",
        "gaminggen_policy": "v23.63.35-general-discovery-fail-closed-no-product-specific-macbook-recovery",
        "amazon_redmi_watch5_active_silver_recovery": "v23.63.35-preserved-exact-silver-wearable-card",
        "turkcell_pasaj_macbook_neo_discovery": "v23.63.34-preserved-exact-apple-macbook-neo-8gb-256gb-direct-detail-url",
        "mediamarkt_redmi_watch5_active_discovery": "v23.63.33-preserved-exact-mat-gumus-direct-detail-url",
        "turkcell_pasaj_huawei_freebuds_se2_discovery": "v23.63.29-preserved-exact-direct-product-url",
        "turkcell_pasaj_huawei_freebuds_se2_price_provenance": "v23.63.30-preserved-exact-structured-price",
        "turkcell_pasaj_huawei_freebuds_se2_color_identity": "v23.63.31-preserved-exact-url-two-labeled-white-specs-no-conflict",
        "mediamarkt_redmi_note15pro_price_retry": "v23.63.28-preserved-single-card-price-opt-in-detail-retry",
        "turkcell_pasaj_redmi_watch5_active_discovery": "v23.63.26-preserved-exact-direct-product-url",
        "turkcell_pasaj_redmi_watch5_active_price_provenance": "v23.63.27-preserved-exact-url-exact-identity-structured-price-equals-generic-only",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-preserved-compact-capacity-url-lock",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 144,
    }


@app.get("/api/runtime-identity/v236339")
def runtime_identity_v236339():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "v236335-production-baseline-restored-gaminggen-experimental-branch-removed",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236339",
        "behavior_policy": "v23.63.35-production-behavior-restored-no-v236336-v236338-gaminggen-experimental-runtime-code",
        "database_continuity": "v23.62.85-preserved",
        "gaminggen_policy": "v23.63.35-general-discovery-fail-closed-no-product-specific-macbook-recovery",
        "amazon_redmi_watch5_active_silver_recovery": "v23.63.35-preserved-exact-silver-wearable-card",
        "turkcell_pasaj_macbook_neo_discovery": "v23.63.34-preserved-exact-apple-macbook-neo-8gb-256gb-direct-detail-url",
        "mediamarkt_redmi_watch5_active_discovery": "v23.63.33-preserved-exact-mat-gumus-direct-detail-url",
        "turkcell_pasaj_huawei_freebuds_se2_discovery": "v23.63.29-preserved-exact-direct-product-url",
        "turkcell_pasaj_huawei_freebuds_se2_price_provenance": "v23.63.30-preserved-exact-structured-price",
        "turkcell_pasaj_huawei_freebuds_se2_color_identity": "v23.63.31-preserved-exact-url-two-labeled-white-specs-no-conflict",
        "mediamarkt_redmi_note15pro_price_retry": "v23.63.28-preserved-single-card-price-opt-in-detail-retry",
        "turkcell_pasaj_redmi_watch5_active_discovery": "v23.63.26-preserved-exact-direct-product-url",
        "turkcell_pasaj_redmi_watch5_active_price_provenance": "v23.63.27-preserved-exact-url-exact-identity-structured-price-equals-generic-only",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-preserved-compact-capacity-url-lock",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 124,
    }


@app.get("/api/runtime-identity/v236335")
def runtime_identity_v236335():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "amazon-redmi-watch5-active-silver-verified-search-card-recovery",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236335",
        "behavior_policy": "v23.63.34-preserved-amazon-exact-silver-wearable-card-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_macbook_neo_discovery": "v23.63.34-exact-apple-macbook-neo-8gb-256gb-direct-detail-url",
        "mediamarkt_redmi_watch5_active_discovery": "v23.63.33-preserved-exact-mat-gumus-direct-detail-url",
        "turkcell_pasaj_huawei_freebuds_se2_discovery": "v23.63.29-preserved-exact-direct-product-url",
        "turkcell_pasaj_huawei_freebuds_se2_price_provenance": "v23.63.30-preserved-exact-structured-price",
        "turkcell_pasaj_huawei_freebuds_se2_color_identity": "v23.63.31-preserved-exact-url-two-labeled-white-specs-no-conflict",
        "mediamarkt_redmi_note15pro_price_retry": "v23.63.28-preserved-single-card-price-opt-in-detail-retry",
        "turkcell_pasaj_redmi_watch5_active_discovery": "v23.63.26-preserved-exact-direct-product-url",
        "turkcell_pasaj_redmi_watch5_active_price_provenance": "v23.63.27-preserved-exact-url-exact-identity-structured-price-equals-generic-only",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-preserved-compact-capacity-url-lock",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "amazon_redmi_watch5_active_silver_recovery": "v23.63.35-dom-card-score316-single-price-fresh-detail-silver-title-no-bypass",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 124,
    }


@app.get("/api/runtime-soak-stability/v236332")
def runtime_soak_stability_v236332():
    data = runtime_soak_stability_v236331()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236323
    return data

@app.get("/api/runtime-identity/v236331")
def runtime_identity_v236331():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "turkcell-freebuds-se2-authoritative-labeled-white-color",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236331",
        "behavior_policy": "v23.63.30-preserved-turkcell-exact-audio-labeled-color-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_huawei_freebuds_se2_discovery": "v23.63.29-preserved-exact-direct-product-url",
        "turkcell_pasaj_huawei_freebuds_se2_price_provenance": "v23.63.30-preserved-exact-structured-price",
        "turkcell_pasaj_huawei_freebuds_se2_color_identity": "v23.63.31-exact-url-two-labeled-white-specs-no-conflict-before-normal-audio-gates",
        "mediamarkt_redmi_note15pro_price_retry": "v23.63.28-preserved-single-card-price-opt-in-detail-retry",
        "turkcell_pasaj_redmi_watch5_active_discovery": "v23.63.26-preserved-exact-direct-product-url",
        "turkcell_pasaj_redmi_watch5_active_price_provenance": "v23.63.27-preserved-exact-url-exact-identity-structured-price-equals-generic-only",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-preserved-compact-capacity-url-lock",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236331")
def runtime_soak_stability_v236331():
    data = runtime_soak_stability_v236330()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236323
    return data

@app.get("/api/runtime-identity/v236330")
def runtime_identity_v236330():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "turkcell-huawei-freebuds-se2-structured-price-provenance",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236330",
        "behavior_policy": "v23.63.29-preserved-turkcell-exact-audio-price-provenance-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_huawei_freebuds_se2_discovery": "v23.63.29-preserved-exact-direct-product-url",
        "turkcell_pasaj_huawei_freebuds_se2_price_provenance": "v23.63.30-exact-url-exact-identity-structured-price-equals-generic-only",
        "mediamarkt_redmi_note15pro_price_retry": "v23.63.28-preserved-single-card-price-opt-in-detail-retry",
        "turkcell_pasaj_redmi_watch5_active_discovery": "v23.63.26-preserved-exact-direct-product-url",
        "turkcell_pasaj_redmi_watch5_active_price_provenance": "v23.63.27-preserved-exact-url-exact-identity-structured-price-equals-generic-only",
        "turkcell_pasaj_price_provenance": "v23.63.07-preserved-with-v236327-wearable-and-v236330-audio-structured-fallbacks",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-preserved-compact-capacity-url-lock",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236330")
def runtime_soak_stability_v236330():
    data = runtime_soak_stability_v236329()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236323
    return data

@app.get("/api/runtime-identity/v236329")
def runtime_identity_v236329():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "turkcell-huawei-freebuds-se2-authoritative-direct-discovery",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236329",
        "behavior_policy": "v23.63.28-preserved-turkcell-exact-audio-discovery-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_huawei_freebuds_se2_discovery": "v23.63.29-exact-huawei-freebuds-se2-direct-product-url-before-normal-detail-gates",
        "mediamarkt_redmi_note15pro_price_retry": "v23.63.28-preserved-single-card-price-opt-in-detail-retry",
        "turkcell_pasaj_redmi_watch5_active_discovery": "v23.63.26-preserved-exact-direct-product-url",
        "turkcell_pasaj_redmi_watch5_active_price_provenance": "v23.63.27-preserved-exact-url-exact-identity-structured-price-equals-generic-only",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-preserved-compact-capacity-url-lock",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236329")
def runtime_soak_stability_v236329():
    data = runtime_soak_stability_v236328()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236323
    return data

@app.get("/api/runtime-identity/v236328")
def runtime_identity_v236328():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "mediamarkt-redmi-note15pro-verified-card-price-detail-retry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236328",
        "behavior_policy": "v23.63.27-preserved-mediamarkt-detail-price-retry-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_redmi_watch5_active_discovery": "v23.63.26-preserved-exact-direct-product-url",
        "turkcell_pasaj_redmi_watch5_active_price_provenance": "v23.63.28-exact-url-exact-identity-structured-price-equals-generic-only",
        "turkcell_pasaj_price_provenance": "v23.63.07-preserved-visible-direct-sale-lock-with-v236328-wearable-structured-fallback",
        "mediamarkt_redmi_note15pro_price_retry": "v23.63.28-single-card-price-opt-in-detail-retry-normal-identity-color-gates-preserved",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-preserved-compact-capacity-url-lock",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236328")
def runtime_soak_stability_v236328():
    data = runtime_soak_stability_v236326()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236323
    return data

@app.get("/api/runtime-identity/v236326")
def runtime_identity_v236326():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "turkcell-redmi-watch5-active-authoritative-direct-discovery",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236326",
        "behavior_policy": "v23.63.25-preserved-turkcell-wearable-discovery-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_redmi_watch5_active_discovery": "v23.63.26-exact-xiaomi-redmi-watch-5-active-direct-product-url-before-normal-detail-gates",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.25-preserved-exact-white-card",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-preserved-compact-capacity-url-lock",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236326")
def runtime_soak_stability_v236326():
    data = runtime_soak_stability_v236325()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236323
    return data

@app.get("/api/runtime-identity/v236325")
def runtime_identity_v236325():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236323,
        "architecture": "n11-freebuds-se2-white-normalized-url-token-lock-fix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236323,
        "runtime_version_source": "single-source-v236325",
        "behavior_policy": "v23.63.24-preserved-n11-normalized-url-token-lock-only",
        "database_continuity": "v23.62.85-preserved",
        "n11_freebuds_se2_white_search_card_recovery": "v23.63.23-preserved-score338-exact-white-url-tight-price-cluster-no-bypass",
        "n11_freebuds_se2_white_normalization_fix": "v23.63.25-use-existing-v236283-fold-no-undefined-helper",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-preserved-compact-capacity-url-lock",
        "hepsiburada_security_challenge_recheck": "v23.63.20-preserved-two-bounded-rechecks-no-bypass",
        "hepsiburada_transient_navigation": "v23.63.16-preserved-same-url-single-retry-on-err-http2-protocol-error-only",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236325")
def runtime_soak_stability_v236325():
    data = runtime_soak_stability_v236322()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236323
    return data

@app.get("/api/runtime-identity/v236322")
def runtime_identity_v236322():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236322,
        "architecture": "hepsiburada-macbook-neo-compact-capacity-url-lock",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236322,
        "runtime_version_source": "single-source-v236322",
        "behavior_policy": "v23.63.21-preserved-macbook-url-capacity-token-normalization-only",
        "database_continuity": "v23.62.85-preserved",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-preserved-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_macbook_url_capacity_lock": "v23.63.22-accept-spaced-or-compact-storage-and-ram-tokens-only",
        "hepsiburada_security_challenge_recheck": "v23.63.20-preserved-two-bounded-rechecks-no-bypass",
        "hepsiburada_transient_navigation": "v23.63.16-preserved-same-url-single-retry-on-err-http2-protocol-error-only",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236322")
def runtime_soak_stability_v236322():
    data = runtime_soak_stability_v236321()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236322
    return data

@app.get("/api/runtime-identity/v236321")
def runtime_identity_v236321():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236321,
        "architecture": "hepsiburada-verified-search-card-audio-laptop-recovery",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236321,
        "runtime_version_source": "single-source-v236321",
        "behavior_policy": "v23.63.20-preserved-hepsiburada-trusted-dom-card-recovery-only",
        "database_continuity": "v23.62.85-preserved",
        "hepsiburada_verified_search_card_recovery": "v23.63.21-trusted-final-price-exact-freebuds-se2-or-macbook-neo-only",
        "hepsiburada_security_challenge_recheck": "v23.63.20-preserved-two-bounded-rechecks-no-bypass",
        "hepsiburada_transient_navigation": "v23.63.16-preserved-same-url-single-retry-on-err-http2-protocol-error-only",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236321")
def runtime_soak_stability_v236321():
    data = runtime_soak_stability_v236320()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236321
    return data

@app.get("/api/runtime-identity/v236320")
def runtime_identity_v236320():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236320,
        "architecture": "hepsiburada-security-challenge-bounded-second-recheck",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236320,
        "runtime_version_source": "single-source-v236320",
        "behavior_policy": "v23.63.19-preserved-hepsiburada-challenge-recheck-window-only",
        "database_continuity": "v23.62.85-preserved",
        "hepsiburada_security_challenge_recheck": "v23.63.20-two-bounded-rechecks-1000ms-then-2000ms-no-bypass",
        "hepsiburada_security_challenge_policy": "same-persistent-session-observe-only-fail-closed",
        "hepsiburada_transient_navigation": "v23.63.16-preserved-same-url-single-retry-on-err-http2-protocol-error-only",
        "idefix_curated_canonical_evidence": "v23.63.19-preserved-clean-scoring-label-carried-to-detail-binding",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "idefix_general_discovery": "v23.63.00-preserved-brand-catalog-recovery",
        "beymen_store": "v23.63.09-preserved-no-candidate-is-valid-when-model-not-listed",
        "turkcell_pasaj_price_provenance": "v23.63.07-preserved",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236320")
def runtime_soak_stability_v236320():
    data = runtime_soak_stability_v236319()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236320
    return data

@app.get("/api/runtime-identity/v236319")
def runtime_identity_v236319():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236319,
        "architecture": "idefix-curated-canonical-evidence-label-carry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236319,
        "runtime_version_source": "single-source-v236319",
        "behavior_policy": "v23.63.18-preserved-idefix-clean-scoring-label-carried-into-detail-evidence-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "hepsiburada_transient_navigation": "v23.63.16-preserved-same-url-single-retry-on-err-http2-protocol-error-only",
        "idefix_apple_iphone_discovery": "v23.63.17-preserved-curated-iphone-landing",
        "idefix_apple_iphone_curated_network_badge": "v23.63.18-preserved-scoring-only-5g-badge-neutralization",
        "idefix_curated_canonical_evidence": "v23.63.19-clean-scoring-label-carried-to-detail-binding-original-display-label-preserved",
        "idefix_general_discovery": "v23.63.00-preserved-brand-catalog-recovery",
        "beymen_store": "v23.63.09-preserved-no-candidate-is-valid-when-model-not-listed",
        "turkcell_pasaj_price_provenance": "v23.63.07-preserved",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236319")
def runtime_soak_stability_v236319():
    data = runtime_soak_stability_v236318()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236319
    return data

@app.get("/api/runtime-identity/v236318")
def runtime_identity_v236318():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236318,
        "architecture": "idefix-apple-iphone-curated-5g-badge-identity-neutralization",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236318,
        "runtime_version_source": "single-source-v236318",
        "behavior_policy": "v23.63.17-preserved-idefix-curated-card-network-badge-noise-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "hepsiburada_transient_navigation": "v23.63.16-preserved-same-url-single-retry-on-err-http2-protocol-error-only",
        "idefix_apple_iphone_discovery": "v23.63.17-preserved-curated-iphone-landing",
        "idefix_apple_iphone_curated_network_badge": "v23.63.18-scoring-only-5g-badge-neutralization-when-source-network-unspecified-and-core-identity-exact",
        "idefix_general_discovery": "v23.63.00-preserved-brand-catalog-recovery",
        "beymen_store": "v23.63.09-preserved-no-candidate-is-valid-when-model-not-listed",
        "turkcell_pasaj_price_provenance": "v23.63.07-preserved",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236318")
def runtime_soak_stability_v236318():
    data = runtime_soak_stability_v236317()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236318
    return data

@app.get("/api/runtime-identity/v236317")
def runtime_identity_v236317():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236317,
        "architecture": "idefix-apple-iphone-curated-landing-recovery",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236317,
        "runtime_version_source": "single-source-v236317",
        "behavior_policy": "v23.63.16-preserved-idefix-apple-iphone-discovery-recall-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "hepsiburada_transient_navigation": "v23.63.16-preserved-same-url-single-retry-on-err-http2-protocol-error-only",
        "idefix_apple_iphone_discovery": "v23.63.17-curated-iphone-landing-after-search-shell-before-normal-match-gates",
        "idefix_general_discovery": "v23.63.00-preserved-brand-catalog-recovery",
        "beymen_store": "v23.63.09-preserved-no-candidate-is-valid-when-model-not-listed",
        "turkcell_pasaj_price_provenance": "v23.63.07-preserved",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236317")
def runtime_soak_stability_v236317():
    data = runtime_soak_stability_v236316()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236317
    return data

@app.get("/api/runtime-identity/v236316")
def runtime_identity_v236316():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236316,
        "architecture": "hepsiburada-transient-http2-search-navigation-single-retry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236316,
        "runtime_version_source": "single-source-v236316",
        "behavior_policy": "v23.63.15-preserved-hepsiburada-transport-reliability-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_ios_discovery": "v23.63.12-preserved-ios-category-generation-path-no-ram-slug",
        "turkcell_pasaj_ios_url_identity": "v23.63.13-preserved-authoritative-path-name-model",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "pttavm_store": "v23.63.10-seller-brand-separation-preserved",
        "pttavm_transient_navigation": "v23.63.15-preserved-same-url-single-retry-on-err-http-response-code-failure-only",
        "hepsiburada_transient_navigation": "v23.63.16-same-url-single-retry-on-err-http2-protocol-error-only",
        "hepsiburada_retry_policy": "bounded-2-total-attempts-no-security-challenge-bypass-fail-closed",
        "beymen_store": "v23.63.09-preserved-no-candidate-is-valid-when-model-not-listed",
        "turkcell_pasaj_price_provenance": "v23.63.07-preserved",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236316")
def runtime_soak_stability_v236316():
    data = runtime_soak_stability_v236315()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236316
    return data

@app.get("/api/runtime-identity/v236315")
def runtime_identity_v236315():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236315,
        "architecture": "pttavm-transient-search-navigation-single-retry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236315,
        "runtime_version_source": "single-source-v236315",
        "behavior_policy": "v23.63.14-preserved-pttavm-transport-reliability-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_ios_discovery": "v23.63.12-preserved-ios-category-generation-path-no-ram-slug",
        "turkcell_pasaj_ios_url_identity": "v23.63.13-preserved-authoritative-path-name-model",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-preserved-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "pttavm_store": "v23.63.10-seller-brand-separation-preserved",
        "pttavm_transient_navigation": "v23.63.15-same-url-single-retry-on-err-http-response-code-failure-only",
        "pttavm_retry_policy": "bounded-2-total-attempts-fail-closed",
        "beymen_store": "v23.63.09-preserved-no-candidate-is-valid-when-model-not-listed",
        "turkcell_pasaj_price_provenance": "v23.63.07-preserved",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236315")
def runtime_soak_stability_v236315():
    data = runtime_soak_stability_v236314()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236315
    return data

@app.get("/api/runtime-identity/v236314")
def runtime_identity_v236314():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236314,
        "architecture": "turkcell-ios-canonical-candidate-identity-override",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236314,
        "runtime_version_source": "single-source-v236314",
        "behavior_policy": "v23.63.13-preserved-turkcell-ios-canonical-candidate-identity-correctness-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_ios_discovery": "v23.63.12-preserved-ios-category-generation-path-no-ram-slug",
        "turkcell_pasaj_ios_url_identity": "v23.63.13-preserved-authoritative-path-name-model",
        "turkcell_pasaj_ios_canonical_candidate_identity": "v23.63.14-authoritative-url-match-copy-excludes-sibling-capacity-noise",
        "pttavm_store": "v23.63.10-seller-brand-separation-preserved",
        "beymen_store": "v23.63.09-preserved-no-candidate-is-valid-when-model-not-listed",
        "turkcell_pasaj_price_provenance": "v23.63.07-preserved",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236314")
def runtime_soak_stability_v236314():
    data = runtime_soak_stability_v236310()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236314
    return data

@app.get("/api/runtime-identity/v236310")
def runtime_identity_v236310():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236310,
        "architecture": "pttavm-marketplace-seller-brand-separation-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236310,
        "runtime_version_source": "single-source-v236310",
        "behavior_policy": "v23.63.09-preserved-pttavm-seller-as-brand-correctness-only",
        "database_continuity": "v23.62.85-preserved",
        "pttavm_store": "v23.63.08-preserved",
        "pttavm_marketplace_brand_policy": "v23.63.10-jsonld-seller-not-manufacturer-title-derived-brand-only-when-explicit",
        "beymen_store": "v23.63.09-preserved-no-candidate-is-valid-when-model-not-listed",
        "turkcell_pasaj_price_provenance": "v23.63.07-preserved",
        "source_variant_anchor": "v23.63.04-preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236310")
def runtime_soak_stability_v236310():
    data = runtime_soak_stability_v236309()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236310
    return data

@app.get("/api/runtime-identity/v236309")
def runtime_identity_v236309():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236309,
        "architecture": "beymen-phone-category-and-detail-store-onboarding",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236309,
        "runtime_version_source": "single-source-v236309",
        "behavior_policy": "v23.63.08-preserved-beymen-store-integration-only",
        "database_continuity": "v23.62.85-preserved",
        "pttavm_store": "v23.63.08-search-adapter-detail-registry-enabled",
        "pttavm_search": "https://www.pttavm.com/arama?q=canonical-query",
        "pttavm_product_url_contract": "root-slug-ending-p-id",
        "pttavm_identity": "existing-canonical-family-variant-network-storage-color-gates",
        "beymen_store": "v23.63.09-phone-category-search-adapter-detail-registry-enabled",
        "beymen_product_url_contract": "/tr/p_slug_numeric-id",
        "beymen_identity": "existing-canonical-family-variant-network-storage-color-gates",
        "teknosa_store": "existing-v23.62.23-plus-v23.62.7-detail-preserved",
        "turkcell_pasaj_price_provenance": "v23.63.07-preserved",
        "source_variant_anchor": "v23.63.04-preserved",
        "n11_force_inclusion_invariant": "preserved",
        "force_store_budget": 14,
        "security_challenge_bypass": "disabled",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236309")
def runtime_soak_stability_v236309():
    data = runtime_soak_stability_v236307()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236309
    return data

@app.get("/api/runtime-identity/v236307")
def runtime_identity_v236307():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236307,
        "architecture": "turkcell-contract-price-hard-reject-and-direct-sale-provenance-lock",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236307,
        "runtime_version_source": "single-source-v236307",
        "behavior_policy": "v23.63.06-preserved-turkcell-alternative-payment-hard-reject-only",
        "database_continuity": "v23.62.85-preserved",
        "source_variant_anchor": "v23.63.04-preserved",
        "turkcell_pasaj_force_inclusion": "v23.63.04-preserved",
        "turkcell_pasaj_price_provenance": "v23.63.07-contract-installment-insurance-hard-reject",
        "turkcell_pasaj_contract_price_policy": "peşine-kontratli-or-tarifede-kalma-context-hard-reject",
        "turkcell_pasaj_direct_sale_policy": "seller-shipping-context-min-score-5-fail-closed",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-and-protected-with-turkcell",
        "force_store_budget": 12,
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged-outside-turkcell-price-provenance-correctness",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236307")
def runtime_soak_stability_v236307():
    data = runtime_soak_stability_v236306()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236307
    return data

@app.get("/api/runtime-identity/v236306")
def runtime_identity_v236306():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236306,
        "architecture": "startup-smoke-version-coherence-and-source-anchor-runtime-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236306,
        "runtime_version_source": "single-source-v236306",
        "behavior_policy": "v23.63.05-runtime-constructor-fix-preserved-startup-smoke-coherence-only",
        "database_continuity": "v23.62.85-preserved",
        "source_variant_anchor": "v23.63.04-preserved",
        "source_anchor_product_constructor": "v23.63.05-preserved-all-required-product-fields-explicit",
        "startup_smoke_contract": "v23.63.06-version-and-preserved-symbols-coherent",
        "turkcell_pasaj_force_inclusion": "v23.63.04-preserved",
        "turkcell_pasaj_price_provenance": "v23.63.03-preserved",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-and-protected-with-turkcell",
        "force_store_budget": 12,
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged-outside-startup-smoke-coherence",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236306")
def runtime_soak_stability_v236306():
    data = runtime_soak_stability_v236305()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236306
    return data

@app.get("/api/runtime-identity/v236305")
def runtime_identity_v236305():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236305,
        "architecture": "stable-source-anchor-product-constructor-compatibility-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236305,
        "runtime_version_source": "single-source-v236305",
        "behavior_policy": "v23.63.04-preserved-product-dataclass-constructor-compatibility-only",
        "database_continuity": "v23.62.85-preserved",
        "source_variant_anchor": "v23.63.04-preserved",
        "source_anchor_product_constructor": "v23.63.05-all-required-product-fields-explicit",
        "turkcell_pasaj_force_inclusion": "v23.63.04-preserved",
        "turkcell_pasaj_price_provenance": "v23.63.03-preserved",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-and-protected-with-turkcell",
        "force_store_budget": 12,
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged-outside-constructor-hotfix",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236305")
def runtime_soak_stability_v236305():
    data = runtime_soak_stability_v236304()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236305
    return data

@app.get("/api/runtime-identity/v236304")
def runtime_identity_v236304():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236304,
        "architecture": "stable-source-variant-anchor-and-turkcell-force-inclusion-contract",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236304,
        "runtime_version_source": "single-source-v236304",
        "behavior_policy": "v23.63.03-preserved-source-anchor-and-force-roster-correctness-only",
        "database_continuity": "v23.62.85-preserved",
        "source_variant_anchor": "v23.63.04-canonical-color-then-oldest-explicit-variant-color-then-oldest-raw",
        "source_store_drift_policy": "new-offers-cannot-become-next-force-source-by-updated-at",
        "turkcell_pasaj_force_inclusion": "v23.63.04-user-ingestion-protected-due-set",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-and-protected-with-turkcell",
        "force_store_budget": 12,
        "force_store_budget_policy": "protected-n11-and-turkcell-never-evicted-drop-low-priority-tail-if-source-is-protected",
        "turkcell_pasaj_price_provenance": "v23.63.03-preserved",
        "amazon_phone_search_card_offer": "v23.62.91-preserved",
        "n11_rendered_option_recovery": "v23.62.95-preserved",
        "idefix_brand_catalog_recovery": "v23.62.99-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged-outside-user-ingestion-source-and-roster-correctness",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236304")
def runtime_soak_stability_v236304():
    data = runtime_soak_stability_v236303()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236304
    return data

@app.get("/api/runtime-identity/v236303")
def runtime_identity_v236303():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236303,
        "architecture": "turkcell-pasaj-direct-sale-price-provenance-lock",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236303,
        "runtime_version_source": "single-source-v236303",
        "behavior_policy": "v23.63.02-preserved-turkcell-direct-sale-price-provenance-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_store": "v23.63.02-runtime-registry-preserved",
        "turkcell_pasaj_price_provenance": "v23.63.03-visible-direct-seller-shipping-context",
        "turkcell_pasaj_alternative_payment_rejection": "installment-contract-insurance-values-not-offer-price",
        "turkcell_pasaj_price_policy": "fail-closed-without-high-confidence-direct-sale-context",
        "turkcell_pasaj_discovery": "v23.63.01-preserved",
        "turkcell_pasaj_identity": "existing-canonical-detail-family-variant-network-storage-color-gates",
        "expected_cross_store_budget": 12,
        "amazon_phone_search_card_offer": "v23.62.91-preserved",
        "n11_rendered_option_recovery": "v23.62.95-preserved",
        "idefix_brand_catalog_recovery": "v23.62.99-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged-except-turkcell-price-provenance-lock",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236303")
def runtime_soak_stability_v236303():
    data = runtime_soak_stability_v236302()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236303
    return data


@app.get("/api/runtime-identity/v236302")
def runtime_identity_v236302():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236302,
        "architecture": "turkcell-pasaj-runtime-registry-convergence-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236302,
        "runtime_version_source": "single-source-v236302",
        "behavior_policy": "v23.63.01-preserved-runtime-scraper-registry-convergence-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_store": "v23.63.01-preserved",
        "turkcell_pasaj_runtime_registry": "v23.63.02-app-services-scraper-registry-converged",
        "turkcell_pasaj_discovery": "v23.63.01-phone-first-exact-canonical-detail-slug-preserved",
        "turkcell_pasaj_identity": "existing-canonical-detail-family-variant-network-storage-color-gates",
        "turkcell_pasaj_offer_pipeline": "generic-detail-jsonld-dom-plus-normal-price-integrity",
        "expected_cross_store_budget": 12,
        "amazon_phone_search_card_offer": "v23.62.91-preserved",
        "n11_rendered_option_recovery": "v23.62.95-preserved",
        "idefix_brand_catalog_recovery": "v23.62.99-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged-except-new-turkcell-store",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236302")
def runtime_soak_stability_v236302():
    data = runtime_soak_stability_v236301()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236302
    return data


@app.get("/api/runtime-identity/v236301")
def runtime_identity_v236301():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236301,
        "architecture": "turkcell-pasaj-phone-first-canonical-store-integration",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236301,
        "runtime_version_source": "single-source-v236301",
        "behavior_policy": "v23.63.00-preserved-turkcell-pasaj-new-store-only",
        "database_continuity": "v23.62.85-preserved",
        "turkcell_pasaj_store": "v23.63.01-enabled",
        "turkcell_pasaj_discovery": "phone-first-exact-canonical-detail-slug-plus-normal-search-fallback",
        "turkcell_pasaj_identity": "existing-canonical-detail-family-variant-network-storage-color-gates",
        "turkcell_pasaj_offer_pipeline": "generic-detail-jsonld-dom-plus-normal-price-integrity",
        "expected_cross_store_budget": 12,
        "amazon_phone_search_card_offer": "v23.62.91-preserved",
        "n11_rendered_option_recovery": "v23.62.95-preserved",
        "idefix_brand_catalog_recovery": "v23.62.99-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged-except-new-turkcell-store",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236301")
def runtime_soak_stability_v236301():
    data = runtime_soak_stability_v236300()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236301
    return data


@app.get("/api/runtime-identity/v236300")
def runtime_identity_v236300():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236300,
        "architecture": "idefix-brand-catalog-post-recovery-elapsed-scope-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236300,
        "runtime_version_source": "single-source-v236300",
        "behavior_policy": "v23.62.99-preserved-idefix-post-brand-recovery-control-flow-hotfix-only",
        "database_continuity": "v23.62.85-preserved",
        "amazon_phone_search_card_offer": "v23.62.91-preserved",
        "n11_rendered_option_recovery": "v23.62.95-preserved",
        "idefix_search_query_policy": "v23.62.96-preserved",
        "idefix_product_url_contract": "v23.62.97-preserved",
        "idefix_readiness_contract": "v23.62.98-preserved",
        "idefix_brand_catalog_recovery": "v23.62.99-preserved-44-candidate-brand-catalog-path",
        "idefix_post_recovery_elapsed_scope": "v23.63.00-direct-query-start-measurement-no-unbound-local",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236300")
def runtime_soak_stability_v236300():
    data = runtime_soak_stability_v236299()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236300
    return data

@app.get("/api/runtime-identity/v236299")
def runtime_identity_v236299():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236299,
        "architecture": "idefix-brand-catalog-fallback-after-client-only-search-shell",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236299,
        "runtime_version_source": "single-source-v236299",
        "behavior_policy": "v23.62.98-preserved-idefix-brand-catalog-discovery-fallback-and-p-slug-cleaning-only",
        "database_continuity": "v23.62.85-preserved",
        "amazon_phone_search_card_offer": "v23.62.91-preserved",
        "n11_rendered_option_recovery": "v23.62.95-preserved",
        "idefix_search_query_policy": "v23.62.96-preserved",
        "idefix_product_url_contract": "v23.62.97-root-slug-ending-p-id-plus-legacy-urun",
        "idefix_anchor_probe": "v23.62.97-current-p-slug-plus-adapter-selector-union-bounded-2500ms",
        "idefix_extraction": "v23.62.97-absolute-relative-p-id-html-patterns-plus-legacy-urun",
        "idefix_readiness_contract": "v23.62.98-dom-anchor-or-existing-adapter-html-product-url-contract",
        "idefix_html_contract_policy": "fail-closed-if-both-dom-and-html-have-zero-product-candidates",
        "idefix_brand_catalog_recovery": "v23.62.99-resolve-brand-via-markalar-then-normal-canonical-gates",
        "idefix_product_path_cleaner": "v23.62.99-root-p-id-plus-legacy-urun",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236299")
def runtime_soak_stability_v236299():
    data = runtime_soak_stability_v236296()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236299
    return data

@app.get("/api/runtime-identity/v236296")
def runtime_identity_v236296():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236296,
        "architecture": "idefix-canonical-strong-query-and-adapter-anchor-probe",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236296,
        "runtime_version_source": "single-source-v236296",
        "behavior_policy": "v23.62.95-preserved-idefix-strong-canonical-query-and-adapter-anchor-probe-only",
        "database_continuity": "v23.62.85-preserved",
        "amazon_phone_search_card_offer": "v23.62.91-preserved",
        "n11_exact_color_variant_resolver": "v23.62.92-linked-variant-fresh-title-family-variant-storage-color-exact",
        "n11_rendered_option_recovery": "v23.62.95-preserved",
        "idefix_search_query_policy": "v23.62.96-canonical-search-query-first-single-strong-query",
        "idefix_anchor_probe": "v23.62.96-adapter-selector-union-bounded-2500ms",
        "n11_detail_color_gate": "v23.35-preserved-fail-closed",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-plus-v23.62.68-budget-cap",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236296")
def runtime_soak_stability_v236296():
    data = runtime_soak_stability_v236291()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236296
    return data


@app.get("/api/runtime-identity/v236291")
def runtime_identity_v236291():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236291,
        "architecture": "amazon-xiaomi-redmi-brand-alias-after-exact-phone-identity",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236291,
        "runtime_version_source": "single-source-v236291",
        "behavior_policy": "v23.62.90-preserved-amazon-xiaomi-redmi-title-brand-alias-correctness-only",
        "database_continuity": "v23.62.85-preserved",
        "amazon_phone_search_card_offer": "v23.62.91-score280-exact-asin-family-variant-storage-color-plus-xiaomi-redmi-alias",
        "amazon_phone_brand_alias": "xiaomi-source-redmi-title-only-after-exact-family-variant-storage-color",
        "amazon_phone_detail_fallback": "v23.62.90-preserved",
        "amazon_phone_prefilter": "v23.62.88-preserved",
        "amazon_phone_preflight_identity": "v23.62.90-preserved",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-plus-v23.62.68-budget-cap",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236291")
def runtime_soak_stability_v236291():
    data = runtime_soak_stability_v236290()
    data = dict(data)
    data["runtime_version"] = _RUNTIME_VERSION_V236291
    return data


@app.get("/api/runtime-soak-stability/v236290")
def runtime_soak_stability_v236290():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236290,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }


@app.get("/api/runtime-identity/v236288")
def runtime_identity_v236288():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236288,
        "architecture": "amazon-phone-recall-safe-prefilter-and-plausible-price-priority",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236288,
        "runtime_version_source": "single-source-v236288",
        "behavior_policy": "v23.62.87-preserved-amazon-phone-recall-safe-search-card-prefilter-and-priority-only",
        "database_continuity": "v23.62.85-preserved",
        "amazon_phone_preflight_candidate_window": 8,
        "amazon_phone_prefilter": "v23.62.88-explicit-accessory-noun-only-no-generic-uyumlu-hard-reject",
        "amazon_phone_low_price_policy": "soft-signal-retained-for-title-preflight",
        "amazon_phone_plausible_price_priority": "v23.62.88-search-card-price-45pct-to-175pct-source-before-score",
        "amazon_phone_preflight_identity": "v23.62.87-family-plus-variant-plus-storage-preserved",
        "amazon_phone_preflight_expensive_path": "first-preflight-compatible-candidate-only",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-plus-v23.62.68-budget-cap",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236288")
def runtime_soak_stability_v236288():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236288,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }


@app.get("/api/runtime-identity/v236287")
def runtime_identity_v236287():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236287,
        "architecture": "amazon-preflight-window-family-variant-storage-gate",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236287,
        "runtime_version_source": "single-source-v236287",
        "behavior_policy": "v23.62.86-preserved-amazon-preflight-window-and-family-generation-correctness-only",
        "database_continuity": "v23.62.85-preserved",
        "amazon_phone_preflight_candidate_window": 8,
        "amazon_phone_preflight_identity": "v23.62.87-explicit-family-plus-variant-plus-storage-mismatch-reject",
        "amazon_phone_preflight_expensive_path": "first-preflight-compatible-candidate-only",
        "amazon_phone_search_card_identity_order": "v23.62.81-preserved",
        "amazon_phone_search_card_prefilter": "v23.62.78-preserved",
        "source_color_token_boundary": "v23.62.79-preserved",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-plus-v23.62.68-budget-cap",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236287")
def runtime_soak_stability_v236287():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236287,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }


@app.get("/api/runtime-identity/v236286")
def runtime_identity_v236286():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236286,
        "architecture": "master-runtime-force-and-amazon-preflight-correctness",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236286,
        "runtime_version_source": "single-source-v236286",
        "behavior_policy": "v23.62.85-master-preserved-runtime-force-version-and-amazon-preflight-correctness-only",
        "database_continuity": "v23.62.85-preserved",
        "amazon_phone_detail_title_preflight": "v23.62.86-pro-plus-distinct-top8-preflight-candidates",
        "amazon_phone_preflight_candidate_cap": 8,
        "amazon_phone_search_card_identity_order": "v23.62.81-preserved",
        "amazon_no_buyable_detail_identity_bridge": "v23.62.82-preserved-pro-plus-aware",
        "amazon_candidate_retry_policy": "bounded-preflight-mismatch-only-browser-first-compatible",
        "amazon_phone_search_card_prefilter": "v23.62.78-preserved",
        "source_color_token_boundary": "v23.62.79-preserved",
        "detail_color_reject_evidence": "v23.62.80-preserved",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-plus-v23.62.68-budget-cap",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236286")
def runtime_soak_stability_v236286():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236286,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }


@app.get("/api/runtime-identity/v236285")
def runtime_identity_v236285():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236285,
        "architecture": "master-startup-import-and-wal-safe-continuity-hardening",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236285,
        "runtime_version_source": "single-source-v236285",
        "behavior_policy": "v23.62.84-master-preserved-startup-and-continuity-correctness-only",
        "database_continuity": "v23.62.85-offer-rich-95pct-product-coverage-wal-safe-selector",
        "database_integrity_import_mode": "module-launch-plus-direct-run-root-bootstrap",
        "startup_pythonpath_policy": "project-root-explicit",
        "package_path_policy": "short-root-FirsatAI85-single-launcher",
        "amazon_phone_detail_title_preflight": "v23.62.83-preserved",
        "amazon_phone_search_card_identity_order": "v23.62.81-preserved",
        "amazon_no_buyable_detail_identity_bridge": "v23.62.82-preserved",
        "amazon_candidate_retry_policy": "v23.62.77-preserved-bounded",
        "amazon_phone_search_card_prefilter": "v23.62.78-preserved",
        "source_color_token_boundary": "v23.62.79-preserved",
        "detail_color_reject_evidence": "v23.62.80-preserved",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-plus-v23.62.68-budget-cap",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236285")
def runtime_soak_stability_v236285():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236285,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }


@app.get("/api/runtime-identity/v236284")
def runtime_identity_v236284():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236284,
        "architecture": "master-rebuild-wal-safe-continuity-path-safe-package",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236284,
        "runtime_version_source": "single-source-v236284",
        "behavior_policy": "v23.62.83-scraping-preserved-master-stability-and-data-continuity-hardening",
        "database_continuity": "v23.62.84-user-profile-discovery-wal-safe-sqlite-backup",
        "database_continuity_search_roots": "project-parent-plus-user-desktop-downloads-documents",
        "database_integrity_policy": "full-integrity-before-import-and-after-snapshot",
        "startup_port_guard": "127.0.0.1:8000-must-be-free",
        "package_path_policy": "short-root-FirsatAI84-single-launcher",
        "amazon_phone_detail_title_preflight": "v23.62.83-preserved",
        "amazon_phone_search_card_identity_order": "v23.62.81-preserved",
        "amazon_no_buyable_detail_identity_bridge": "v23.62.82-preserved",
        "amazon_candidate_retry_policy": "v23.62.77-preserved-bounded",
        "amazon_phone_search_card_prefilter": "v23.62.78-preserved",
        "source_color_token_boundary": "v23.62.79-preserved",
        "detail_color_reject_evidence": "v23.62.80-preserved",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-plus-v23.62.68-budget-cap",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }

@app.get("/api/runtime-soak-stability/v236284")
def runtime_soak_stability_v236284():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236284,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }

@app.get("/api/runtime-identity/v236283")
def runtime_identity_v236283():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236283,
        "architecture": "amazon-phone-detail-title-preflight-variant-gate",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236283,
        "runtime_version_source": "single-source-v236283",
        "behavior_policy": "v23.62.82-preserved-amazon-phone-preflight-variant-gate-only",
        "baseline_source": "v23.62.81-amazon-phone-identity-aware-detail-order",
        "force_store_budget": 11,
        "minimum_offer_count": 6,
        "minimum_store_success_count": 6,
        "n11_expected_status": "SUCCESS",
        "amazon_phone_search_card_identity_order": "v23.62.81-preserved",
        "amazon_no_buyable_detail_identity_bridge": "v23.62.82-preserved-plus-pro-plus-aware-v23.62.83",
        "amazon_phone_detail_title_preflight": "v23.62.83-top3-http-title-reject-only-before-browser",
        "amazon_phone_preflight_retry_cap": "max3-retained-only-explicit-variant-mismatch-unlocks-next",
        "amazon_candidate_retry_policy": "v23.62.77-preserved-one-backup-bounded",
        "amazon_no_buyable_normal_policy": "backup-remains-blocked-without-authoritative-detail-identity-mismatch",
        "amazon_phone_search_card_prefilter": "v23.62.78-preserved",
        "source_color_token_boundary": "v23.62.79-preserved",
        "detail_color_reject_evidence": "v23.62.80-preserved",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236283")
def runtime_soak_stability_v236283():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236283,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }

@app.get("/api/runtime-identity/v236281")
def runtime_identity_v236281():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236281,
        "architecture": "amazon-phone-search-card-identity-aware-detail-order",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236281,
        "runtime_version_source": "single-source-v236281",
        "behavior_policy": "v23.62.80-preserved-amazon-phone-card-identity-order-only",
        "baseline_source": "v23.62.80-color-reject-evidence-telemetry",
        "force_store_budget": 11,
        "minimum_offer_count": 6,
        "minimum_store_success_count": 6,
        "n11_expected_status": "SUCCESS",
        "amazon_phone_search_card_identity_order": "v23.62.81-score316-brand-family-variant-storage-before-color",
        "amazon_phone_search_card_prefilter": "v23.62.78-preserved",
        "amazon_candidate_retry_policy": "v23.62.77-preserved-one-backup-after-canonical-identity-reject",
        "source_color_token_boundary": "v23.62.79-preserved",
        "detail_color_reject_evidence": "v23.62.80-preserved",
        "hepsiburada_final_price_normalization": "v23.62.76-preserved",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236281")
def runtime_soak_stability_v236281():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236281,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }


@app.get("/api/runtime-identity/v236280")
def runtime_identity_v236280():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236280,
        "architecture": "detail-color-reject-evidence-telemetry",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236280,
        "runtime_version_source": "single-source-v236280",
        "behavior_policy": "v23.62.79-preserved-observability-only-no-acceptance-change",
        "baseline_source": "v23.62.79-source-color-boundary-hotfix",
        "force_store_budget": 11,
        "minimum_offer_count": 6,
        "minimum_store_success_count": 6,
        "n11_expected_status": "SUCCESS",
        "detail_color_reject_evidence": "v23.62.80-source-and-candidate-name-model-category-url-log",
        "source_color_token_boundary": "v23.62.79-preserved",
        "amazon_phone_search_card_prefilter": "v23.62.78-preserved",
        "amazon_candidate_retry_policy": "v23.62.77-preserved-one-backup-after-canonical-identity-reject",
        "hepsiburada_final_price_normalization": "v23.62.76-preserved",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236280")
def runtime_soak_stability_v236280():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236280,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }


@app.get("/api/runtime-identity/v236279")
def runtime_identity_v236279():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236279,
        "architecture": "token-boundary-safe-source-color-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236279,
        "runtime_version_source": "single-source-v236279",
        "behavior_policy": "v23.62.78-preserved-source-color-token-boundary-hotfix-only",
        "baseline_source": "v23.62.78-amazon-phone-prefilter-preserved",
        "force_store_budget": 11,
        "minimum_offer_count": 6,
        "minimum_store_success_count": 6,
        "n11_expected_status": "SUCCESS",
        "source_color_token_boundary": "v23.62.79-red-must-not-match-redmi-blue-must-not-match-bluetooth",
        "source_color_regression_case": "Redmi-Note-15-Pro-Titanyum-Gri=>gri-not-kirmizi",
        "amazon_phone_search_card_prefilter": "v23.62.78-preserved",
        "amazon_candidate_retry_policy": "v23.62.77-preserved-one-backup-after-canonical-identity-reject",
        "hepsiburada_final_price_normalization": "v23.62.76-preserved",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-plus-v23.62.68-budget-cap",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236279")
def runtime_soak_stability_v236279():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236279,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }


@app.get("/api/runtime-identity/v236278")
def runtime_identity_v236277():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236278,
        "architecture": "amazon-phone-search-card-plausibility-prefilter",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236278,
        "runtime_version_source": "single-source-v236278",
        "behavior_policy": "v23.62.77-preserved-amazon-phone-search-card-plausibility-prefilter-only",
        "baseline_source": "v23.62.76-hepsiburada-recovery-pass",
        "force_store_budget": 11,
        "force_store_budget_policy": "n11-observability-replaces-one-existing-slot-never-adds-12th-store",
        "minimum_offer_count": 6,
        "minimum_store_success_count": 6,
        "extra_valid_offer_policy": "allowed-not-regression",
        "n11_expected_status": "SUCCESS",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-plus-v23.62.68-budget-cap",
        "offer_unique_key_convergence": "v23.62.65-preserved",
        "offer_url_unique_convergence": "v23.62.66-preserved",
        "n11_cold_start_trust_bootstrap": "v23.62.66-preserved",
        "n11_recent_verified_detail_bridge": "v23.62.62-preserved",
        "n11_detail_http_connection_pool": "v23.62.60-preserved",
        "amazon_search_query_policy": "v23.62.74-preserved",
        "amazon_search_navigation_budget_ms": 8000,
        "amazon_detail_total_budget_policy": "v23.62.72-18s-wall-clock-shared-detail-recovery-browser-budget",
        "amazon_candidate_retry_policy": "v23.62.77-one-backup-only-after-first-canonical-identity-reject",
        "amazon_candidate_retry_max_detail_candidates": 2,
        "amazon_phone_search_card_prefilter": "v23.62.78-accessory-token-or-below-35pct-source-price-hard-reject",
        "amazon_candidate_retry_unlock_events": ["CANONICAL_IDENTITY_REJECT"],
        "amazon_candidate_retry_block_events": ["NO_BUYABLE_OFFER", "SECURITY_CHALLENGE", "TIMEOUT", "SCRAPE_ERROR", "COLOR_REJECT"],
        "hepsiburada_final_price_normalization": "v23.62.76-preserved",
        "hepsiburada_verified_card_recovery": "v23.62.76-preserved",
        "phone_search_card_accessory_prefilter": "v23.62.69-preserved",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236278")
def runtime_soak_stability_v236277():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236278,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }


@app.get("/api/runtime-identity/v236276")
def runtime_identity_v236276():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236276,
        "architecture": "hepsiburada-turkish-thousands-final-price-and-exact-card-recovery",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236276,
        "runtime_version_source": "single-source-v236276",
        "behavior_policy": "v23.62.75-preserved-hepsiburada-price-normalization-and-exact-card-recovery-only",
        "baseline_source": "v23.62.66-15-of-15-soak-pass",
        "force_store_budget": 11,
        "force_store_budget_policy": "n11-observability-replaces-one-existing-slot-never-adds-12th-store",
        "minimum_offer_count": 6,
        "minimum_store_success_count": 6,
        "extra_valid_offer_policy": "allowed-not-regression",
        "n11_expected_status": "SUCCESS",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-plus-v23.62.68-budget-cap",
        "offer_unique_key_convergence": "v23.62.65-preserved",
        "offer_url_unique_convergence": "v23.62.66-preserved",
        "n11_cold_start_trust_bootstrap": "v23.62.66-preserved",
        "n11_recent_verified_detail_bridge": "v23.62.62-preserved",
        "n11_detail_http_connection_pool": "v23.62.60-preserved",
        "baseline_n11_success_rate_percent": 100.0,
        "baseline_n11_latency_avg_seconds": 6.745,
        "latency_policy": "observation-only-single-outlier-warn-no-scraping-change",
        "amazon_browser_fallback_navigation_budget_ms": 6000,
        "amazon_browser_fallback_initial_wait_seconds": 1.0,
        "amazon_browser_fallback_scroll": "disabled",
        "amazon_search_query_order": "v23.62.70-strong-search-query-first",
        "amazon_no_buyable_circuit_break": "v23.62.70-stop-after-first-authoritative-no-buyable",
        "amazon_detail_http_timeout_seconds": 6.0,
        "amazon_detail_total_budget_policy": "v23.62.72-18s-wall-clock-shared-detail-recovery-browser-budget",
        "amazon_detail_candidate_policy": "v23.62.75-binding-force-path-first-detail-candidate-only",
        "amazon_search_query_policy": "v23.62.74-strong-canonical-query-only-when-brand-model-strong",
        "amazon_search_navigation_budget_ms": 8000,
        "amazon_search_selector_ready": "dp-anchor-3s-probe-150ms-settle-skip-networkidle",
        "hepsiburada_final_price_normalization": "v23.62.76-single-dot-three-digit-is-thousands-separator",
        "hepsiburada_verified_card_recovery": "v23.62.76-score316-trusted-final-price-exact-phone-wearable-only",
        "hepsiburada_challenge_policy": "fail-closed-detail-challenge-search-card-evidence-independent",
        "phone_search_card_accessory_prefilter": "v23.62.69-jelatin-nano-cam-seramik-film-temperli-cam-hard-reject",
        "observed_latency_outlier_owner": "amazon-bounded-v23.62.75",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236276")
def runtime_soak_stability_v236276():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236276,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }


@app.get("/api/runtime-identity/v236275")
def runtime_identity_v236275():
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236275,
        "architecture": "amazon-binding-first-candidate-real-path-hotfix",
        "serving_mode": "catalog-first-primary-tier-ready-deep-refresh",
        "force_refresh_response_runtime_version": _RUNTIME_VERSION_V236275,
        "runtime_version_source": "single-source-v236275",
        "behavior_policy": "v23.62.74-preserved-binding-force-path-first-amazon-candidate-only",
        "baseline_source": "v23.62.66-15-of-15-soak-pass",
        "force_store_budget": 11,
        "force_store_budget_policy": "n11-observability-replaces-one-existing-slot-never-adds-12th-store",
        "minimum_offer_count": 6,
        "minimum_store_success_count": 6,
        "extra_valid_offer_policy": "allowed-not-regression",
        "n11_expected_status": "SUCCESS",
        "n11_force_inclusion_invariant": "v23.62.65-preserved-plus-v23.62.68-budget-cap",
        "offer_unique_key_convergence": "v23.62.65-preserved",
        "offer_url_unique_convergence": "v23.62.66-preserved",
        "n11_cold_start_trust_bootstrap": "v23.62.66-preserved",
        "n11_recent_verified_detail_bridge": "v23.62.62-preserved",
        "n11_detail_http_connection_pool": "v23.62.60-preserved",
        "baseline_n11_success_rate_percent": 100.0,
        "baseline_n11_latency_avg_seconds": 6.745,
        "latency_policy": "observation-only-single-outlier-warn-no-scraping-change",
        "amazon_browser_fallback_navigation_budget_ms": 6000,
        "amazon_browser_fallback_initial_wait_seconds": 1.0,
        "amazon_browser_fallback_scroll": "disabled",
        "amazon_search_query_order": "v23.62.70-strong-search-query-first",
        "amazon_no_buyable_circuit_break": "v23.62.70-stop-after-first-authoritative-no-buyable",
        "amazon_detail_http_timeout_seconds": 6.0,
        "amazon_detail_total_budget_policy": "v23.62.72-18s-wall-clock-shared-detail-recovery-browser-budget",
        "amazon_detail_candidate_policy": "v23.62.75-binding-force-path-first-detail-candidate-only",
        "amazon_search_query_policy": "v23.62.74-strong-canonical-query-only-when-brand-model-strong",
        "amazon_search_navigation_budget_ms": 8000,
        "amazon_search_selector_ready": "dp-anchor-3s-probe-150ms-settle-skip-networkidle",
        "phone_search_card_accessory_prefilter": "v23.62.69-jelatin-nano-cam-seramik-film-temperli-cam-hard-reject",
        "observed_latency_outlier_owner": "amazon-not-n11",
        "security_challenge_bypass": "disabled",
        "production_ingestion_behavior": "unchanged",
        "price_integrity_quarantine": "preserved",
        "canonical_test_global_product_id": 160,
    }


@app.get("/api/runtime-soak-stability/v236275")
def runtime_soak_stability_v236275():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236275,
        "contract_semantics": "minimum-floor-extra-valid-offers-allowed",
        "force_store_budget": 11,
        **snapshot,
    }


@app.get("/api/runtime-soak-stability/v236267")
def runtime_soak_stability_v236267():
    snapshot = _soak_snapshot_v236248()
    return {
        "ok": True,
        "runtime_version": _RUNTIME_VERSION_V236267,
        "baseline_source": "v23.62.66-15-of-15-soak-pass",
        "baseline_locked": True,
        "telemetry_scope": "localhost-force-refresh-process-lifetime-rolling-window-contract",
        "persistence": "in-memory-reset-on-process-restart",
        **snapshot,
    }
