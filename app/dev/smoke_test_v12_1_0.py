from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    main_text = (ROOT / "main.py").read_text(encoding="utf-8-sig")
    health_path = ROOT / "app" / "web" / "health_v12_routes.py"
    env_path = ROOT / "app" / "ops" / "production_env_v12.py"
    backup_path = ROOT / "app" / "ops" / "sqlite_backup_v12.py"
    for path in (health_path, env_path, backup_path):
        ast.parse(path.read_text(encoding="utf-8-sig"))
    ok(version == "12.1.0", "VERSION 12.1.0")
    ok("health_v12_router" in main_text, "health v12 router main.py içine bağlı")
    health_text = health_path.read_text(encoding="utf-8-sig")
    ok('@router.get("/live")' in health_text, "/health/live endpoint mevcut")
    ok('@router.get("/ready")' in health_text, "/health/ready endpoint mevcut")
    ok("PRAGMA integrity_check" in health_text, "readiness SQLite bütünlüğünü kontrol ediyor")
    ok("secrets.token_urlsafe" in env_path.read_text(encoding="utf-8-sig"), "güvenli anahtar üreticisi mevcut")
    ok("src.backup(dst)" in backup_path.read_text(encoding="utf-8-sig"), "tutarlı SQLite backup API kullanılıyor")
    print("\nFırsatAI v12.1.0 Production Operations smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
