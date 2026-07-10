"""
notifications feature (Hao Jun) — you OWN this folder.

Schema note: the shared Notification table (models.py, owned by Marcus)
currently only has: id, user_id, message, is_read, created_at.
There's no title/type/due_at/status — so this feature is "instant
message, read or unread," not a scheduled/timed reminder. If you want
reminders that fire at a future time (e.g. "1 hour before a booking"),
you'll need to ask Marcus to add a `due_at` (DateTime) and `status`
column back — message him rather than editing models.py yourself.
"""
from datetime import datetime
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Notification, Booking, Service

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications", template_folder="templates")


@notifications_bp.route("/")
@login_required
def index():
    items = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template("notifications/index.html", notifications=items)


@notifications_bp.route("/api/unread")
@login_required
def api_unread():
    """Polled by base.html's bell dropdown."""
    items = (
        Notification.query.filter_by(user_id=current_user.id, is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(6)
        .all()
    )
    return jsonify({
        "count": len(items),
        "items": [
            {
                "id": n.id,
                "message": n.message,
                "created_at": n.created_at.isoformat() + "Z",
            }
            for n in items
        ],
    })


@notifications_bp.route("/api/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_read(notif_id):
    n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
    if not n:
        return jsonify({"error": "not found"}), 404
    n.is_read = True
    db.session.commit()
    return jsonify({"ok": True})


@notifications_bp.route("/api/<int:notif_id>/delete", methods=["POST"])
@login_required
def delete(notif_id):
    """No 'cancelled' status exists anymore, so removing a notification
    means deleting the row outright."""
    n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
    if not n:
        return jsonify({"error": "not found"}), 404
    db.session.delete(n)
    db.session.commit()
    return jsonify({"ok": True})


@notifications_bp.route("/api/demo", methods=["POST"])
@login_required
def demo():
    """Creates a sample notification for the logged-in user so you can
    demo/prove the feature works without wiring it up to bookings yet."""
    create_notification(current_user.id, "This is a test notification — everything's working!")
    return jsonify({"ok": True})


@notifications_bp.route("/api/demo-booking", methods=["POST"])
@login_required
def demo_booking():
    """Simulates a real booking: creates an actual Booking row (linked to
    a real Service row) and fires a notification off THAT data — not
    hand-typed text. This proves the models.py -> notification wiring
    works before Ashish's real booking-creation page exists.

    Once he builds the real 'confirm booking' route in app/booking/routes.py,
    delete this route and just call notify_booking_confirmed(booking) there
    instead, right after the real Booking row is committed.
    """
    service = Service.query.first()
    if not service:
        # No services in the DB yet (listings still uses hardcoded data) —
        # seed one minimal row so this demo has something real to point at.
        service = Service(
            name="Home Cleaning",
            category="Home",
            description="Standard home cleaning service.",
            price=45.0,
            duration="2 - 3 Hours",
        )
        db.session.add(service)
        db.session.commit()

    booking = Booking(
        user_id=current_user.id,
        service_id=service.id,
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        time="14:00",
        address="123 Demo Street",
        status="Confirmed",
    )
    db.session.add(booking)
    db.session.commit()

    notify_booking_confirmed(booking)
    return jsonify({"ok": True, "service": service.name, "booking_id": booking.id})


@notifications_bp.route("/api/demo-reminder", methods=["POST"])
@login_required
def demo_reminder():
    """Fires the 'your booking is coming up soon' style notification.

    IMPORTANT: this does NOT actually wait — it's called by the frontend
    AFTER a client-side delay (see the JS in index.html), purely so you
    can visually demo what a delayed reminder would look like. True
    scheduled sends (e.g. 'fire exactly 1 hour before due_at, whenever
    that turns out to be') aren't possible yet because Notification has
    no due_at column — see the note at the top of this file.
    """
    booking = (
        Booking.query.filter_by(user_id=current_user.id)
        .order_by(Booking.id.desc())
        .first()
    )
    if not booking:
        # No booking to remind about yet — reuse the same demo-booking
        # logic so this button works standalone too.
        service = Service.query.first()
        if not service:
            service = Service(
                name="Home Cleaning", category="Home",
                description="Standard home cleaning service.",
                price=45.0, duration="2 - 3 Hours",
            )
            db.session.add(service)
            db.session.commit()
        booking = Booking(
            user_id=current_user.id, service_id=service.id,
            date=datetime.utcnow().strftime("%Y-%m-%d"), time="14:00",
            address="123 Demo Street", status="Confirmed",
        )
        db.session.add(booking)
        db.session.commit()

    notify_booking_reminder(booking)
    return jsonify({"ok": True, "service": booking.service.name})


def notify_booking_reminder(booking):
    """Call this closer to booking.date/time (e.g. from a scheduled job,
    once due_at exists) to remind the customer their cleaner is coming up.
    Pulls the service/date/time straight off the real Booking row.
    """
    message = (
        f"Reminder: your {booking.service.name} booking is coming up "
        f"soon — {booking.date} at {booking.time}."
    )
    return create_notification(booking.user_id, message)


def notify_booking_confirmed(booking):
    """Call this right after a Booking row is created (e.g. from
    app/booking/routes.py, once the real booking flow exists) to notify
    the customer. Pulls the service name/date/time straight off the
    Booking -> Service relationship in models.py, so the message always
    reflects the real booking — never hand-typed text that could drift
    out of sync with what was actually booked.
    """
    message = (
        f"Your booking for {booking.service.name} on {booking.date} "
        f"at {booking.time} has been confirmed."
    )
    return create_notification(booking.user_id, message)


def create_notification(user_id, message):
    """Helper other blueprints can import to send a notification, e.g.
    from app.notifications.routes import create_notification
    create_notification(user_id=booking.user_id, message="Your booking was confirmed.")

    Note: this fires immediately (there's no due_at to delay it).
    """
    n = Notification(user_id=user_id, message=message, is_read=False)
    db.session.add(n)
    db.session.commit()
    return n
