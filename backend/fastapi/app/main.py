from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .routers import assessments, health

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(title="SoulSense FastAPI")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(assessments.router)

    @app.on_event("startup")
    async def startup_event():
        app.state.settings = settings

    return app


app = create_app()
