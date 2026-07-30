"""
Smoke test: does the app start and does the home page load?

FIXED: this previously called create_app() with no arguments, which loads the
REAL config. Because app/config.py calls load_dotenv(), anyone with a .env
pointing at the shared Aiven database was running this test against LIVE TEAM
DATA (and on a bare CI runner it silently created an instance/sparkle.db file).

Using the `client` fixture from conftest.py instead means every test runs
against a throwaway in-memory SQLite database — isolated, fast, and safe.
"""


def test_home_page_loads(client):
    """The landing page should render for a logged-out visitor."""
    response = client.get("/")
    assert response.status_code == 200


def test_login_page_loads(client):
    """The login page should be reachable without being logged in."""
    response = client.get("/login")
    assert response.status_code == 200


def test_unknown_page_returns_404(client):
    """A route that doesn't exist should 404, not 500."""
    response = client.get("/this-page-does-not-exist")
    assert response.status_code == 404


def test_protected_page_redirects_when_logged_out(client):
    """The dashboard is @login_required, so an anonymous visitor should be
    redirected to the login page rather than shown the page."""
    response = client.get("/dashboard")
    assert response.status_code in (301, 302)
    assert "/login" in response.headers.get("Location", "")
