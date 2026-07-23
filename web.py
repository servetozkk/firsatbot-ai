from app.web.whatsapp_routes import router as whatsapp_router
from app.web.dashboard_routes import router as dashboard_router
from contextlib import asynccontextmanager
from app.web.dashboard_routes import router as dashboard_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.scheduler import start_scheduler, stop_scheduler
from app.web.routes import router
from app.web.product_routes import router as product_router
from app.web.category_routes import router as category_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_scheduler()

    try:
        yield

    finally:
        await stop_scheduler()


app = FastAPI(
    title="Fırsat AI",
    lifespan=lifespan,
)

app.mount(
    "/static",
    StaticFiles(directory="app/web/static"),
    name="static",
)

app.include_router(product_router)
app.include_router(category_router)
app.include_router(dashboard_router)
app.include_router(router)
app.include_router(whatsapp_router)
from app.web.dashboard_routes import router as dashboard_router