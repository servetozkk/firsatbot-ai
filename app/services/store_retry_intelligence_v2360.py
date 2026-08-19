from __future__ import annotations

from typing import Any


def store_retry_intelligence_v2360(*, success: bool, failure_class: str | None) -> dict[str, Any]:
    """Return conservative retry/reliability guidance for one store attempt.

    V23.60 is advisory only: it never triggers an immediate retry itself.
    Identity rejects are treated as a successful safety decision, not a broken store.
    """
    fc = str(failure_class or "").upper().strip()

    if success:
        return {
            "reliability_score": 100,
            "retryable": False,
            "retry_mode": "NONE",
            "retry_after_seconds": None,
            "recommended_action": "KEEP_SUCCESS_PATH",
            "reason": "offer-saved",
        }

    policies: dict[str, dict[str, Any]] = {
        "SECURITY_CHALLENGE": {
            "reliability_score": 45,
            "retryable": True,
            "retry_mode": "DEFERRED",
            "retry_after_seconds": 1800,
            "recommended_action": "RETRY_LATER_PRESERVE_SECURITY_POLICY",
            "reason": "store-reachable-but-security-challenge",
        },
        "TIMEOUT": {
            "reliability_score": 55,
            "retryable": True,
            "retry_mode": "TRANSIENT",
            "retry_after_seconds": 300,
            "recommended_action": "RETRY_LATER_WITH_SAME_IDENTITY_GATES",
            "reason": "transient-timeout",
        },
        "SCRAPE_ERROR": {
            "reliability_score": 50,
            "retryable": True,
            "retry_mode": "TRANSIENT",
            "retry_after_seconds": 600,
            "recommended_action": "RETRY_LATER_AND_REVIEW_SCRAPER_IF_REPEATED",
            "reason": "scraper-transient-or-layout-error",
        },
        "PRICE_READ_ERROR": {
            "reliability_score": 60,
            "retryable": True,
            "retry_mode": "DEFERRED",
            "retry_after_seconds": 900,
            "recommended_action": "RETRY_LATER_PRICE_PATH_ONLY",
            "reason": "candidate-found-price-not-trusted",
        },
        "NO_BUYABLE_OFFER": {
            "reliability_score": 72,
            "retryable": True,
            "retry_mode": "DEFERRED",
            "retry_after_seconds": 21600,
            "recommended_action": "RECHECK_ON_FUTURE_REFRESH",
            "reason": "product-context-found-no-buyable-offer",
        },
        "NO_CANDIDATE": {
            "reliability_score": 65,
            "retryable": True,
            "retry_mode": "DEFERRED",
            "retry_after_seconds": 21600,
            "recommended_action": "RECHECK_ON_FUTURE_REFRESH_NO_IMMEDIATE_RETRY",
            "reason": "search-completed-no-safe-candidate",
        },
        "IDENTITY_REJECT": {
            "reliability_score": 88,
            "retryable": False,
            "retry_mode": "CONTEXT_CHANGE_ONLY",
            "retry_after_seconds": None,
            "recommended_action": "DO_NOT_RETRY_UNTIL_QUERY_OR_VARIANT_CONTEXT_CHANGES",
            "reason": "safety-gate-worked-candidate-was-not-same-product",
        },
        "OTHER": {
            "reliability_score": 40,
            "retryable": True,
            "retry_mode": "DEFERRED",
            "retry_after_seconds": 1800,
            "recommended_action": "RETRY_LATER_AND_CLASSIFY_IF_REPEATED",
            "reason": "unclassified-failure",
        },
    }
    return dict(policies.get(fc, policies["OTHER"]))


def summarize_store_retry_intelligence_v2360(rows: list[dict[str, Any]]) -> dict[str, Any]:
    retryable = [r for r in rows if bool(r.get("retryable"))]
    transient = [r for r in rows if r.get("retry_mode") == "TRANSIENT"]
    deferred = [r for r in rows if r.get("retry_mode") == "DEFERRED"]
    context_only = [r for r in rows if r.get("retry_mode") == "CONTEXT_CHANGE_ONLY"]
    scored = [int(r.get("reliability_score") or 0) for r in rows]
    return {
        "retryable_store_codes": [str(r.get("store_code") or "") for r in retryable],
        "transient_retry_store_codes": [str(r.get("store_code") or "") for r in transient],
        "deferred_retry_store_codes": [str(r.get("store_code") or "") for r in deferred],
        "context_change_only_store_codes": [str(r.get("store_code") or "") for r in context_only],
        "retryable_count": len(retryable),
        "average_reliability_score": round(sum(scored) / len(scored), 2) if scored else None,
        "lowest_reliability_store": min(rows, key=lambda r: int(r.get("reliability_score") or 0), default=None),
    }
