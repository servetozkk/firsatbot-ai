from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on", "evet"}


def _env_list(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(item.strip().casefold() for item in os.getenv(name, default).split(",") if item.strip())


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


BASE_DIR = Path(__file__).resolve().parents[2]


def _default_app_version() -> str:
    version_file = BASE_DIR / "VERSION"
    try:
        value = version_file.read_text(encoding="utf-8").strip()
        return value or "unknown"
    except OSError:
        return "unknown"


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Fırsat AI")
    app_version: str = os.getenv("APP_VERSION", _default_app_version())
    app_env: str = os.getenv("APP_ENV", "development").strip().casefold()
    host: str = os.getenv("APP_HOST", "127.0.0.1")
    port: int = _env_int("APP_PORT", 8000, 1)
    enable_scheduler: bool = _env_bool("ENABLE_SCHEDULER", True)
    catalog_feed_enabled: bool = _env_bool("CATALOG_FEED_ENABLED", True)
    catalog_feed_interval_minutes: int = _env_int("CATALOG_FEED_INTERVAL_MINUTES", 30, 1)
    catalog_feed_initial_delay_seconds: int = _env_int("CATALOG_FEED_INITIAL_DELAY_SECONDS", 90, 0)
    catalog_feed_batch_size: int = _env_int("CATALOG_FEED_BATCH_SIZE", 3, 1)
    catalog_feed_stale_hours: int = _env_int("CATALOG_FEED_STALE_HOURS", 6, 1)
    slow_request_ms: int = _env_int("SLOW_REQUEST_MS", 1200, 100)
    static_cache_seconds: int = _env_int("STATIC_CACHE_SECONDS", 604800, 0)
    secret_key: str = os.getenv("SECRET_KEY", "dev-only-change-me")
    admin_access_token: str = os.getenv("ADMIN_ACCESS_TOKEN", "").strip()
    admin_cookie_name: str = os.getenv("ADMIN_COOKIE_NAME", "firsat_admin")
    admin_session_minutes: int = _env_int("ADMIN_SESSION_MINUTES", 480, 5)
    secure_cookies: bool = _env_bool("SECURE_COOKIES", False)
    csrf_enabled: bool = _env_bool("CSRF_ENABLED", True)
    rate_limit_enabled: bool = _env_bool("RATE_LIMIT_ENABLED", True)
    rate_limit_per_minute: int = _env_int("RATE_LIMIT_PER_MINUTE", 180, 10)
    admin_rate_limit_per_minute: int = _env_int("ADMIN_RATE_LIMIT_PER_MINUTE", 90, 10)
    trusted_hosts: tuple[str, ...] = _env_list("TRUSTED_HOSTS", "127.0.0.1:8000,localhost:8000")
    database_path: Path = Path(
        os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "products.db"))
    ).resolve()

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def secret_key_is_strong(self) -> bool:
        return len(self.secret_key) >= 32 and self.secret_key != "dev-only-change-me"

    @property
    def admin_protection_enabled(self) -> bool:
        return bool(self.admin_access_token) or self.is_production


settings = Settings()
