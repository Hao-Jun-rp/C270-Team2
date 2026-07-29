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
- Customers can CANCEL or EDIT their own upcoming bookings (see bottom).
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


def validate_slot(service, date_str, time_str):
    """Shared date+slot validation used by BOTH create and edit.
    Returns (parsed_date, error_message). parsed_date is a date object
    when valid, else None."""
    parsed_date = None
    if date_str:
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            parsed_date = None

    if not parsed_date:
        return None, "That date doesn't look right — please pick a valid date."
    if parsed_date < date.today():
        return None, "You can't book a date in the past — please pick today or a later date."

    valid_slots = slots_for(duration_hours(service.duration))
    if time_str not in valid_slots:
        return None, (f"That time slot doesn't fit {service.name} "
                      f"({service.duration}) — please pick a slot from the list.")
    if parsed_date == date.today() and slot_start_passed(time_str):
        return None, "That time slot has already started — please pick a later slot."
    return parsed_date, None


# =========================================================
# List + create
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

        error = None
        parsed_date = None
        if not service or not booking_date or not time or not address:
            error = "Please pick a service and fill in the date, time and address."
        else:
            parsed_date, error = validate_slot(service, booking_date, time)
        if not error and payment_method not in PAYMENT_METHODS:
            error = "Please choose how you'd like to pay."
        elif not error and payment_method == "Card":
            error = validate_card(request.form)  # None if the card is fine

        if error:
            flash(error, "error")
            return show_form({"service_id": service_id, "date": booking_date,
                              "time": time, "address": address, "notes": notes,
                              "payment_method": payment_method})

        # Demo payment: PayNow/Card are AUTHORIZED at booking time (the money
        # is reserved, not taken) and only captured -> "Paid (demo)" when the
        # admin CONFIRMS the booking. Cash = pay after the clean. Card details
        # above were validated and thrown away.
        payment_status = ("Authorized (demo)" if payment_method in ("PayNow", "Card")
                          else "Unpaid")

        booking = Booking(
            user_id=current_user.id,
            service_id=service.id,
            date=parsed_date,
            time=time,
            address=address,
            notes=notes,
            status="Pending",
            payment_method=payment_method,
            payment_status=payment_status,
        )
        db.session.add(booking)
        db.session.commit()

        from ..notifications.routes import create_notification
        create_notification(
            current_user.id,
            f"Your booking for {service.name} on {parsed_date.isoformat()} at {time} "
            f"has been received and is pending confirmation.",
            link=url_for("booking.index"),
        )

        pay_note = ("Payment authorized (demo) - it is captured when we "
                    "confirm your booking.") if payment_status.startswith("Authorized") \
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


# =========================================================
# Customer self-service: EDIT and CANCEL own bookings
# =========================================================
# A customer can only touch a booking that is theirs AND still upcoming
# (Pending or Confirmed). Completed/Cancelled bookings are locked.
EDITABLE_STATUSES = ("Pending", "Confirmed")


def _own_active_booking_or_none(booking_id):
    """Fetch a booking only if it belongs to the current user and is still
    Pending/Confirmed. Returns None otherwise (used to block tampering)."""
    booking = Booking.query.filter_by(id=booking_id,
                                      user_id=current_user.id).first()
    if not booking or booking.status not in EDITABLE_STATUSES:
        return None
    return booking


@booking_bp.route("/<int:booking_id>/edit", methods=["GET", "POST"])
@login_required
def edit_booking(booking_id):
    booking = _own_active_booking_or_none(booking_id)
    if not booking:
        flash("That booking can't be edited (it may be completed or cancelled).",
              "error")
        return redirect(url_for("booking.index"))

    # The service is fixed on edit — to change service, cancel + rebook.
    service = booking.service
    slots = slots_for(duration_hours(service.duration))
    today = date.today().isoformat()

    if request.method == "POST":
        booking_date = request.form.get("date", "").strip()
        time = request.form.get("time", "").strip()
        address = request.form.get("address", "").strip()
        notes = request.form.get("notes", "").strip()

        error = None
        if not booking_date or not time or not address:
            error = "Please fill in the date, time and address."
        else:
            parsed_date, error = validate_slot(service, booking_date, time)

        if error:
            flash(error, "error")
            return render_template("booking/editbooking.html", booking=booking,
                                   service=service, slots=slots, today=today,
                                   form={"date": booking_date, "time": time,
                                         "address": address, "notes": notes})

        # Did anything actually change? (used to decide re-confirmation)
        changed = (parsed_date != booking.date or time != booking.time
                   or address != booking.address or (notes or "") != (booking.notes or ""))

        booking.date = parsed_date
        booking.time = time
        booking.address = address
        booking.notes = notes

        # Editing a CONFIRMED booking sends it back to Pending so the admin
        # re-confirms it (availability may have changed). Pending stays Pending.
        reverted = False
        if changed and booking.status == "Confirmed":
            booking.status = "Pending"
            # Keep the demo-payment story consistent: Pending means "not captured
            # yet", so a captured PayNow/Card payment goes back to Authorized.
            if booking.payment_status == "Paid (demo)":
                booking.payment_status = "Authorized (demo)"
            reverted = True

        db.session.commit()

        if reverted:
            from ..notifications.routes import create_notification
            create_notification(
                current_user.id,
                f"Your {service.name} booking was updated and is pending "
                f"re-confirmation.",
                link=url_for("booking.index"))
            flash("Booking updated. Because you changed a confirmed booking, "
                  "it's pending re-confirmation.", "success")
        else:
            flash("Booking updated.", "success")
        return redirect(url_for("booking.index"))

    # GET — pre-fill the form with the current values.
    return render_template("booking/editbooking.html", booking=booking,
                           service=service, slots=slots, today=today,
                           form={"date": booking.date.isoformat(),
                                 "time": booking.time,
                                 "address": booking.address,
                                 "notes": booking.notes or ""})


@booking_bp.route("/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    booking = _own_active_booking_or_none(booking_id)
    if not booking:
        flash("That booking can't be cancelled (it may be completed or already "
              "cancelled).", "error")
        return redirect(url_for("booking.index"))

    booking.status = "Cancelled"
    # Release the demo payment: an authorized/captured PayNow/Card amount is
    # "refunded" when the customer cancels. Cash was never collected.
    if booking.payment_status in ("Authorized (demo)", "Paid (demo)"):
        booking.payment_status = "Refunded (demo)"
    db.session.commit()

    from ..notifications.routes import create_notification
    create_notification(
        current_user.id,
        f"You cancelled your {booking.service.name} booking on "
        f"{booking.date.isoformat()}.",
        link=url_for("booking.index"))

    flash(f"Your {booking.service.name} booking has been cancelled.", "success")
    return redirect(url_for("booking.index"))
