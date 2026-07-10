"""
BOOKING (Ashish) — connected to the database.

- The Services page passes a service_id to /booking/add ("Book Now").
- The form lists the REAL services from the database.
- Submitting saves a real Booking row AND fires a real notification.
- The list page shows that user's real bookings.
"""
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Service, Booking, Review

booking_bp = Blueprint("booking", __name__, template_folder="templates", url_prefix="/booking")


@booking_bp.route("/")
@login_required
def index():
    bookings = (Booking.query
                .filter_by(user_id=current_user.id)
                .order_by(Booking.date.desc())
                .all())

    # Services this user has ALREADY reviewed (any status) - used to hide the
    # "Write a review" button on bookings for a service they've already reviewed.
    # Reviews are per-service (not per-booking), so this applies across all
    # of that user's bookings for the same service.
    reviewed_service_ids = {
        r.service_id for r in Review.query.filter_by(user_id=current_user.id).all()
    }

    return render_template("booking/index.html", bookings=bookings,
                           reviewed_service_ids=reviewed_service_ids)


@booking_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_booking():
    services = Service.query.filter_by(is_active=True).order_by(Service.name).all()
    today = date.today().isoformat()

    if request.method == "POST":
        service_id = request.form.get("service_id", type=int)
        booking_date = request.form.get("date", "").strip()
        time = request.form.get("time", "").strip()
        address = request.form.get("address", "").strip()
        notes = request.form.get("notes", "").strip()

        service = Service.query.get(service_id) if service_id else None

        # Parse + validate the date: must be a real date, and not in the past.
        parsed_date = None
        if booking_date:
            try:
                parsed_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
            except ValueError:
                parsed_date = None

        error = None
        if not service or not booking_date or not time or not address:
            error = "Please pick a service and fill in the date, time and address."
        elif not parsed_date:
            error = "That date doesn't look right — please pick a valid date."
        elif parsed_date < date.today():
            error = "You can't book a date in the past — please pick today or a later date."

        if error:
            flash(error, "error")
            return render_template(
                "booking/addbooking.html",
                services=services, today=today,
                form={"service_id": service_id, "date": booking_date,
                      "time": time, "address": address, "notes": notes},
            )

        booking = Booking(
            user_id=current_user.id,
            service_id=service.id,
            date=booking_date,
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
            f"Your booking for {service.name} on {booking_date} at {time} "
            f"has been received and is pending confirmation.",
            link=url_for("booking.index"),
        )

        flash(f"Booking for {service.name} requested — we'll confirm it shortly!", "success")
        return redirect(url_for("booking.index"))

    preselect = request.args.get("service_id", type=int)
    return render_template(
        "booking/addbooking.html",
        services=services, today=today,
        form={"service_id": preselect},
    )
