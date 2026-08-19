from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(include_in_schema=False)

@router.get('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools_probe() -> JSONResponse:
    """Chrome DevTools automatic probe; return a quiet valid response."""
    return JSONResponse(content={})
