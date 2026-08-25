from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.benchmark import router as benchmark_router
from app.api.simulation import router as simulation_router
from app.api.collaboration import router as collaboration_router
from app.common.config import get_settings
from app.api.health import router as health_router
from app.api.performance import router as performance_router

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(benchmark_router)
    app.include_router(simulation_router)
    app.include_router(performance_router)
    app.include_router(collaboration_router)
    return app

app = create_app()
