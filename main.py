from app.main import create_asgi_app, main

app = create_asgi_app()

__all__ = ["app", "main"]


if __name__ == "__main__":
    main()
