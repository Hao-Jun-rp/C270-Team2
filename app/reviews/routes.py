"""
REVIEWS (Matthew) — connected to the database.

- The page shows APPROVED reviews (pulled from the review table).
- A logged-in customer can leave a review for a service; it's saved with
  status "Pending" so it can be approved later (admin step, future).
- The listings "View Reviews" button links here with ?service=<name>.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Review, Service

reviews_bp = Blueprint("reviews", __name__, url_prefix="/reviews", template_folder="templates")


def stars(n):
    n = int(n or 0)
    return "\u2605" * n + "\u2606" * (5 - n)


@reviews_bp.route("/")
def index():
    query = Review.query.filter_by(status="Approved")

    # Optional filter: /reviews?service=Home Cleaning
    heading_service = None
    service_name = request.args.get("service")
    if service_name:
        svc = Service.query.filter_by(name=service_name).first()
        if svc:
            heading_service = svc
            query = query.filter_by(service_id=svc.id)

    reviews = query.order_by(Review.created_at.desc()).all()
    avg = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0.0
    services = Service.query.filter_by(is_active=True).order_by(Service.name).all()

    return render_template("reviews/index.html",
                           reviews=reviews, avg=avg, count=len(reviews),
                           services=services, heading_service=heading_service,
                           stars=stars)


@reviews_bp.route("/submit", methods=["POST"])
@login_required
def submit():
    service_id = request.form.get("service_id", type=int)
    rating = request.form.get("rating", type=int)
    text = (request.form.get("review") or "").strip()
    service = Service.query.get(service_id) if service_id else None

    if not service or not rating or rating < 1 or rating > 5 or not text:
        flash("Please choose a service, a star rating, and write a short review.", "error")
        return redirect(url_for("reviews.index"))

    db.session.add(Review(
        user_id=current_user.id, service_id=service.id,
        rating=rating, review_description=text, status="Pending",
    ))
    db.session.commit()
    flash("Thanks for your review! It will appear once it's approved.", "success")
    return redirect(url_for("reviews.index", service=service.name))
