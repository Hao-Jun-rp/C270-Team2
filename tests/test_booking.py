"""
Tests for the Booking feature (Ashish).

Four groups:
  1. Time slots       — slots are generated from the service's real duration.
  2. Payment validation — Luhn checksum, expiry, CVV are checked server-side.
  3. Create a booking  — the full happy-path flow, plus rejecting bad input.
  4. Edit / cancel     — customers can only touch their own, still-upcoming
                         bookings; editing a Confirmed booking reverts it to
                         Pending for re-confirmation.

Run all tests:       pytest
Run just this file:  pytest tests/test_booking.py -v
"""
from datetime import date, timedelta

from app.extensions import db
from app.models import User, Service, Booking
from app.booking.routes import duration_hours, slots_for, luhn_ok, validate_card


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def make_user(email, role="customer", password="password123"):
    user = User(name="Test Person", email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def make_service(name="Deep Cleaning", duration="4 - 5 Hours"):
    service = Service(name=name, category="Home", description="A deep clean.",
                      price=120.0, duration=duration, is_active=True)
    db.session.add(service)
    db.session.commit()
    return service


def make_booking(user, service, status="Pending",
                 payment_method="Cash", payment_status="Unpaid"):
    booking = Booking(user_id=user.id, service_id=service.id,
                      date=date.today() + timedelta(days=3),
                      time="09:00–12:00", address="1 Test Road",
                      status=status, payment_method=payment_method,
                      payment_status=payment_status)
    db.session.add(booking)
    db.session.commit()
    return booking


def login(client, email, password="password123"):
    return client.post("/login", data={"email": email, "password": password})


VALID_CARD = {
    "card_name": "Test User",
    "card_number": "4539 1488 0343 6467",   # passes Luhn
    "card_expiry": "12/30",
    "card_cvv": "123",
}


# ===============================================================
# 1. Time slots — generated from the service's real duration
# ===============================================================
def test_duration_hours_reads_the_bigger_number_in_a_range():
    """'2 - 3 Hours' should block out 3 hours, not 2 — always round up to
    the safer, longer estimate."""
    assert duration_hours("2 - 3 Hours") == 3
    assert duration_hours("4 - 5 Hours") == 5
    assert duration_hours("3 Hours") == 3


def test_duration_hours_falls_back_to_one_hour_on_garbage_text():
    """Unparseable duration text shouldn't crash the slot generator."""
    assert duration_hours("") == 1
    assert duration_hours("ASAP") == 1


def test_slots_fit_within_the_working_day():
    """A 5-hour job starting any later than 13:00 wouldn't finish by 18:00,
    so the last valid slot must start at 13:00, not later."""
    slots = slots_for(5)
    assert "09:00–14:00" in slots
    assert "13:00–18:00" in slots
    assert "14:00–19:00" not in slots  # would run past closing time


# ===============================================================
# 2. Payment validation — Luhn, expiry, CVV
# ===============================================================
def test_luhn_accepts_a_valid_card_number():
    assert luhn_ok("4539148803436467") is True


def test_luhn_rejects_a_made_up_number():
    """A typo'd/fake card number should fail the checksum, not just look
    like a string of the right length."""
    assert luhn_ok("1234567812345678") is False


def test_validate_card_rejects_expired_card():
    form = {**VALID_CARD, "card_expiry": "01/20"}
    error = validate_card(form)
    assert error is not None
    assert "expired" in error.lower()


def test_validate_card_rejects_bad_cvv():
    form = {**VALID_CARD, "card_cvv": "12"}
    error = validate_card(form)
    assert error is not None
    assert "CVV" in error


def test_validate_card_accepts_a_fully_valid_card():
    assert validate_card(VALID_CARD) is None


# ===============================================================
# 3. Creating a booking
# ===============================================================
def test_customer_can_book_a_valid_slot(app, client):
    """The full happy path: pick a real service, a valid slot, pay by
    cash — a Booking row should exist afterwards."""
    with app.app_context():
        make_user("customer@example.com")
        service = make_service()
        service_id = service.id
    login(client, "customer@example.com")

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    client.post("/booking/add", data={
        "service_id": service_id, "date": tomorrow, "time": "09:00–14:00",
        "address": "1 Test Road", "notes": "", "payment_method": "Cash",
    }, follow_redirects=True)

    with app.app_context():
        booking = Booking.query.filter_by(service_id=service_id).first()
        assert booking is not None
        assert booking.status == "Pending"
        assert booking.payment_status == "Unpaid"


def test_cannot_book_a_slot_that_does_not_fit_the_service(app, client):
    """A 1-hour slot doesn't fit a 5-hour "Deep Cleaning" job — the booking
    should be rejected, not silently accepted."""
    with app.app_context():
        make_user("customer@example.com")
        service = make_service(duration="4 - 5 Hours")
        service_id = service.id
    login(client, "customer@example.com")

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    client.post("/booking/add", data={
        "service_id": service_id, "date": tomorrow, "time": "09:00–10:00",
        "address": "1 Test Road", "notes": "", "payment_method": "Cash",
    }, follow_redirects=True)

    with app.app_context():
        assert Booking.query.filter_by(service_id=service_id).first() is None


def test_cannot_book_a_date_in_the_past(app, client):
    with app.app_context():
        make_user("customer@example.com")
        service = make_service()
        service_id = service.id
    login(client, "customer@example.com")

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    client.post("/booking/add", data={
        "service_id": service_id, "date": yesterday, "time": "09:00–14:00",
        "address": "1 Test Road", "notes": "", "payment_method": "Cash",
    }, follow_redirects=True)

    with app.app_context():
        assert Booking.query.filter_by(service_id=service_id).first() is None


def test_card_payment_is_authorized_not_paid_at_booking_time(app, client):
    """Card/PayNow bookings start as 'Authorized (demo)', not 'Paid (demo)'
    — the money is only captured when an admin confirms it later."""
    with app.app_context():
        make_user("customer@example.com")
        service = make_service()
        service_id = service.id
    login(client, "customer@example.com")

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    client.post("/booking/add", data={
        "service_id": service_id, "date": tomorrow, "time": "09:00–14:00",
        "address": "1 Test Road", "notes": "", "payment_method": "Card",
        **VALID_CARD,
    }, follow_redirects=True)

    with app.app_context():
        booking = Booking.query.filter_by(service_id=service_id).first()
        assert booking is not None
        assert booking.payment_status == "Authorized (demo)"


def test_invalid_card_number_blocks_the_booking(app, client):
    with app.app_context():
        make_user("customer@example.com")
        service = make_service()
        service_id = service.id
    login(client, "customer@example.com")

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    client.post("/booking/add", data={
        "service_id": service_id, "date": tomorrow, "time": "09:00–14:00",
        "address": "1 Test Road", "notes": "", "payment_method": "Card",
        **{**VALID_CARD, "card_number": "4539148803436466"},  # fails Luhn (last digit off)
    }, follow_redirects=True)

    with app.app_context():
        assert Booking.query.filter_by(service_id=service_id).first() is None


# ===============================================================
# 4. Edit / cancel — ownership rules and the Confirmed -> Pending revert
# ===============================================================
def test_customer_cannot_edit_someone_elses_booking(app, client):
    with app.app_context():
        owner = make_user("owner@example.com")
        make_user("stranger@example.com")
        service = make_service()
        booking = make_booking(owner, service, status="Pending")
        booking_id = booking.id
    login(client, "stranger@example.com")

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    client.post(f"/booking/{booking_id}/edit", data={
        "date": tomorrow, "time": "09:00–14:00",
        "address": "Somewhere else", "notes": "",
    }, follow_redirects=True)

    with app.app_context():
        assert db.session.get(Booking, booking_id).address == "1 Test Road"


def test_completed_booking_cannot_be_edited(app, client):
    """A finished job is locked — no further changes allowed."""
    with app.app_context():
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Completed")
        booking_id = booking.id
    login(client, "customer@example.com")

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    client.post(f"/booking/{booking_id}/edit", data={
        "date": tomorrow, "time": "09:00–14:00",
        "address": "New Address", "notes": "",
    }, follow_redirects=True)

    with app.app_context():
        assert db.session.get(Booking, booking_id).address == "1 Test Road"


def test_editing_a_confirmed_booking_reverts_it_to_pending(app, client):
    """Changing the date/time/address on a Confirmed booking sends it back
    to Pending, since the admin needs to re-confirm availability."""
    with app.app_context():
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Confirmed",
                               payment_method="Card",
                               payment_status="Paid (demo)")
        booking_id = booking.id
    login(client, "customer@example.com")

    new_date = (date.today() + timedelta(days=5)).isoformat()
    client.post(f"/booking/{booking_id}/edit", data={
        "date": new_date, "time": "09:00–14:00",
        "address": "New Address", "notes": "",
    }, follow_redirects=True)

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == "Pending"
        # A captured payment should drop back to Authorized, since it's no
        # longer confirmed.
        assert booking.payment_status == "Authorized (demo)"


def test_editing_a_pending_booking_without_changes_stays_pending(app, client):
    """Re-submitting the exact same details shouldn't trigger a needless
    'pending re-confirmation' notification."""
    with app.app_context():
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Pending")
        booking_id = booking.id
        original_date = booking.date.isoformat()

    login(client, "customer@example.com")
    client.post(f"/booking/{booking_id}/edit", data={
        "date": original_date, "time": "09:00–12:00",
        "address": "1 Test Road", "notes": "",
    }, follow_redirects=True)

    with app.app_context():
        assert db.session.get(Booking, booking_id).status == "Pending"


def test_cancelling_a_booking_marks_it_cancelled(app, client):
    with app.app_context():
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Pending")
        booking_id = booking.id
    login(client, "customer@example.com")

    client.post(f"/booking/{booking_id}/cancel", follow_redirects=True)

    with app.app_context():
        assert db.session.get(Booking, booking_id).status == "Cancelled"


def test_cancelling_refunds_an_authorized_card_payment(app, client):
    with app.app_context():
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Pending",
                               payment_method="Card",
                               payment_status="Authorized (demo)")
        booking_id = booking.id
    login(client, "customer@example.com")

    client.post(f"/booking/{booking_id}/cancel", follow_redirects=True)

    with app.app_context():
        assert db.session.get(Booking, booking_id).payment_status == "Refunded (demo)"


def test_cannot_cancel_an_already_completed_booking(app, client):
    with app.app_context():
        customer = make_user("customer@example.com")
        service = make_service()
        booking = make_booking(customer, service, status="Completed")
        booking_id = booking.id
    login(client, "customer@example.com")

    client.post(f"/booking/{booking_id}/cancel", follow_redirects=True)

    with app.app_context():
        assert db.session.get(Booking, booking_id).status == "Completed"
