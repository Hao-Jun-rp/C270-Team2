"""
Shared pytest setup (fixtures) for all test files.

A "fixture" is just a reusable chunk of setup code. Any test function that
takes `app` or `client` as an argument automatically gets a fresh one.

IMPORTANT: this uses an in-memory SQLite database, NOT the shared Aiven
database from .env. Tests never touch the real team data.
"""
import pytest
from app import create_app
from app.extensions import db


class TestConfig:
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}


@pytest.fixture
def app():
    """A fresh Flask app + fresh empty database, for one test."""
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A fake browser that can send GET/POST requests to the app."""
    return app.test_client()
