"""
BOOKING (Ashish) — connected to the database.

- The Services page passes a service_id to /booking/add ("Book Now").
- The form lists the REAL services from the database.
- Submitting saves a real Booking row AND fires a real notification.
- The list page shows that user's real bookings.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Service, Booking

booking_bp = Blueprint("booking", __name__, template_folder="templates", url_prefix="/booking")


@booking_bp.route("/")
@login_required
def index():
    bookings = (Booking.query
                .filter_by(user_id=current_user.id)
                .order_by(Booking.date.desc())
                .all())
    return render_template("booking/index.html", bookings=bookings)


@booking_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_booking():
    services = Service.query.filter_by(is_active=True).order_by(Service.name).all()

    if request.method == "POST":
        service_id = request.form.get("service_id", type=int)
        date = request.form.get("date", "").strip()
        time = request.form.get("time", "").strip()
        address = request.form.get("address", "").strip()
        notes = request.form.get("notes", "").strip()

        service = Service.query.get(service_id) if service_id else None

        if not service or not date or not time or not address:
            flash("Please pick a service and fill in the date, time and address.", "error")
            return render_template(
                "booking/addbooking.html",
                services=services,
                form={"service_id": service_id, "date": date,
                      "time": time, "address": address, "notes": notes},
            )

        booking = Booking(
            user_id=current_user.id,
            service_id=service.id,
            date=date,
            time=time,
            address=address,
            notes=notes,
            status="Pending",
        )
        db.session.add(booking)
        db.session.commit()

        # Fire a REAL notification off the real booking (not hand-typed/demo data).
        from ..notifications.routes import create_notification
        create_notification(
            current_user.id,
            f"Your booking for {service.name} on {date} at {time} "
            f"has been received and is pending confirmation.",
        )

        flash(f"Booking for {service.name} requested — we'll confirm it shortly!", "success")
        return redirect(url_for("booking.index"))

    preselect = request.args.get("service_id", type=int)
    return render_template(
        "booking/addbooking.html",
        services=services,
        form={"service_id": preselect},
    )
