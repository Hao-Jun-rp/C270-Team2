"""
LISTINGS (Hazirah) — the Services page.

CHANGED: this page now reads services from the DATABASE (the Service table)
instead of a hardcoded Python list. Run  python seed_demo.py  once to fill the
table. The template did not need to change — the field names are the same.

CHANGED (per lecturer feedback): categories are now a FIXED list instead of
being generated from whatever's in the database. Previously, if an admin
typed "home" in one service and "Home" in another, they'd show up as two
separate, confusing tabs. Now the admin picks from this same fixed list via
a dropdown (see admin/routes.py), so tabs are always consistent.
"""
from flask import render_template
from . import listings_bp
from ..models import Service, Review
from ..reviews.routes import stars
from ..constants import CATEGORIES


@listings_bp.route("/listings")
def index():
    # Only show services that are switched on (is_active = True).
    services = Service.query.filter_by(is_active=True).order_by(Service.id).all()

    # Fixed category tabs — always the same set, regardless of what's
    # currently in the database.
    categories = ["All"] + CATEGORIES

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
