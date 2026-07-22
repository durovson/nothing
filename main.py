from app.main import asgi_app as app
from app.main import main

__all__ = ["app", "main"]


if __name__ == "__main__":
    main()
