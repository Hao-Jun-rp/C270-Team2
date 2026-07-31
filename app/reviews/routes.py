from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Review, Service, Booking

def stars(rating):
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        rating = 0

    rating = max(0, min(5, rating))
    return "★" * rating + "☆" * (5 - rating)


def reviewable_services_for(user):
    if not user.is_authenticated:
        return []

    completed_bookings = Booking.query.filter_by(
        user_id=user.id,
        status="Completed"
    ).all()

    service_ids = {
        booking.service_id
        for booking in completed_bookings
        if booking.service_id is not None
    }

    reviewed_service_ids = {
        review.service_id
        for review in Review.query.filter_by(user_id=user.id).all()
        if review.service_id is not None
    }

    available_service_ids = service_ids - reviewed_service_ids

    if not available_service_ids:
        return []

    return Service.query.filter(
        Service.id.in_(available_service_ids)
    ).all()


reviews_bp = Blueprint(
    "reviews",
    __name__,
    url_prefix="/reviews",
    template_folder="templates"
)

review_list = [
    {"name": "John", "stars": 5, "text": "Excellent service!"},
    {"name": "Sarah", "stars": 4, "text": "Friendly and professional staff."},
    {"name": "Daniel", "stars": 5, "text": "Highly recommended!"}
]


@reviews_bp.route("/")
def index():
    query = Review.query.filter_by(status="Approved")

    # Optional filter: /reviews?service_id=1  (preferred) or ?service=Home Cleaning
    heading_service = None
    service_id = request.args.get("service_id", type=int)
    service_name = request.args.get("service")
    if service_id:
        heading_service = Service.query.get(service_id)
    elif service_name:
        heading_service = Service.query.filter_by(name=service_name).first()
    if heading_service:
        query = query.filter_by(service_id=heading_service.id)

    reviews = query.order_by(Review.created_at.desc()).all()
    avg = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0.0

    # Dropdown only offers services the user can actually review right now
    # (a completed booking they haven't reviewed yet).
    services = reviewable_services_for(current_user)

    # The logged-in user's OWN reviews that aren't Approved yet (Pending/Hidden).
    # These are deliberately excluded from the public `reviews` list above, so
    # without this a customer who just submitted a review sees nothing and
    # can't tell whether it actually saved. Show it to them, clearly labeled.
    my_pending = []
    if current_user.is_authenticated:
        mine = (Review.query.filter_by(user_id=current_user.id)
                .filter(Review.status != "Approved"))
        if heading_service:
            mine = mine.filter_by(service_id=heading_service.id)
        my_pending = mine.order_by(Review.created_at.desc()).all()

    return render_template("reviews/index.html",
                           reviews=reviews, avg=avg, count=len(reviews),
                           services=services, heading_service=heading_service,
                           my_pending=my_pending, stars=stars)


@reviews_bp.route("/submit", methods=["POST"])
@login_required
def submit():
    service_id = request.form.get("service_id", type=int)
    rating = request.form.get("rating", type=int)
    title = (request.form.get("review_title") or "").strip()
    text = (request.form.get("review") or "").strip()
    service = Service.query.get(service_id) if service_id else None

    if not service or not rating or rating < 1 or rating > 5 or not text:
        flash("Please choose a service, a star rating, and write a short review.", "error")
        return redirect(url_for("reviews.index"))

    # Verified-purchase rule: you can only review a service you've had
    # COMPLETED. (Blocks reviewing services you never actually used.)
    has_completed = Booking.query.filter_by(
        user_id=current_user.id, service_id=service.id, status="Completed").first()
    if not has_completed:
        flash("You can only review a service after a completed booking.", "error")
        return redirect(url_for("reviews.index"))

    already = Review.query.filter_by(user_id=current_user.id, service_id=service.id).first()
    if already:
        flash(f"You've already reviewed {service.name}.", "error")
        return redirect(url_for("reviews.index", service=service.name))

    db.session.add(Review(
        user_id=current_user.id, service_id=service.id,
        rating=rating, review_title=(title or None),
        review_description=text, status="Pending",
    ))
    db.session.commit()

    # Let the customer know it's in, with a link back to that service's reviews.
    from ..notifications.routes import create_notification
    create_notification(
        current_user.id,
        f"Thanks! Your review for {service.name} is awaiting approval.",
        link=url_for("reviews.index", service=service.name),
    )

    flash("Thanks for your review! It will appear once it's approved.", "success")
    return redirect(url_for("reviews.index", service=service.name))
