"""
wsgi.py — WSGI entry point for gunicorn and Azure App Service.
"""
from app import create_app

application = create_app()

if __name__ == "__main__":
    application.run()
