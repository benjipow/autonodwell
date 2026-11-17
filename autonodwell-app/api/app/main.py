from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import admin, customer, public, sales

settings = get_settings()

app = FastAPI(
    title="Autonodwell API",
    version="0.1.0",
    description="Single API for the Autonodwell web app, sales console and future native apps.",
    docs_url="/api/docs" if settings.env != "production" else None,
    openapi_url="/api/openapi.json",
    # Clean operation ids (e.g. "create_design") -> readable generated clients for web and native.
    generate_unique_id_function=lambda route: route.name,
)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

# Everything lives under /api so the web app can serve it same-origin (Firebase Hosting
# rewrite /api/** -> Cloud Run). Versioned: a breaking change ships as /api/v2 while
# installed mobile apps keep using /api/v1.
for r in (public.router, customer.router, sales.router, admin.router):
    app.include_router(r, prefix="/api/v1")
