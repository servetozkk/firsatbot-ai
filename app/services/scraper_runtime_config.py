from __future__ import annotations

import os


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "evet"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def _env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


SCRAPER_HEADLESS = _env_bool("SCRAPER_HEADLESS", True)
SCRAPER_WORKERS = _env_int("SCRAPER_WORKERS", 3, 1, 8)
SCRAPER_REQUEST_DELAY = _env_float("SCRAPER_REQUEST_DELAY", 0.6, 0.0, 10.0)
SCRAPER_RETRY_COUNT = _env_int("SCRAPER_RETRY_COUNT", 1, 0, 3)
