import socket

import uvicorn

from app.api.application import create_application
from app.config import Settings, get_settings
from app.core.logger import configure_logging, uvicorn_log_config
from app.core.runtime import ensure_supported_python
from app.loader import build_container


def create_asgi_app(settings: Settings | None = None):
    """Application factory for external ASGI runners and local tooling."""
    ensure_supported_python()
    app_settings = settings or get_settings()
    return create_application(build_container(app_settings))


def _bind_http_socket(host: str, port: int) -> socket.socket:
    """Expose Render's required TCP port before expensive wallet initialization."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    listener = socket.socket(family=family, type=socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen(2_048)
    listener.setblocking(False)
    return listener


def main() -> None:
    ensure_supported_python()
    configure_logging()
    settings = get_settings()
    listener = _bind_http_socket(settings.APP_HOST, settings.APP_PORT)
    try:
        application = create_asgi_app(settings)
        config = uvicorn.Config(
            application,
            host=settings.APP_HOST,
            port=settings.APP_PORT,
            reload=False,
            log_config=uvicorn_log_config(),
        )
        uvicorn.Server(config).run(sockets=[listener])
    finally:
        listener.close()


if __name__ == "__main__":
    main()
