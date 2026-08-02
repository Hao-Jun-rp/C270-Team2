"""
This is the heart of the app. create_app() builds the website by:
  1. loading settings,
  2. switching on the database + login tools,
  3. plugging in each teammate's feature ("blueprint"),
  4. creating the database tables.
You almost never need to edit this file unless you're adding a new feature.
"""
from flask import Flask
import logging
import sys
from .config import Config
from .extensions import db, login_manager


def configure_logging(app):
    """Sends app logs to stdout instead of print(), so Docker/AWS can
    pick them up (docker logs / CloudWatch just read whatever the
    container writes to stdout — no extra config needed on their end).

    Uses Flask's built-in app.logger rather than the root logger, so
    routes call it as current_app.logger.info(...) / .warning(...) / .error(...).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    ))

    app.logger.handlers.clear()  # avoid duplicate log lines if create_app() runs twice (e.g. tests)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    configure_logging(app)

    # Turn on the database and the login system.
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # where to send logged-out users

    # ---- Register each teammate's feature ----
    from .main.routes import main_bp
    from .auth.routes import auth_bp
    from .dashboard.routes import dashboard_bp
    from .listings.routes import listings_bp
    from .booking.routes import booking_bp
    from .reviews.routes import reviews_bp
    from .notifications.routes import notifications_bp
    from .admin.routes import admin_bp
    from .monitoring.routes import monitoring_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(listings_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(monitoring_bp)

    # Create the database file + tables the first time we run.
    with app.app_context():
        from . import models  # noqa: F401  (imported so tables are registered)
        db.create_all()

    return app
