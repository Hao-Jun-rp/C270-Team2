"""
BOOKING (Ashish) — connected to the database.

- The Services page passes a service_id to /booking/add ("Book Now").
- The form lists the REAL services from the database.
- Time slots are generated from each service's real duration, so a
  "4 - 5 Hours" job gets 5-hour slots, not a 1-hour slot.
- A demo payment step is validated server-side. Card details are
  checked (Luhn, expiry, CVV) and then DISCARDED — never stored.
- Submitting saves a real Booking row AND fires a real notification.
- The list page shows that user's real bookings.
"""
import math
import re
from datetime import date, datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Service, Booking, Review

booking_bp = Blueprint("booking", __name__, template_folder="templates", url_prefix="/booking")


# =========================================================
# Time slots — generated from the service's real duration
# =========================================================
DAY_START = 9   # first slot can start at 09:00
DAY_END = 18    # every slot must END by 18:00


def duration_hours(duration_str):
    """'2 - 3 Hours' -> 3,  '3 Hours' -> 3,  '4 - 5 Hours' -> 5.

    We block out the MAXIMUM of the range so a slot always fits the job
    even on a slow day. Unknown/garbled text falls back to 1 hour.
    """
    numbers = re.findall(r"\d+(?:\.\d+)?", duration_str or "")
    if not numbers:
        return 1
    return max(1, math.ceil(max(float(n) for n in numbers)))


def slots_for(hours):
    """All start times (hourly, from 09:00) where start+hours ends by 18:00.
    e.g. 3 -> ['09:00–12:00', '10:00–13:00', ..., '15:00–18:00']"""
    return [f"{start:02d}:00–{start + hours:02d}:00"
            for start in range(DAY_START, DAY_END - hours + 1)]


def slot_start_passed(slot):
    """True if this slot's START time is at or before the current time.
    Used to reject 'today' bookings for slots that have already begun.
    Slot looks like '09:00–12:00'; we read the start hour before the dash."""
    try:
        start = slot.split("–")[0]                 # "09:00"
        start_hour, start_min = (int(x) for x in start.split(":"))
    except (ValueError, IndexError):
        return True  # unparseable -> treat as invalid/passed, be safe
    now = datetime.now()
    return (start_hour, start_min) <= (now.hour, now.minute)


def build_services_meta(services):
    """Per-service info the form needs: price, duration text and the
    valid slots. Sent to the template as JSON so the slot dropdown can
    rebuild itself when the user changes service."""
    return {
        s.id: {
            "name": s.name,
            "price": s.price,
            "duration": s.duration,
            "slots": slots_for(duration_hours(s.duration)),
        }
        for s in services
    }


# =========================================================
# Payment validation (demo) — details are checked, NOT stored
# =========================================================
PAYMENT_METHODS = {"PayNow", "Card", "Cash"}


def luhn_ok(number):
    """Standard card-number checksum. Catches typos/made-up numbers."""
    total = 0
    for i, ch in enumerate(reversed(number)):
        digit = int(ch)
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def validate_card(form):
    """Return an error message, or None if the card details look valid.
    We only VALIDATE these fields — they are never saved anywhere."""
    name = form.get("card_name", "").strip()
    number = re.sub(r"[\s-]", "", form.get("card_number", ""))
    expiry = form.get("card_expiry", "").strip()
    cvv = form.get("card_cvv", "").strip()

    if not name:
        return "Please enter the cardholder name."
    if not (number.isdigit() and 13 <= len(number) <= 19 and luhn_ok(number)):
        return "That card number doesn't look valid — please check it."
    match = re.fullmatch(r"(0[1-9]|1[0-2])\s*/\s*(\d{2})", expiry)
    if not match:
        return "Card expiry must be in MM/YY format, e.g. 08/27."
    month, year = int(match.group(1)), 2000 + int(match.group(2))
    today = date.today()
    if (year, month) < (today.year, today.month):
        return "That card has expired."
    if not re.fullmatch(r"\d{3,4}", cvv):
        return "CVV must be 3 or 4 digits."
    return None


# =========================================================
# Routes
# =========================================================
@booking_bp.route("/")
@login_required
def index():
    bookings = (Booking.query
                .filter_by(user_id=current_user.id)
                .order_by(Booking.date.desc())
                .all())

    # Services this user has ALREADY reviewed (any status) - used to hide the
    # "Write a review" button on bookings for a service they've already reviewed.
    reviewed_service_ids = {
        r.service_id for r in Review.query.filter_by(user_id=current_user.id).all()
    }

    return render_template("booking/index.html", bookings=bookings,
                           reviewed_service_ids=reviewed_service_ids)


@booking_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_booking():
    services = Service.query.filter_by(is_active=True).order_by(Service.name).all()
    services_meta = build_services_meta(services)
    today = date.today().isoformat()

    def show_form(form_values):
        """Re-render the form (used for errors), keeping what was typed.
        Card fields are deliberately NOT echoed back."""
        sid = form_values.get("service_id")
        return render_template(
            "booking/addbooking.html",
            services=services, services_meta=services_meta, today=today,
            selected_slots=services_meta.get(sid, {}).get("slots", []),
            form=form_values,
        )

    if request.method == "POST":
        service_id = request.form.get("service_id", type=int)
        booking_date = request.form.get("date", "").strip()
        time = request.form.get("time", "").strip()
        address = request.form.get("address", "").strip()
        notes = request.form.get("notes", "").strip()
        payment_method = request.form.get("payment_method", "").strip()

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
        elif time not in services_meta[service.id]["slots"]:
            # Blocks stale/forged slots, e.g. a 1-hour slot for a 5-hour job.
            error = (f"That time slot doesn't fit {service.name} "
                     f"({service.duration}) — please pick a slot from the list.")
        elif parsed_date == date.today() and slot_start_passed(time):
            # Booking for TODAY: the slot's start time must still be ahead of
            # us. (Rejecting past dates isn't enough — "09:00" is invalid at 3pm.)
            error = "That time slot has already started — please pick a later slot."
        elif payment_method not in PAYMENT_METHODS:
            error = "Please choose how you'd like to pay."
        elif payment_method == "Card":
            error = validate_card(request.form)  # None if the card is fine

        if error:
            flash(error, "error")
            return show_form({"service_id": service_id, "date": booking_date,
                              "time": time, "address": address, "notes": notes,
                              "payment_method": payment_method})

        # Demo payment: PayNow/Card are treated as paid; Cash = pay after
        # the clean. Card details above were validated and thrown away.
        payment_status = "Paid (demo)" if payment_method in ("PayNow", "Card") else "Unpaid"

        booking = Booking(
            user_id=current_user.id,
            service_id=service.id,
            date=booking_date,
            time=time,
            address=address,
            notes=notes,
            status="Pending",
            payment_method=payment_method,
            payment_status=payment_status,
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

        pay_note = "Payment received (demo)." if payment_status.startswith("Paid") \
                   else "You'll pay after the clean."
        flash(f"Booking for {service.name} requested — we'll confirm it shortly! {pay_note}",
              "success")
        return redirect(url_for("booking.index"))

    preselect = request.args.get("service_id", type=int)
    return render_template(
        "booking/addbooking.html",
        services=services, services_meta=services_meta, today=today,
        selected_slots=services_meta.get(preselect, {}).get("slots", []),
        form={"service_id": preselect},
    )
