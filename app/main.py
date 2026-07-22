import uvicorn

from app.api.application import create_application
from app.core.logger import configure_logging
from app.core.runtime import ensure_supported_python
from app.loader import build_container

ensure_supported_python()
configure_logging()

container = build_container()
asgi_app = create_application(container)


def main() -> None:
    uvicorn.run(
        asgi_app,
        host=container.settings.APP_HOST,
        port=container.settings.APP_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
