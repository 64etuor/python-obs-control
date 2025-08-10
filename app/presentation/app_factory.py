from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.infrastructure.metrics.metrics import setup_metrics
from app.infrastructure.logging_setup import init_logging
from app.presentation.api.routes import router as api_router
from app.presentation.api.camera_routes import router as camera_router
from app.presentation.api.overlay_routes import router as overlay_router
from app.hotkeys import hotkeys


def create_app() -> FastAPI:
    # Initialize logging before app construction to capture startup logs
    init_logging()
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

    # Prometheus metrics (/metrics) + psutil system/process gauges
    setup_metrics(app)
    return app


app = create_app()


@app.on_event("startup")
async def _startup() -> None:
    import logging
    logging.getLogger(__name__).info("application startup")
    if settings.auto_bootstrap:
        try:
            from app.infrastructure.obs.bootstrap import wire_default_layout

            await wire_default_layout()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("bootstrap skipped or failed: %s", exc)
    hotkeys.start()


@app.on_event("shutdown")
async def _shutdown() -> None:
    import logging
    logging.getLogger(__name__).info("application shutdown")
    hotkeys.stop()
