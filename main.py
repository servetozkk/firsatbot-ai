from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.scheduler import start_scheduler, stop_scheduler
from app.web.admin_routes import router as admin_router
from app.web.category_routes import router as category_router
from app.web.dashboard_routes import router as dashboard_router
from app.web.product_routes import router as product_router
from app.web.routes import router as main_router
from app.web.whatsapp_routes import router as whatsapp_router


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "app" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Fırsat AI başlatılıyor...")

    await start_scheduler()

    try:
        yield

    finally:
        print("Fırsat AI kapatılıyor...")

        await stop_scheduler()


app = FastAPI(
    title="Fırsat AI",
    version="1.0.0",
    lifespan=lifespan,
)


app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


app.include_router(admin_router)
app.include_router(main_router)
app.include_router(category_router)
app.include_router(dashboard_router)
app.include_router(product_router)
app.include_router(whatsapp_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Fırsat AI",
    }