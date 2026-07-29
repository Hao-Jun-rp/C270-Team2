"""
MAIN (Marcus / lead) — owns the site entry point.
"/" shows the landing page to visitors, or sends logged-in users to their dashboard.
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from ..models import Service, Review, Booking

main_bp = Blueprint("main", __name__, template_folder="templates")


@main_bp.route("/")
def index():
    # Logged in? You don't need the sales pitch — go to your dashboard.
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    # Everything below is real data from the database — no hardcoded
    # numbers/testimonials. If the demo DB is nearly empty, sections
    # fall back to honest placeholders instead of fake stats.
    services = (Service.query.filter_by(is_active=True)
                .order_by(Service.id).limit(4).all())

    approved = Review.query.filter_by(status="Approved").all()
    avg_rating = round(sum(r.rating for r in approved) / len(approved), 1) if approved else 0.0

    testimonials = (Review.query.filter_by(status="Approved")
                     .order_by(Review.rating.desc(), Review.created_at.desc())
                     .limit(3).all())

    top_service = (Service.query.filter_by(is_active=True)
                    .filter(Service.rating > 0)
                    .order_by(Service.rating.desc()).first())
    top_service_reviews = (Review.query.filter_by(
        service_id=top_service.id, status="Approved").count() if top_service else 0)

    stats = {
        "cleans_delivered": Booking.query.filter_by(status="Completed").count(),
        "avg_rating": avg_rating,
        "review_count": len(approved),
        "active_services": Service.query.filter_by(is_active=True).count(),
    }

    return render_template(
        "main/landing.html",
        services=services,
        testimonials=testimonials,
        stats=stats,
        top_service=top_service,
        top_service_reviews=top_service_reviews,
    )
