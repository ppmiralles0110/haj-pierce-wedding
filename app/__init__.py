# =============================================================================
# app/__init__.py — Flask Application Factory
# Wedding Website | Flask + SQLAlchemy + Azure
# =============================================================================
"""
Application factory module.

Creates and configures the Flask application instance, registers all
blueprints, initialises extensions, and wires up error handlers and
context processors.  Import ``create_app`` anywhere you need a fully
configured application object.
"""

import logging
from typing import Optional

from flask import Flask, render_template, session

from app.config import Config
from app.extensions import db, migrate, limiter


# ---------------------------------------------------------------------------
# Logging — set early so every module that imports this one gets a handler
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_object: Optional[object] = None) -> Flask:
    """
    Create and configure the Flask application using the factory pattern.

    Args:
        config_object: Optional config class/object to override defaults.
                       Useful for testing (pass a TestConfig).

    Returns:
        A fully configured Flask application instance.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # ------------------------------------------------------------------
    # 1. Load Configuration
    # ------------------------------------------------------------------
    if config_object is None:
        app.config.from_object(Config)
    else:
        app.config.from_object(config_object)

    # ------------------------------------------------------------------
    # 2. Initialise Extensions
    # ------------------------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # ------------------------------------------------------------------
    # 3. Register Blueprints
    # ------------------------------------------------------------------
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.rsvp import rsvp_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(rsvp_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    # ------------------------------------------------------------------
    # 4. Context Processors — inject wedding config & theme vars globally
    # ------------------------------------------------------------------
    @app.context_processor
    def inject_wedding_config() -> dict:
        """
        Inject wedding configuration and CSS theme variables into every
        Jinja2 template context so templates never need to query the DB
        directly.

        Returns:
            Dict with ``wedding_config`` (dict) and ``theme`` (dict).
        """
        from app.models.wedding_config import WeddingConfig
        try:
            config_rows = WeddingConfig.query.all()
            wedding_config = {row.key: row.value for row in config_rows}
        except Exception:
            # DB might not be ready (e.g. first migration run)
            wedding_config = {}

        theme = {
            "color_primary": wedding_config.get("color_primary", "#c9a96e"),
            "color_secondary": wedding_config.get("color_secondary", "#e8c4b8"),
            "color_accent": wedding_config.get("color_accent", "#ff6b35"),
            "font_heading": wedding_config.get("font_heading", "Cormorant Garamond"),
            "font_subheading": wedding_config.get("font_subheading", "Montserrat"),
            "font_body": wedding_config.get("font_body", "Lato"),
        }

        return {
            "wedding_config": wedding_config,
            "theme": theme,
            # Convenience shorthand used in many templates
            "current_user_email": session.get("user_email"),
            "is_authenticated": session.get("authenticated", False),
            "is_admin": session.get("is_admin", False),
        }

    # ------------------------------------------------------------------
    # 5. Azure Application Insights telemetry (no-op if key absent)
    # ------------------------------------------------------------------
    _setup_app_insights(app)

    # ------------------------------------------------------------------
    # 6. Error Handlers
    # ------------------------------------------------------------------
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limited(e):
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Unhandled 500 error: %s", e)
        return render_template("errors/500.html"), 500

    logger.info("Flask application created successfully.")
    return app


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _setup_app_insights(app: Flask) -> None:
    """
    Configure Azure Application Insights via opencensus if the
    APPINSIGHTS_INSTRUMENTATIONKEY is present in the app config.

    Args:
        app: Configured Flask application instance.
    """
    key = app.config.get("APPINSIGHTS_INSTRUMENTATIONKEY")
    if not key:
        logger.info("App Insights key not set — telemetry disabled.")
        return

    try:
        from opencensus.ext.azure.trace_exporter import AzureExporter
        from opencensus.ext.flask.flask_middleware import FlaskMiddleware
        from opencensus.trace.samplers import ProbabilitySampler

        FlaskMiddleware(
            app,
            exporter=AzureExporter(connection_string=f"InstrumentationKey={key}"),
            sampler=ProbabilitySampler(rate=1.0),
        )
        logger.info("Azure Application Insights telemetry enabled.")
    except ImportError:
        logger.warning("opencensus-ext-azure not installed — telemetry disabled.")
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to set up App Insights: %s", exc)
