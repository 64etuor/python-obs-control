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
from typing import Optional
import asyncio

_guard_stop_event: Optional[asyncio.Event] = None
_guard_task: Optional[asyncio.Task] = None


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

    # Ensure OBS is running and reachable before bootstrap/hotkeys
    if settings.obs_autostart:
        try:
            # In Docker, skip OBS autostart unless explicitly disabled
            if not (settings.obs_skip_autostart_in_docker and _is_running_in_docker()):
                from app.infrastructure.obs.process import ensure_obs_running

                await ensure_obs_running()
            else:
                logging.getLogger(__name__).info("skip OBS autostart (running in container)")
        except Exception as exc:
            logging.getLogger(__name__).error("OBS autostart failed: %s", exc)

    if settings.auto_bootstrap:
        try:
            from app.infrastructure.obs.bootstrap import wire_default_layout

            await wire_default_layout()
        except Exception as exc:
            logging.getLogger(__name__).warning("bootstrap skipped or failed: %s", exc)

    hotkeys.start()

    # Start guardian loop to keep OBS alive
    if settings.obs_guardian_enabled and not (settings.obs_skip_autostart_in_docker and _is_running_in_docker()):
        try:
            from app.infrastructure.obs.process import guardian_loop

            global _guard_stop_event, _guard_task
            _guard_stop_event = asyncio.Event()
            _guard_task = asyncio.create_task(guardian_loop(_guard_stop_event))
        except Exception as exc:
            logging.getLogger(__name__).warning("failed to start OBS guardian: %s", exc)


@app.on_event("shutdown")
async def _shutdown() -> None:
    import logging
    logging.getLogger(__name__).info("application shutdown")
    hotkeys.stop()
    # stop guardian
    global _guard_stop_event, _guard_task
    try:
        if _guard_stop_event is not None:
            _guard_stop_event.set()
        if _guard_task is not None:
            _guard_task.cancel()
    except Exception:
        pass


def _is_running_in_docker() -> bool:
    try:
        # Heuristic: /.dockerenv or cgroup contains docker/kubepods
        from pathlib import Path

        if Path("/.dockerenv").exists():
            return True
        cgroup = Path("/proc/1/cgroup")
        if cgroup.exists():
            data = cgroup.read_text(errors="ignore")
            if "docker" in data or "kubepods" in data or "containerd" in data:
                return True
    except Exception:
        pass
    return False
