from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

# Uncomment these two lines when you wire the form to the real database:
# from ..extensions import db
# from ..models import Booking

booking_bp = Blueprint("booking", __name__, template_folder="templates", url_prefix="/booking")

# Mock data — still used by the list page until the DB step is done.
MOCK_BOOKINGS = [
    {
        "id": 1,
        "service": "Deep Clean",
        "date": "2027-01-15",
        "time": "10:00–11:00",
        "status": "Confirmed",
        "address": "12 Orchard Road, Singapore",
        "notes": "Please bring eco products."
    },
    {
        "id": 2,
        "service": "Standard Clean",
        "date": "2027-01-22",
        "time": "14:00–15:00",
        "status": "Pending",
        "address": "88 Tanjong Pagar, Singapore",
        "notes": ""
    }
]


@booking_bp.route("/")
@login_required
def index():
    return render_template("booking/index.html", bookings=MOCK_BOOKINGS)


@booking_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_booking():
    # ---- Someone submitted the form ----
    if request.method == "POST":
        service_name = request.form.get("service_name", "").strip()
        date = request.form.get("date", "").strip()
        time = request.form.get("time", "").strip()
        address = request.form.get("address", "").strip()
        notes = request.form.get("notes", "").strip()

        # Simple check so we don't accept an empty booking.
        if not (service_name and date and time and address):
            flash("Please fill in the service, date, time and address.", "error")
            return redirect(url_for("booking.add_booking",
                                    service=service_name,
                                    service_id=request.form.get("service_id", "")))

        # ------------------------------------------------------------------
        # TODO (database step): once services live in the DB, save for real:
        #
        #   booking = Booking(
        #       user_id=current_user.id,
        #       service_id=request.form.get("service_id", type=int),
        #       date=date, time=time, address=address, notes=notes,
        #       status="Pending",
        #   )
        #   db.session.add(booking)
        #   db.session.commit()
        #
        # …and change index() above to:
        #   bookings = Booking.query.filter_by(user_id=current_user.id).all()
        # ------------------------------------------------------------------

        flash(f"Booking request for {service_name} received — we'll confirm it shortly!", "success")
        return redirect(url_for("booking.index"))

    # ---- GET: show the form, pre-filled from the "Book Now" button ----
    service_name = request.args.get("service", "")
    service_id = request.args.get("service_id", "")
    price = request.args.get("price", "")
    return render_template(
        "booking/addbooking.html",
        service_name=service_name,
        service_id=service_id,
        price=price,
    )
