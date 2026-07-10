"""
DASHBOARD feature (Tristan) — now reads the user's real bookings.
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..models import Booking

dashboard_bp = Blueprint("dashboard", __name__, template_folder="templates")


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def home():
    bookings = (Booking.query
                .filter_by(user_id=current_user.id)
                .order_by(Booking.date.desc())
                .all())

    # Real summary counts for this user.
    summary = {
        "Pending": sum(1 for b in bookings if b.status == "Pending"),
        "Confirmed": sum(1 for b in bookings if b.status == "Confirmed"),
        "Completed": sum(1 for b in bookings if b.status == "Completed"),
    }

    # Show the 5 most recent on the dashboard; full list lives on /booking.
    return render_template("dashboard/home.html",
                           bookings=bookings[:5], summary=summary)
