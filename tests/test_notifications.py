"""
Tests for the notifications feature (Hao Jun).
Run with:  pytest tests/test_notifications.py
"""
from app.extensions import db
from app.models import User, Notification
from app.notifications.routes import create_notification


def _make_user(email="user@test.com"):
    """Small helper: create + save a user, return it."""
    u = User(name="Test User", email=email)
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()
    return u


def test_create_notification_saves_it_for_the_right_user(app):
    """create_notification() should add a row that belongs to the given user."""
    with app.app_context():
        user = _make_user()
        create_notification(user.id, "Your booking is confirmed.", link="/booking")

        saved = Notification.query.filter_by(user_id=user.id).first()
        assert saved is not None
        assert saved.message == "Your booking is confirmed."
        assert saved.link == "/booking"
        assert saved.is_read is False  # new notifications start unread


def test_unread_api_only_returns_that_users_unread_notifications(app, client):
    """/api/unread should return only the logged-in user's unread items —
    not another user's, and not ones already marked read."""
    with app.app_context():
        me = _make_user("me@test.com")
        someone_else = _make_user("other@test.com")

        create_notification(me.id, "For me, unread")
        read_one = create_notification(me.id, "For me, already read")
        read_one.is_read = True
        db.session.commit()

        create_notification(someone_else.id, "For someone else")

    client.post("/login", data={"email": "me@test.com", "password": "password123"})
    resp = client.get("/notifications/api/unread")
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["count"] == 1
    assert data["items"][0]["message"] == "For me, unread"


def test_user_cannot_mark_another_users_notification_as_read(app, client):
    """Marking a notification as read should fail (404) if it doesn't
    belong to the logged-in user — this is the IDOR protection check."""
    with app.app_context():
        owner = _make_user("owner@test.com")
        _make_user("attacker@test.com")
        notif = create_notification(owner.id, "Private notification")
        notif_id = notif.id

    client.post("/login", data={"email": "attacker@test.com", "password": "password123"})
    resp = client.post(f"/notifications/api/{notif_id}/read")

    assert resp.status_code == 404

    with app.app_context():
        # confirm it's genuinely untouched, not just an error response
        still_unread = db.session.get(Notification, notif_id)
        assert still_unread.is_read is False
