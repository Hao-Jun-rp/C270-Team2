<<<<<<< HEAD
import os
import pytest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import create_app
=======
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
>>>>>>> 89cc33061444f52b7702ef941d09fd8038ff3f29


@pytest.fixture
def app():
<<<<<<< HEAD
    app = create_app()

    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })

    yield app
=======
    """A fresh Flask app + fresh empty database, for one test."""
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
>>>>>>> 89cc33061444f52b7702ef941d09fd8038ff3f29


@pytest.fixture
def client(app):
<<<<<<< HEAD
    return app.test_client()
=======
    """A fake browser that can send GET/POST requests to the app."""
    return app.test_client()
>>>>>>> 89cc33061444f52b7702ef941d09fd8038ff3f29
