from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.database.database import SessionLocal
from app.services.global_catalog_search_service import build_global_search_candidates
from app.services.smart_search_service import build_autocomplete, enrich_and_rank_candidates, parse_smart_query

router = APIRouter(prefix="/api/search", tags=["smart-search-v13.3"])

@router.get("/intelligence")
def search_intelligence(q: str = ""):
    parsed = parse_smart_query(q)
    return JSONResponse({"engine_version": "13.3.0", "read_only": True, "query": q, "parsed": parsed})

@router.get("/autocomplete-v13")
def autocomplete_v13(q: str = ""):
    cleaned = " ".join(str(q or "").split())
    if len(cleaned) < 2:
        return JSONResponse({"engine_version": "13.3.0", "query": cleaned, "items": []})
    db = SessionLocal()
    try:
        parsed = parse_smart_query(cleaned)
        products = build_global_search_candidates(db=db, query=parsed.get("search_text") or cleaned)
        ranked = enrich_and_rank_candidates(products, parsed)
        return JSONResponse({"engine_version": "13.3.0", "query": cleaned, "parsed": parsed, "items": build_autocomplete(cleaned, ranked or products)})
    finally:
        db.close()
