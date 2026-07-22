from fastapi import FastAPI

from app.api.lifecycle import create_lifespan
from app.api.routes import create_api_router
from app.loader import AppContainer


def create_application(container: AppContainer) -> FastAPI:
    application = FastAPI(
        title=container.settings.APP_NAME,
        lifespan=create_lifespan(container),
    )
    application.include_router(create_api_router(container))
    return application

