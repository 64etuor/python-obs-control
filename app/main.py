from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import router as api_router
from .hotkeys import hotkeys


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
    return app


app = create_app()


@app.on_event("startup")
async def _startup() -> None:
    hotkeys.start()


@app.on_event("shutdown")
async def _shutdown() -> None:
    hotkeys.stop()

