from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import API_PREFIX, APP_NAME, CORS_ORIGINS, DEBUG
from app.core.database import init_db
from app.core.response import fail
from app.routers import admin_api, admin_content, admin_dashboard, admin_earth_online, admin_enrichment, admin_review, admin_scenic, admin_system, comments, earth_online, map_provider, public, scenic, search, user, weather, public_content
from app.services.seed import seed_data

app = FastAPI(title=APP_NAME, debug=DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else (["*"] if DEBUG else []),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    seed_data()


@app.exception_handler(Exception)
async def unhandled_exception(_: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    error_msg = str(exc) if DEBUG else "Internal Server Error"
    return JSONResponse(status_code=500, content=fail(error_msg))


for router in [
    public.router,
    scenic.router,
    search.router,
    map_provider.router,
    weather.router,
    comments.router,
    earth_online.router,
    user.router,
    public_content.router,
    admin_dashboard.router,
    admin_scenic.router,
    admin_review.router,
    admin_content.router,
    admin_api.router,
    admin_earth_online.router,
    admin_enrichment.router,
    admin_system.router,
]:
    app.include_router(router, prefix=API_PREFIX)
