"""
LISTINGS (Hazirah) — the Services page.

CHANGED: this page now reads services from the DATABASE (the Service table)
instead of a hardcoded Python list. Run  python seed.py  once to fill the
table. The template did not need to change — the field names are the same.
"""
from flask import render_template
from . import listings_bp
from ..models import Service, Review
from ..reviews.routes import stars


@listings_bp.route("/listings")
def index():
    # Only show services that are switched on (is_active = True).
    services = Service.query.filter_by(is_active=True).order_by(Service.id).all()

    # Build the category filter buttons from whatever services exist.
    categories = ["All"] + sorted({s.category for s in services})

    # Approved review count per service, for "no reviews yet" vs a real star rating.
    review_counts = {
        s.id: Review.query.filter_by(service_id=s.id, status="Approved").count()
        for s in services
    }

    return render_template(
        "listings/index.html",
        services=services,
        categories=categories,
        review_counts=review_counts,
        stars=stars,
    )
