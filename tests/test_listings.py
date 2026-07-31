"""
Tests for the Listings feature (Hazirah).

Run all tests:          pytest
Run just this file:     pytest tests/test_listings.py -v
"""
from app.extensions import db
from app.models import Service, Review


def make_service(**overrides):
    """Helper: build a Service with sensible defaults, override what you need."""
    defaults = dict(
        name="Home Cleaning",
        category="Home",
        description="A basic home clean.",
        price=45.0,
        duration="2 - 3 Hours",
        image="home cleaning.jpg",
        is_active=True,
    )
    defaults.update(overrides)
    service = Service(**defaults)
    db.session.add(service)
    db.session.commit()
    return service


def test_listings_page_loads(client):
    """The /listings page should load successfully, even with no services yet."""
    response = client.get("/listings")
    assert response.status_code == 200


def test_active_service_appears_on_page(app, client):
    """A service with is_active=True should show up on the listings page."""
    with app.app_context():
        make_service(name="Deep Cleaning")

    response = client.get("/listings")
    assert response.status_code == 200
    assert b"Deep Cleaning" in response.data


def test_inactive_service_is_hidden(app, client):
    """A deactivated service (is_active=False) should NOT show up on the page."""
    with app.app_context():
        make_service(name="Retired Service", is_active=False)

    response = client.get("/listings")
    assert b"Retired Service" not in response.data


def test_service_category_appears_as_a_tab(app, client):
    """A service's category (e.g. 'Office') should be one of the fixed
    tabs shown on the page."""
    with app.app_context():
        make_service(name="Office Cleaning", category="Office")

    response = client.get("/listings")
    assert b"Office" in response.data


def test_service_with_no_reviews_shows_zero_count(app, client):
    """A brand-new service with no reviews should still render without crashing,
    and should be treated as having 0 approved reviews."""
    with app.app_context():
        service = make_service(name="Brand New Service")
        approved_count = Review.query.filter_by(
            service_id=service.id, status="Approved"
        ).count()
        assert approved_count == 0

    response = client.get("/listings")
    assert response.status_code == 200
    assert b"Brand New Service" in response.data


def test_multiple_categories_all_appear(app, client):
    """The fixed category tabs (Home, Office, Deep Clean, Move Out, Eco,
    Special) should always show up, regardless of which services exist —
    this prevents admin typos (e.g. 'home' vs 'Home') from creating
    duplicate, confusing tabs."""
    response = client.get("/listings")
    for category in [b"Home", b"Office", b"Deep Clean", b"Move Out", b"Eco", b"Special"]:
        assert category in response.data


def test_category_tabs_are_fixed_not_derived_from_services(app, client):
    """Even with zero services in the database, all category tabs should
    still appear (since they come from a fixed list, not from scanning
    existing services)."""
    response = client.get("/listings")
    assert b"Home" in response.data
    assert b"All" in response.data


def test_only_approved_reviews_count_towards_review_count(app, client):
    """A Pending or Hidden review should NOT be counted as an approved
    review — only reviews with status='Approved' should be included."""
    with app.app_context():
        service = make_service(name="Mixed Reviews Service")
        db.session.add(Review(
            service_id=service.id, user_id=1, rating=5,
            review_description="Great!", status="Approved"
        ))
        db.session.add(Review(
            service_id=service.id, user_id=1, rating=1,
            review_description="Awaiting moderation", status="Pending"
        ))
        db.session.commit()

        approved_count = Review.query.filter_by(
            service_id=service.id, status="Approved"
        ).count()
        assert approved_count == 1


def test_display_id_is_formatted_correctly(app):
    """Service.display_id should format the raw integer id as e.g. 'S001',
    used anywhere the app shows a human-friendly service code."""
    with app.app_context():
        service = make_service(name="Formatted ID Service")
        assert service.display_id == f"S{service.id:03d}"
        assert service.display_id.startswith("S")


def test_new_service_defaults(app):
    """Sanity check on model defaults: a Service created without explicitly
    setting rating/is_active should default to rating=0.0 and is_active=True."""
    with app.app_context():
        service = Service(
            name="Default Check",
            category="Home",
            description="Testing defaults.",
            price=50.0,
            duration="1 Hour",
        )
        db.session.add(service)
        db.session.commit()

        assert service.is_active is True
        assert service.rating == 0.0
