"""
Tests for the Auth feature (Marcus).

Covers registration, login/logout, and the password-reset token flow.

Run all tests:       pytest
Run just this file:  pytest tests/test_auth.py -v
"""
from app.extensions import db
from app.models import User


def make_user(email="aisha@example.com", password="password123",
              name="Aisha", role="customer"):
    """Helper: create a saved user with a hashed password."""
    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


# ---------------------------------------------------------------
# Registration
# ---------------------------------------------------------------
def test_register_creates_user_and_hashes_password(app, client):
    """A valid registration saves the user AND never stores the raw password."""
    response = client.post("/register", data={
        "name": "New Customer",
        "email": "new@example.com",
        "password": "secret123",
        "confirm": "secret123",
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="new@example.com").first()
        assert user is not None
        # The raw password must never appear in the database.
        assert user.password_hash != "secret123"
        assert "secret123" not in user.password_hash
        # But it must still verify correctly.
        assert user.check_password("secret123")
        # New accounts are customers, never admins.
        assert user.role == "customer"


def test_register_rejects_duplicate_email(app, client):
    """Two accounts can't share an email — the second attempt is refused."""
    with app.app_context():
        make_user(email="taken@example.com")

    client.post("/register", data={
        "name": "Impostor",
        "email": "taken@example.com",
        "password": "secret123",
        "confirm": "secret123",
    }, follow_redirects=True)

    with app.app_context():
        assert User.query.filter_by(email="taken@example.com").count() == 1


def test_register_rejects_mismatched_passwords(app, client):
    """If the two password boxes don't match, no account is created."""
    client.post("/register", data={
        "name": "Typo Person",
        "email": "typo@example.com",
        "password": "secret123",
        "confirm": "secret124",
    }, follow_redirects=True)

    with app.app_context():
        assert User.query.filter_by(email="typo@example.com").first() is None


# ---------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------
def test_login_with_correct_password_succeeds(app, client):
    """Correct credentials log the user in and reach the dashboard."""
    with app.app_context():
        make_user()

    response = client.post("/login", data={
        "email": "aisha@example.com",
        "password": "password123",
    }, follow_redirects=True)

    assert response.status_code == 200
    # The dashboard is login-only, so reaching it proves the session works.
    assert client.get("/dashboard").status_code == 200


def test_login_with_wrong_password_fails(app, client):
    """A wrong password does NOT create a session."""
    with app.app_context():
        make_user()

    client.post("/login", data={
        "email": "aisha@example.com",
        "password": "wrong-password",
    }, follow_redirects=True)

    # Still logged out, so /dashboard bounces to the login page.
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logout_ends_the_session(app, client):
    """After logging out, protected pages are no longer reachable."""
    with app.app_context():
        make_user()
    client.post("/login", data={"email": "aisha@example.com",
                                "password": "password123"})
    assert client.get("/dashboard").status_code == 200

    client.get("/logout")

    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------
# Forgot / reset password (CA2 enhancement)
# ---------------------------------------------------------------
def test_reset_token_lets_user_set_a_new_password(app, client):
    """A genuine reset token allows a password change, and the new password
    works while the old one stops working."""
    with app.app_context():
        from app.auth.routes import _reset_serializer
        user = make_user(email="forgot@example.com", password="oldpass123")
        token = _reset_serializer().dumps({"uid": user.id})

    response = client.post(f"/reset/{token}", data={
        "password": "newpass123",
        "confirm": "newpass123",
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="forgot@example.com").first()
        assert user.check_password("newpass123")
        assert not user.check_password("oldpass123")


def test_tampered_reset_token_is_rejected(app, client):
    """A token that has been edited fails its signature check, so the
    password is left untouched."""
    with app.app_context():
        from app.auth.routes import _reset_serializer
        user = make_user(email="target@example.com", password="oldpass123")
        token = _reset_serializer().dumps({"uid": user.id})

    tampered = token[:-3] + "xyz"
    client.post(f"/reset/{tampered}", data={
        "password": "hacked123",
        "confirm": "hacked123",
    }, follow_redirects=True)

    with app.app_context():
        user = User.query.filter_by(email="target@example.com").first()
        assert user.check_password("oldpass123")
        assert not user.check_password("hacked123")


def test_expired_reset_token_is_rejected(app, client, monkeypatch):
    """A token older than the 30-minute limit is refused. We simulate age by
    temporarily setting the maximum age to 0 seconds."""
    import app.auth.routes as auth_routes

    with app.app_context():
        user = make_user(email="slow@example.com", password="oldpass123")
        token = auth_routes._reset_serializer().dumps({"uid": user.id})

    monkeypatch.setattr(auth_routes, "RESET_TOKEN_MAX_AGE", -1)

    client.post(f"/reset/{token}", data={
        "password": "toolate123",
        "confirm": "toolate123",
    }, follow_redirects=True)

    with app.app_context():
        user = User.query.filter_by(email="slow@example.com").first()
        assert user.check_password("oldpass123")
