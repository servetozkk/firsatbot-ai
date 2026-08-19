from __future__ import annotations

from fastapi import APIRouter

from app.services.performance_optimization_service import load_report

router = APIRouter(tags=["performance-v13"])


@router.get("/api/performance/v13")
def performance_v13_status():
    """v13.7.0 performans raporunu salt okunur olarak döndürür."""
    payload = load_report()
    payload["read_only"] = True
    return payload
