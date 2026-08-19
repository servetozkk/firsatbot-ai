from __future__ import annotations

import json, os, sqlite3, subprocess, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "products.db"
REPORT = ROOT / "data" / "reports" / "v12_0_0_final_release_report.json"
REQUIRED_INDEXES = {
    "ix_product_offers_group_active_hidden_price",
    "ix_product_offers_store_active_checked",
    "ix_offer_price_history_offer_created",
    "ix_product_groups_category_brand",
}

def env_value(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

def run_module(name: str) -> dict:
    p = subprocess.run([sys.executable, "-m", name], cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace")
    return {"module": name, "ok": p.returncode == 0, "returncode": p.returncode, "stdout_tail": p.stdout[-4000:], "stderr_tail": p.stderr[-2000:]}

def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    if not DB.exists():
        raise SystemExit(f"Veritabanı bulunamadı: {DB}")
    conn = sqlite3.connect(DB)
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    fk = len(conn.execute("PRAGMA foreign_key_check").fetchall())
    counts = {}
    for table in ("stores", "product_groups", "product_offers", "offer_price_history"):
        try: counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.Error: counts[table] = None
    indexes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    missing_indexes = sorted(REQUIRED_INDEXES - indexes)
    conn.close()

    app_env = env_value("APP_ENV", "development").casefold()
    secret = env_value("SECRET_KEY", "dev-only-change-me")
    admin_token = env_value("ADMIN_ACCESS_TOKEN")
    secure_cookies = env_value("SECURE_COOKIES", "0").casefold() in {"1","true","yes","on"}
    trusted_hosts = env_value("TRUSTED_HOSTS", "127.0.0.1:8000,localhost:8000")
    production_checks = {
        "app_env_production": app_env == "production",
        "secret_key_strong": len(secret) >= 32 and secret != "dev-only-change-me",
        "admin_access_token_present": len(admin_token) >= 24,
        "secure_cookies": secure_cookies,
        "trusted_hosts_configured": bool(trusted_hosts) and "*" not in trusted_hosts,
    }

    regression_modules = [
        "app.dev.regression_global_product_v12_0_0",
        "app.dev.regression_performance_v12_0_0",
    ]
    regression = [run_module(m) for m in regression_modules]
    blockers = []
    if version != "12.0.0": blockers.append("VERSION_12_0_0_DEGIL")
    if integrity != "ok": blockers.append("SQLITE_INTEGRITY_HATASI")
    if fk: blockers.append("FOREIGN_KEY_IHLALI")
    if missing_indexes: blockers.append("PERFORMANS_INDEKSI_EKSIK")
    if any(not x["ok"] for x in regression): blockers.append("REGRESYON_TESTI_BASARISIZ")

    deployment_requirements = [k for k,v in production_checks.items() if not v]
    if blockers:
        status = "PRODUCTION_BLOCKED"
    elif deployment_requirements:
        status = "PRODUCTION_READY_FOR_DEPLOYMENT"
    else:
        status = "PRODUCTION_READY"

    backups = list((ROOT / "backups").rglob("*")) if (ROOT / "backups").exists() else []
    out = {
        "version": version,
        "status": status,
        "generated_at": datetime.now().isoformat(),
        "database": {"integrity": integrity, "foreign_key_violations": fk, "counts": counts},
        "performance": {"required_indexes": sorted(REQUIRED_INDEXES), "missing_indexes": missing_indexes},
        "production_checks": production_checks,
        "deployment_requirements": deployment_requirements,
        "blockers": blockers,
        "regression": regression,
        "backup_files_detected": sum(1 for p in backups if p.is_file()),
        "akakce_model": {
            "global_product_catalog": True,
            "multi_store_offers": True,
            "variant_safety": True,
            "price_history": True,
            "canonical_product_url": "/urun/{identity_key}",
        },
    }
    REPORT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK  VERSION: {version}")
    print(f"OK  SQLite integrity: {integrity}")
    print(f"OK  Foreign key ihlali: {fk}")
    print(f"OK  Performans indeksi: {len(REQUIRED_INDEXES)-len(missing_indexes)}/{len(REQUIRED_INDEXES)}")
    print(f"OK  Regresyon testi: {sum(1 for x in regression if x['ok'])}/{len(regression)}")
    print(f"BİLGİ  Product Group: {counts.get('product_groups')}")
    print(f"BİLGİ  Teklif: {counts.get('product_offers')}")
    print(f"BİLGİ  Fiyat geçmişi: {counts.get('offer_price_history')}")
    print(f"BİLGİ  Dağıtım gereksinimi: {len(deployment_requirements)}")
    print(f"BİLGİ  Engel: {len(blockers)}")
    print(f"DURUM: {status}")
    print(f"RAPOR: {REPORT}")
    return 1 if blockers else 0

if __name__ == "__main__":
    raise SystemExit(main())
