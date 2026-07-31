from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database.database import create_db
from app.scheduler import start_scheduler, stop_scheduler

from app.web.admin_routes import router as admin_router
from app.web.admin_category_routes import router as admin_category_router
from app.routes.favorites import router as favorites_router
from app.web.category_routes import router as category_router
from app.web.dashboard_routes import router as dashboard_router
from app.web.product_routes import router as product_router
from app.web.routes import router as main_router
from app.web.whatsapp_routes import router as whatsapp_router
from app.web.product_group_routes import (
    router as product_group_router,
)

from app.routes.scrape import router as scrape_router
from app.routes.comparison import router as comparison_router
from app.routes.search import router as search_router
from app.routes.history import router as history_router
from app.web.whatsapp_admin_routes import (
    router as whatsapp_admin_router,
)



BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "app" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Fırsat AI başlatılıyor...")

    # Veritabanını oluştur / güncelle
    create_db()
    print("Veritabanı kontrol edildi ve hazırlandı.")

    # Scheduler'ı başlat
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


# Routerlar
app.include_router(admin_router)
app.include_router(admin_category_router)
app.include_router(product_group_router)
app.include_router(main_router)
app.include_router(category_router)
app.include_router(dashboard_router)
app.include_router(product_router)
app.include_router(whatsapp_router)
app.include_router(scrape_router)
app.include_router(comparison_router)
app.include_router(search_router)
app.include_router(history_router)
app.include_router(whatsapp_admin_router)
app.include_router(favorites_router)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Fırsat AI",
    }