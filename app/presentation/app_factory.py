from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.presentation.api.routes import router as api_router
from app.presentation.api.camera_routes import router as camera_router
from app.presentation.api.overlay_routes import router as overlay_router
from app.hotkeys import hotkeys


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.include_router(camera_router)
    app.include_router(overlay_router)
    return app


app = create_app()


@app.on_event("startup")
async def _startup() -> None:
    if settings.auto_bootstrap:
        try:
            from app.infrastructure.obs.bootstrap import wire_default_layout

            await wire_default_layout()
        except Exception as exc:
            print(f"[bootstrap] skipped or failed: {exc}")
    hotkeys.start()


@app.on_event("shutdown")
async def _shutdown() -> None:
    hotkeys.stop()
