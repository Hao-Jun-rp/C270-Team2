"""
A tiny "smoke test": does the app start and does the home page load?
Run it with:  pytest
Later this becomes the 'test' step of your CI/CD pipeline (Phase 2).
"""
from app import create_app


def test_home_page_loads():
    app = create_app()
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
