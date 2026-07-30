import os
import pytest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import create_app


@pytest.fixture
def app():
    app = create_app()

    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })

    yield app


@pytest.fixture
def client(app):
    return app.test_client()