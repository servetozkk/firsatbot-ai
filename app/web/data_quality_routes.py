from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.services.data_quality_service import build_data_quality_report, write_data_quality_report
from app.services.product_quality_fix_service import apply_safe_fixes

router = APIRouter(prefix="/admin/data-quality", tags=["Data Quality"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("", response_class=HTMLResponse)
def data_quality_page(
    request: Request,
    issue: str = Query(default="all"),
    search: str = Query(default=""),
    level: str = Query(default="all"),
    sort: str = Query(default="score_asc"),
    fixed: int = Query(default=0),
    fields: int = Query(default=0),
):
    db = SessionLocal()
    try:
        report = build_data_quality_report(db, limit=1000)
        products = list(report["products"])
        if issue and issue != "all":
            if issue == "duplicates":
                products = [item for item in products if item.get("possible_duplicate")]
            else:
                products = [item for item in products if issue in item.get("issue_codes", [])]
        if level == "critical":
            products = [item for item in products if item.get("score", 0) < 45]
        elif level == "attention":
            products = [item for item in products if 45 <= item.get("score", 0) < 65]
        elif level == "good":
            products = [item for item in products if item.get("score", 0) >= 85]
        query = search.strip().casefold()
        if query:
            products = [item for item in products if query in item.get("name", "").casefold() or query in item.get("brand", "").casefold() or query in item.get("category", "").casefold()]
        if sort == "score_desc":
            products.sort(key=lambda item: (item.get("score", 0), item.get("product_id", 0)), reverse=True)
        elif sort == "price_desc":
            products.sort(key=lambda item: item.get("price", 0), reverse=True)
        elif sort == "price_asc":
            products.sort(key=lambda item: item.get("price", 0))
        else:
            products.sort(key=lambda item: (item.get("score", 0), item.get("product_id", 0)))
        return templates.TemplateResponse(
            request=request,
            name="data_quality_dashboard.html",
            context={
                "report": report,
                "products": products[:250],
                "selected_issue": issue,
                "selected_level": level,
                "selected_sort": sort,
                "search": search,
                "fixed": fixed,
                "fields": fields,
            },
        )
    finally:
        db.close()


@router.post("/fix-safe")
def data_quality_fix_safe(
    product_ids: list[int] = Form(default=[]),
    issue: str = Form(default="all"),
    return_issue: str = Form(default="all"),
    return_level: str = Form(default="all"),
    return_sort: str = Form(default="score_asc"),
    return_search: str = Form(default=""),
):
    db = SessionLocal()
    try:
        result = apply_safe_fixes(
            db,
            product_ids=product_ids or None,
            issue=None if issue in {"all", "safe"} else issue,
        )
    finally:
        db.close()
    query = urlencode({
        "issue": return_issue,
        "level": return_level,
        "sort": return_sort,
        "search": return_search,
        "fixed": result["updated"],
        "fields": result["fields_changed"],
    })
    return RedirectResponse(url=f"/admin/data-quality?{query}", status_code=303)


@router.get("/api", response_class=JSONResponse)
def data_quality_api():
    db = SessionLocal()
    try:
        return build_data_quality_report(db, limit=1000)
    finally:
        db.close()


@router.get("/export")
def data_quality_export():
    db = SessionLocal()
    try:
        path = write_data_quality_report(db)
        return FileResponse(path, media_type="application/json", filename="firsatai_data_quality_report.json")
    finally:
        db.close()
