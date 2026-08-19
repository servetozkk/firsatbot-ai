from __future__ import annotations

import hashlib
import json
import logging
import threading
from collections import Counter
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "data" / "logs"
APP_LOG_PATH = LOG_DIR / "firsatai.log"
EVENT_LOG_PATH = LOG_DIR / "operations.jsonl"
_LOCK = threading.RLock()
_CONFIGURED = False


def configure_operational_logging() -> None:
    global _CONFIGURED
    with _LOCK:
        if _CONFIGURED:
            return
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        absolute_path = str(APP_LOG_PATH.resolve())
        exists = any(
            isinstance(handler, RotatingFileHandler)
            and str(getattr(handler, "baseFilename", "")) == absolute_path
            for handler in root_logger.handlers
        )
        if not exists:
            handler = RotatingFileHandler(
                APP_LOG_PATH,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
                )
            )
            root_logger.addHandler(handler)
        _CONFIGURED = True


def _signature(source: str, event_type: str, message: str) -> str:
    raw = f"{source}|{event_type}|{message}".casefold().strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def record_operation_event(
    *,
    level: str,
    source: str,
    event_type: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    configure_operational_logging()
    row = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
        "level": str(level or "INFO").upper(),
        "source": str(source or "system"),
        "event_type": str(event_type or "event"),
        "message": str(message or ""),
        "signature": _signature(source, event_type, message),
        "details": details or {},
    }
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with EVENT_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    logger = logging.getLogger(f"firsatai.{row['source']}")
    method = getattr(logger, row["level"].casefold(), logger.info)
    method("%s | %s | %s", row["event_type"], row["message"], row["details"])
    return row


def read_operation_events(
    *,
    limit: int = 300,
    level: str | None = None,
    source: str | None = None,
    hours: int | None = None,
) -> list[dict[str, Any]]:
    if not EVENT_LOG_PATH.exists():
        return []
    minimum = (
        datetime.utcnow() - timedelta(hours=max(1, int(hours)))
        if hours is not None
        else None
    )
    try:
        lines = EVENT_LOG_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in reversed(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if level and str(row.get("level", "")).upper() != level.upper():
            continue
        if source and str(row.get("source", "")) != source:
            continue
        if minimum is not None:
            try:
                timestamp = datetime.fromisoformat(str(row.get("timestamp", "")))
            except ValueError:
                continue
            if timestamp < minimum:
                continue
        rows.append(row)
        if len(rows) >= max(1, min(int(limit), 2000)):
            break
    return rows


def operational_summary() -> dict[str, Any]:
    rows = read_operation_events(limit=2000, hours=24)
    levels = Counter(str(row.get("level", "INFO")) for row in rows)
    signatures = Counter(
        str(row.get("signature", ""))
        for row in rows
        if str(row.get("level", "")).upper() in {"ERROR", "CRITICAL"}
    )
    repeated = []
    for signature, count in signatures.most_common(10):
        if count < 2:
            continue
        sample = next(
            (row.get("message") for row in rows if row.get("signature") == signature),
            "",
        )
        repeated.append({"signature": signature, "count": count, "sample": sample})
    return {
        "events_24h": len(rows),
        "errors_24h": levels.get("ERROR", 0) + levels.get("CRITICAL", 0),
        "warnings_24h": levels.get("WARNING", 0),
        "info_24h": levels.get("INFO", 0),
        "repeated_errors": repeated,
        "app_log_size_mb": round(APP_LOG_PATH.stat().st_size / 1048576, 3) if APP_LOG_PATH.exists() else 0,
        "event_log_size_mb": round(EVENT_LOG_PATH.stat().st_size / 1048576, 3) if EVENT_LOG_PATH.exists() else 0,
    }


def clear_operation_events() -> int:
    rows = len(read_operation_events(limit=2000))
    with _LOCK:
        EVENT_LOG_PATH.unlink(missing_ok=True)
    return rows
