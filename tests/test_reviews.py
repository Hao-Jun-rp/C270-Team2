"""
Tests for the Reviews feature (Matthew).

Three groups:
  1. Visibility        — only Approved reviews are public; a service's own
                         average is calculated from Approved reviews only.
  2. Verified purchase  — you can only review a service you've had a
                         COMPLETED booking for.
  3. Submission rules   — one review per service per person; bad input is
                         rejected.

Run all tests:       pytest
Run just this file:  pytest tests/test_reviews.py -v
"""
from datetime import date, timedelta

from app.extensions import db
from app.models import User, Service, Booking, Review
from app.reviews.routes import stars, reviewable_services_for


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def make_user(email, role="customer", password="password123"):
    user = User(name="Test Person", email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def make_service(name="Deep Cleaning"):
    service = Service(name=name, category="Home", description="A deep clean.",
                      price=120.0, duration="3 - 4 Hours", is_active=True)
    db.session.add(service)
    db.session.commit()
    return service


def make_booking(user, service, status="Completed"):
    booking = Booking(user_id=user.id, service_id=service.id,
                      date=date.today() - timedelta(days=1),
                      time="09:00–12:00", address="1 Test Road",
                      status=status, payment_method="Cash",
                      payment_status="Paid (cash on completion)")
    db.session.add(booking)
    db.session.commit()
    return booking


def make_review(user, service, rating=5, status="Approved"):
    review = Review(user_id=user.id, service_id=service.id, rating=rating,
                    review_description="Nice clean.", status=status)
    db.session.add(review)
    db.session.commit()
    return review


def login(client, email, password="password123"):
    return client.post("/login", data={"email": email, "password": password})


# ===============================================================
# 1. Visibility — only Approved reviews are public
# ===============================================================
def test_stars_renders_the_right_number_of_filled_stars():
    assert stars(3) == "★★★☆☆"
    assert stars(5) == "★★★★★"
    assert stars(0) == "☆☆☆☆☆"


def test_pending_review_is_not_shown_on_the_public_page(app, client):
    with app.app_context():
        author = make_user("author@example.com")
        service = make_service()
        make_review(author, service, status="Pending")

    response = client.get("/reviews/")
    assert b"Nice clean." not in response.data


def test_approved_review_is_shown_on_the_public_page(app, client):
    with app.app_context():
        author = make_user("author@example.com")
        service = make_service()
        make_review(author, service, status="Approved")

    response = client.get("/reviews/")
    assert b"Nice clean." in response.data


def test_own_pending_review_is_visible_to_its_author(app, client):
    """A customer who just submitted a review should see it, clearly
    marked as not-yet-approved — otherwise it looks like it vanished."""
    with app.app_context():
        make_user("author@example.com")
        service = make_service()
        author = User.query.filter_by(email="author@example.com").first()
        make_review(author, service, status="Pending")

    login(client, "author@example.com")
    response = client.get("/reviews/")
    assert b"Nice clean." in response.data


# ===============================================================
# 2. Verified purchase rule
# ===============================================================
def test_service_with_no_completed_booking_is_not_reviewable(app, client):
    with app.app_context():
        user = make_user("customer@example.com")
        service = make_service()
        # No booking at all for this service.
        reviewable = reviewable_services_for(user)
        assert service not in reviewable


def test_service_with_a_completed_booking_is_reviewable(app, client):
    with app.app_context():
        user = make_user("customer@example.com")
        service = make_service()
        make_booking(user, service, status="Completed")
        reviewable = reviewable_services_for(user)
        assert service in reviewable


def test_pending_booking_does_not_make_a_service_reviewable(app, client):
    """You shouldn't be able to review a service before the job is
    actually done."""
    with app.app_context():
        user = make_user("customer@example.com")
        service = make_service()
        make_booking(user, service, status="Pending")
        reviewable = reviewable_services_for(user)
        assert service not in reviewable


def test_submitting_a_review_without_a_completed_booking_is_rejected(app, client):
    with app.app_context():
        make_user("customer@example.com")
        service = make_service()
        service_id = service.id
    login(client, "customer@example.com")

    client.post("/reviews/submit", data={
        "service_id": service_id, "rating": 5,
        "review_title": "Great", "review": "Loved it!",
    }, follow_redirects=True)

    with app.app_context():
        assert Review.query.filter_by(service_id=service_id).first() is None


# ===============================================================
# 3. Submission rules
# ===============================================================
def test_customer_can_submit_a_review_after_a_completed_booking(app, client):
    with app.app_context():
        user = make_user("customer@example.com")
        service = make_service()
        make_booking(user, service, status="Completed")
        service_id = service.id
    login(client, "customer@example.com")

    client.post("/reviews/submit", data={
        "service_id": service_id, "rating": 4,
        "review_title": "Good job", "review": "Would book again.",
    }, follow_redirects=True)

    with app.app_context():
        review = Review.query.filter_by(service_id=service_id).first()
        assert review is not None
        assert review.status == "Pending"
        assert review.rating == 4


def test_cannot_review_the_same_service_twice(app, client):
    with app.app_context():
        user = make_user("customer@example.com")
        service = make_service()
        make_booking(user, service, status="Completed")
        make_review(user, service, status="Approved")
        service_id = service.id
    login(client, "customer@example.com")

    client.post("/reviews/submit", data={
        "service_id": service_id, "rating": 2,
        "review_title": "Again", "review": "Trying to review twice.",
    }, follow_redirects=True)

    with app.app_context():
        reviews = Review.query.filter_by(service_id=service_id).all()
        assert len(reviews) == 1
        assert reviews[0].rating == 5  # original review is unchanged


def test_review_without_a_rating_is_rejected(app, client):
    with app.app_context():
        user = make_user("customer@example.com")
        service = make_service()
        make_booking(user, service, status="Completed")
        service_id = service.id
    login(client, "customer@example.com")

    client.post("/reviews/submit", data={
        "service_id": service_id, "review_title": "No stars",
        "review": "Forgot to pick a rating.",
    }, follow_redirects=True)

    with app.app_context():
        assert Review.query.filter_by(service_id=service_id).first() is None


def test_review_with_empty_text_is_rejected(app, client):
    with app.app_context():
        user = make_user("customer@example.com")
        service = make_service()
        make_booking(user, service, status="Completed")
        service_id = service.id
    login(client, "customer@example.com")

    client.post("/reviews/submit", data={
        "service_id": service_id, "rating": 5, "review_title": "Empty",
        "review": "",
    }, follow_redirects=True)

    with app.app_context():
        assert Review.query.filter_by(service_id=service_id).first() is None
