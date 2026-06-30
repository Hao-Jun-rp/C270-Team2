"""
This is the heart of the app. create_app() builds the website by:
  1. loading settings,
  2. switching on the database + login tools,
  3. plugging in each teammate's feature ("blueprint"),
  4. creating the database tables.
You almost never need to edit this file unless you're adding a new feature.
"""
from flask import Flask
from .config import Config
from .extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Turn on the database and the login system.
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # where to send logged-out users

    # ---- Register each teammate's feature ----
    from .auth.routes import auth_bp
    from .dashboard.routes import dashboard_bp
    from .listings.routes import listings_bp
    from .booking.routes import booking_bp
    from .reviews.routes import reviews_bp
    from .notifications.routes import notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(listings_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(notifications_bp)

    # Create the database file + tables the first time we run.
    with app.app_context():
        from . import models  # noqa: F401  (imported so tables are registered)
        db.create_all()

    return app
