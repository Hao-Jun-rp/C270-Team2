"""
NOTIFICATIONS (Hao Jun) — real notifications, driven by real events.

Notifications are created by other features when something actually happens
(e.g. booking.routes calls create_notification after a booking is made).
The bell in base.html polls /api/unread; this page lists them all.
"""
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Notification

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications", template_folder="templates")


@notifications_bp.route("/")
@login_required
def index():
    items = (Notification.query.filter_by(user_id=current_user.id)
             .order_by(Notification.created_at.desc())
             .all())
    return render_template("notifications/index.html", notifications=items)


@notifications_bp.route("/api/unread")
@login_required
def api_unread():
    """Polled by base.html's bell dropdown."""
    items = (Notification.query.filter_by(user_id=current_user.id, is_read=False)
             .order_by(Notification.created_at.desc())
             .limit(6)
             .all())
    return jsonify({
        "count": len(items),
        "items": [
            {"id": n.id, "message": n.message, "created_at": n.created_at.isoformat() + "Z"}
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
    n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
    if not n:
        return jsonify({"error": "not found"}), 404
    db.session.delete(n)
    db.session.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Helpers other features import to SEND a notification when a real event happens.
#   from ..notifications.routes import create_notification
# ---------------------------------------------------------------------------
def create_notification(user_id, message):
    """Create + save one notification immediately."""
    n = Notification(user_id=user_id, message=message, is_read=False)
    db.session.add(n)
    db.session.commit()
    return n


def notify_booking_confirmed(booking):
    """Call after a booking's status becomes Confirmed (e.g. from an admin
    action later). Pulls details straight off the real Booking row."""
    return create_notification(
        booking.user_id,
        f"Your booking for {booking.service.name} on {booking.date} "
        f"at {booking.time} has been confirmed.",
    )
