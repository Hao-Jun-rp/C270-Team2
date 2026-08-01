"""
Tests for the Admin feature (Marcus).

Three groups:
  1. Access control  — @admin_required keeps non-admins out.
  2. Booking status  — only sensible transitions are allowed (server-side).
  3. Payment lifecycle — the CA2 fix: money is captured on Confirm, not at
     booking time.

Run all tests:       pytest
Run just this file:  pytest tests/test_admin.py -v
"""
from datetime import date, timedelta

from app.extensions import db
from app.models import User, Service, Booking, Review, Notification


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def make_user(email, role="customer", password="password123"):
    user = User(name="Test Person", email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def make_service(name="Deep Cleaning"):
    service = Service(name=name, category="Home", description="A deep clean.",
                      price=120.0, duration="3 - 4 Hours", is_active=True)
    db.session.add(service)
    db.session.commit()
    return service


def make_booking(user, service, status="Pending",
                 payment_method="PayNow", payment_status="Authorized (demo)"):
    booking = Booking(user_id=user.id, service_id=service.id,
                      date=date.today() + timedelta(days=3),
                      time="09:00-12:00", address="1 Test Road",
                      status=status, payment_method=payment_method,
                      payment_status=payment_status)
    db.session.add(booking)
    db.session.commit()
    return booking


def login(client, email, password="password123"):
    return client.post("/login", data={"email": email, "password": password})


# ===============================================================
# 1. Access control — @admin_required
# ===============================================================
def test_anonymous_visitor_is_sent_to_login(client):
    """Logged-out visitors never see admin pages; they're sent to login."""
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logged_in_customer_is_refused(app, client):
    """A normal customer who knows the URL is still refused — the check is
    server-side, not just a hidden nav link."""
    with app.app_context():
        make_user("customer@example.com")
    login(client, "customer@example.com")

    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/admin" not in response.headers["Location"]


def test_admin_can_open_the_admin_dashboard(app, client):
    """An admin account reaches the dashboard normally."""
    with app.app_context():
        make_user("marcus@sparkle.sg", role="admin")
    login(client, "marcus@sparkle.sg")

    assert client.get("/admin/").status_code == 200


# ===============================================================
# 2. Booking status transitions
# ===============================================================
def test_admin_can_confirm_a_pending_booking(app, client):
    """Pending -> Confirmed is a legal move and is saved."""
    with app.app_context():
        admin = make_user("marcus@sparkle.sg", role="admin")
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Pending")
        booking_id = booking.id
    login(client, "marcus@sparkle.sg")

    client.post(f"/admin/bookings/{booking_id}/status",
                data={"status": "Confirmed"}, follow_redirects=True)

    with app.app_context():
        assert db.session.get(Booking, booking_id).status == "Confirmed"


def test_completed_booking_cannot_be_moved_back_to_pending(app, client):
    """Completed is final. A crafted request trying Completed -> Pending is
    rejected server-side, so the booking is unchanged."""
    with app.app_context():
        make_user("marcus@sparkle.sg", role="admin")
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Completed")
        booking_id = booking.id
    login(client, "marcus@sparkle.sg")

    client.post(f"/admin/bookings/{booking_id}/status",
                data={"status": "Pending"}, follow_redirects=True)

    with app.app_context():
        assert db.session.get(Booking, booking_id).status == "Completed"


def test_pending_booking_cannot_skip_straight_to_completed(app, client):
    """A job can't be finished before it's confirmed — Pending -> Completed
    is not in the allowed transitions."""
    with app.app_context():
        make_user("marcus@sparkle.sg", role="admin")
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Pending")
        booking_id = booking.id
    login(client, "marcus@sparkle.sg")

    client.post(f"/admin/bookings/{booking_id}/status",
                data={"status": "Completed"}, follow_redirects=True)

    with app.app_context():
        assert db.session.get(Booking, booking_id).status == "Pending"


def test_customer_cannot_change_a_booking_status(app, client):
    """The status endpoint is admin-only — a customer POSTing to it directly
    changes nothing."""
    with app.app_context():
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Pending")
        booking_id = booking.id
    login(client, "customer@example.com")

    client.post(f"/admin/bookings/{booking_id}/status",
                data={"status": "Confirmed"}, follow_redirects=True)

    with app.app_context():
        assert db.session.get(Booking, booking_id).status == "Pending"


# ===============================================================
# 3. Payment lifecycle (the CA2 "Pending but already Paid?" fix)
# ===============================================================
def test_card_payment_is_captured_only_when_admin_confirms(app, client):
    """Authorized (demo) -> Paid (demo) happens on Confirm, not at booking."""
    with app.app_context():
        make_user("marcus@sparkle.sg", role="admin")
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Pending",
                               payment_method="PayNow",
                               payment_status="Authorized (demo)")
        booking_id = booking.id
    login(client, "marcus@sparkle.sg")

    client.post(f"/admin/bookings/{booking_id}/status",
                data={"status": "Confirmed"}, follow_redirects=True)

    with app.app_context():
        assert db.session.get(Booking, booking_id).payment_status == "Paid (demo)"


def test_cancelling_refunds_an_authorized_payment(app, client):
    """Cancelling releases the authorisation as a demo refund."""
    with app.app_context():
        make_user("marcus@sparkle.sg", role="admin")
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Pending",
                               payment_status="Authorized (demo)")
        booking_id = booking.id
    login(client, "marcus@sparkle.sg")

    client.post(f"/admin/bookings/{booking_id}/status",
                data={"status": "Cancelled"}, follow_redirects=True)

    with app.app_context():
        assert db.session.get(Booking, booking_id).payment_status == "Refunded (demo)"


def test_cash_booking_is_paid_only_on_completion(app, client):
    """Cash stays Unpaid until the job is done, then flips to paid."""
    with app.app_context():
        make_user("marcus@sparkle.sg", role="admin")
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Confirmed",
                               payment_method="Cash", payment_status="Unpaid")
        booking_id = booking.id
    login(client, "marcus@sparkle.sg")

    client.post(f"/admin/bookings/{booking_id}/status",
                data={"status": "Completed"}, follow_redirects=True)

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == "Completed"
        assert booking.payment_status == "Paid (cash on completion)"


# ===============================================================
# 4. Review moderation keeps the public rating correct
# ===============================================================
def test_approving_a_review_updates_the_service_rating(app, client):
    """Service.rating is a stored average of APPROVED reviews only, so
    approving one must recompute it."""
    with app.app_context():
        make_user("marcus@sparkle.sg", role="admin")
        customer = make_user("customer@example.com")
        service = make_service()
        review = Review(user_id=customer.id, service_id=service.id, rating=4,
                        review_description="Very thorough.", status="Pending")
        db.session.add(review)
        db.session.commit()
        review_id, service_id = review.id, service.id
        # A pending review must not count towards the public score yet.
        assert db.session.get(Service, service_id).rating == 0.0
    login(client, "marcus@sparkle.sg")

    client.post(f"/admin/reviews/{review_id}",
                data={"action": "approve"}, follow_redirects=True)

    with app.app_context():
        assert db.session.get(Review, review_id).status == "Approved"
        assert db.session.get(Service, service_id).rating == 4.0


# ===============================================================
# 5. Completion notification adapts to whether they've reviewed
# ===============================================================
def test_completion_invites_a_review_when_they_havent_reviewed(app, client):
    """First completed booking for a service: prompt them to review."""
    with app.app_context():
        make_user("marcus@sparkle.sg", role="admin")
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Confirmed",
                               payment_method="Cash", payment_status="Unpaid")
        booking_id, customer_id = booking.id, customer.id
    login(client, "marcus@sparkle.sg")

    client.post(f"/admin/bookings/{booking_id}/status",
                data={"status": "Completed"}, follow_redirects=True)

    with app.app_context():
        note = (Notification.query.filter_by(user_id=customer_id)
                .order_by(Notification.id.desc()).first())
        assert note is not None
        assert "leave a review" in note.message


def test_completion_does_not_reinvite_a_review_already_left(app, client):
    """Reviews are one-per-service. A repeat customer who already reviewed
    this service must NOT be prompted to review it again — the link would
    lead to a page with no review form (a dead end)."""
    with app.app_context():
        make_user("marcus@sparkle.sg", role="admin")
        customer = make_user("customer@example.com")
        service = make_service()
        db.session.add(Review(user_id=customer.id, service_id=service.id,
                              rating=5, review_description="Great first clean.",
                              status="Approved"))
        booking = make_booking(customer, service, status="Confirmed",
                               payment_method="Cash", payment_status="Unpaid")
        db.session.commit()
        booking_id, customer_id = booking.id, customer.id
    login(client, "marcus@sparkle.sg")

    client.post(f"/admin/bookings/{booking_id}/status",
                data={"status": "Completed"}, follow_redirects=True)

    with app.app_context():
        note = (Notification.query.filter_by(user_id=customer_id)
                .order_by(Notification.id.desc()).first())
        assert note is not None
        assert "leave a review" not in note.message
        assert "complete" in note.message.lower()
