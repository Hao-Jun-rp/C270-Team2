"""
ADMIN routes (Marcus).  URL prefix: /admin  — every view is @admin_required.

What the admin can do, and the logic behind each:

BOOKINGS   (/admin/bookings)
  Customers create bookings as "Pending". Only an admin moves them along:
      Pending  -> Confirmed  (we notify the customer)
      Confirmed/Pending -> Completed (we notify + invite a review)
      any -> Cancelled
  We only allow sensible changes and always tell the customer via a real
  notification.

REVIEWS    (/admin/reviews)
  Customer reviews arrive as "Pending" and are invisible on the public page
  until approved. Admin can Approve or Hide, and add an optional staff reply.
  Because Service.rating is a stored average of APPROVED reviews, we
  recompute it every time approval status changes.

SERVICES   (/admin/services)
  Full CRUD. We DON'T hard-delete a service (bookings/reviews point at it) —
  instead we deactivate it (is_active=False) so it disappears from the
  Services page but existing records stay intact.
"""
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, abort, jsonify)

from ..extensions import db
from ..models import User, Service, Booking, Review, Notification
from ..notifications.routes import create_notification
from .decorators import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin",
                     template_folder="templates")

BOOKING_STATUSES = ["Pending", "Confirmed", "Completed", "Cancelled"]

# Which status changes an admin is allowed to make. Completed and Cancelled
# are terminal (no onward moves). This is enforced server-side so a crafted
# request can't do nonsense like Completed -> Pending.
ALLOWED_TRANSITIONS = {
    "Pending":   {"Confirmed", "Cancelled"},
    "Confirmed": {"Completed", "Cancelled"},
    "Completed": set(),
    "Cancelled": set(),
}


# ---------------------------------------------------------------
# Helper: keep Service.rating in sync with its APPROVED reviews
# ---------------------------------------------------------------
def recompute_service_rating(service):
    """Service.rating is the average of that service's APPROVED reviews
    (0.0 if it has none). Call this whenever a review is approved/hidden."""
    approved = Review.query.filter_by(service_id=service.id,
                                      status="Approved").all()
    service.rating = round(sum(r.rating for r in approved) / len(approved), 1) \
        if approved else 0.0


# ===============================================================
# Admin home — a quick "what needs my attention" overview
# ===============================================================
@admin_bp.route("/")
@admin_required
def dashboard():
    stats = {
        "pending_bookings": Booking.query.filter_by(status="Pending").count(),
        "confirmed_bookings": Booking.query.filter_by(status="Confirmed").count(),
        "pending_reviews": Review.query.filter_by(status="Pending").count(),
        "active_services": Service.query.filter_by(is_active=True).count(),
        "total_services": Service.query.count(),
        "customers": User.query.filter_by(role="customer").count(),
    }
    # The five most recent bookings, so the admin sees fresh activity.
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats,
                           recent_bookings=recent_bookings)


@admin_bp.route("/api/pending-count")
@admin_required
def pending_count():
    """Polled by the navbar so the admin badge updates without a refresh.
    Returns how many things currently need admin attention."""
    pending = (Booking.query.filter_by(status="Pending").count()
               + Review.query.filter_by(status="Pending").count())
    return jsonify({"pending": pending})


# ===============================================================
# Bookings management
# ===============================================================
@admin_bp.route("/bookings")
@admin_required
def bookings():
    status = request.args.get("status")  # optional filter
    query = Booking.query
    if status in BOOKING_STATUSES:
        query = query.filter_by(status=status)
    all_bookings = query.order_by(Booking.created_at.desc()).all()
    return render_template("admin/bookings.html", bookings=all_bookings,
                           statuses=BOOKING_STATUSES, active_status=status)


@admin_bp.route("/bookings/<int:booking_id>/status", methods=["POST"])
@admin_required
def update_booking_status(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    new_status = request.form.get("status", "").strip()

    if new_status not in BOOKING_STATUSES:
        flash("That isn't a valid booking status.", "error")
        return redirect(url_for("admin.bookings"))
    if new_status == booking.status:
        flash(f"Booking {booking.display_id} is already {new_status}.", "error")
        return redirect(url_for("admin.bookings"))
    if new_status not in ALLOWED_TRANSITIONS.get(booking.status, set()):
        # e.g. trying to move a Completed/Cancelled booking, or an illogical jump.
        flash(f"Can't change booking {booking.display_id} from "
              f"{booking.status} to {new_status}.", "error")
        return redirect(url_for("admin.bookings"))

    booking.status = new_status

    # Cash bookings are deliberately "Unpaid" until the job is done (that's
    # the whole point of "pay after the clean"). The moment an admin marks
    # the job Completed, the cash has been collected in person - so flip it
    # to paid here. PayNow/Card bookings were already paid at booking time
    # and are untouched.
    if new_status == "Completed" and booking.payment_method == "Cash" \
            and booking.payment_status == "Unpaid":
        booking.payment_status = "Paid (cash on completion)"

    db.session.commit()

    # Tell the customer what changed (real notification, links to their bookings).
    link = url_for("booking.index")
    if new_status == "Confirmed":
        create_notification(
            booking.user_id,
            f"Good news! Your {booking.service.name} booking on "
            f"{booking.date} at {booking.time} is confirmed.",
            link=link)
    elif new_status == "Completed":
        create_notification(
            booking.user_id,
            f"Your {booking.service.name} is complete — "
            f"leave a review to help others!",
            link=url_for("reviews.index", service=booking.service.name))
    elif new_status == "Cancelled":
        create_notification(
            booking.user_id,
            f"Your {booking.service.name} booking on {booking.date} "
            f"has been cancelled. Contact us if this is unexpected.",
            link=link)

    flash(f"Booking {booking.display_id} marked {new_status}.", "success")
    return redirect(url_for("admin.bookings", status=request.args.get("status")))


# ===============================================================
# Reviews moderation
# ===============================================================
@admin_bp.route("/reviews")
@admin_required
def reviews():
    # Pending first (they need action), then the rest, newest first.
    pending = (Review.query.filter_by(status="Pending")
               .order_by(Review.created_at.desc()).all())
    others = (Review.query.filter(Review.status != "Pending")
              .order_by(Review.created_at.desc()).all())
    return render_template("admin/reviews.html",
                           pending=pending, others=others)


@admin_bp.route("/reviews/<int:review_id>", methods=["POST"])
@admin_required
def moderate_review(review_id):
    review = Review.query.get_or_404(review_id)
    action = request.form.get("action", "").strip()      # approve / hide
    staff_reply = (request.form.get("staff_reply") or "").strip()

    if action not in ("approve", "hide"):
        flash("Unknown review action.", "error")
        return redirect(url_for("admin.reviews"))

    review.staff_reply = staff_reply or None
    review.status = "Approved" if action == "approve" else "Hidden"
    review.updated_at = datetime.utcnow()

    # Approving/hiding changes the service's public average — keep it correct.
    recompute_service_rating(review.service)
    db.session.commit()

    if action == "approve":
        create_notification(
            review.user_id,
            f"Your review for {review.service.name} is now live. Thank you!",
            link=url_for("reviews.index", service=review.service.name))
        flash(f"Review {review.display_id} approved and now public.", "success")
    else:
        flash(f"Review {review.display_id} hidden from the public page.", "success")
    return redirect(url_for("admin.reviews"))


# ===============================================================
# Services CRUD
# ===============================================================
@admin_bp.route("/services")
@admin_required
def services():
    all_services = Service.query.order_by(Service.id).all()
    return render_template("admin/services.html", services=all_services)


def _read_service_form(form):
    """Pull + validate the service fields from the form.
    Returns (data_dict, error_message). error is None when all good."""
    name = (form.get("name") or "").strip()
    category = (form.get("category") or "").strip()
    description = (form.get("description") or "").strip()
    duration = (form.get("duration") or "").strip()
    image = (form.get("image") or "").strip()
    price_raw = (form.get("price") or "").strip()

    if not name or not category or not description or not duration:
        return None, "Name, category, description and duration are all required."
    try:
        price = float(price_raw)
        if price < 0:
            raise ValueError
    except ValueError:
        return None, "Price must be a number (e.g. 45 or 59.90)."

    return {
        "name": name, "category": category, "description": description,
        "duration": duration, "image": image or None, "price": price,
    }, None


@admin_bp.route("/services/new", methods=["GET", "POST"])
@admin_required
def new_service():
    if request.method == "POST":
        data, error = _read_service_form(request.form)
        if error:
            flash(error, "error")
            return render_template("admin/service_form.html",
                                   service=None, form=request.form)
        service = Service(created_by=current_admin_id(), is_active=True, **data)
        db.session.add(service)
        db.session.commit()
        flash(f"Service '{service.name}' created.", "success")
        return redirect(url_for("admin.services"))

    return render_template("admin/service_form.html", service=None, form={})


@admin_bp.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_service(service_id):
    service = Service.query.get_or_404(service_id)
    if request.method == "POST":
        data, error = _read_service_form(request.form)
        if error:
            flash(error, "error")
            return render_template("admin/service_form.html",
                                   service=service, form=request.form)
        for key, value in data.items():
            setattr(service, key, value)
        service.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f"Service '{service.name}' updated.", "success")
        return redirect(url_for("admin.services"))

    return render_template("admin/service_form.html", service=service, form={})


@admin_bp.route("/services/<int:service_id>/toggle", methods=["POST"])
@admin_required
def toggle_service(service_id):
    """Soft delete / restore. We never hard-delete: bookings and reviews
    point at this service, so we just flip is_active."""
    service = Service.query.get_or_404(service_id)
    service.is_active = not service.is_active
    service.updated_at = datetime.utcnow()
    db.session.commit()
    state = "active" if service.is_active else "hidden"
    flash(f"Service '{service.name}' is now {state}.", "success")
    return redirect(url_for("admin.services"))


def current_admin_id():
    from flask_login import current_user
    return current_user.id
