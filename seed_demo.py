"""
seed_demo.py — fills the database with a full set of demo data:
5 users, 6 services, 12 bookings, 8 reviews, 9 notifications.
Service ratings are CALCULATED from the approved reviews.

Run once, from the cleaning-app folder, with your venv active:
    python seed_demo.py

It writes to whatever database config.py points at — your local sparkle.db,
or the shared database if DATABASE_URL is set in .env. Safe to re-run: it
skips tables that already have data.

All demo users log in with password:  password123
"""
from datetime import datetime
from app import create_app
from app.extensions import db
from urllib.parse import quote
from app.models import User, Service, Booking, Review, Notification


def d(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


USERS = [
    ("Marcus Tan", "marcus@sparkle.sg"),
    ("Tristan Lee", "tristan@example.com"),
    ("Hazirah Binte", "hazirah@example.com"),
    ("Ashish Kumar", "ashish@example.com"),
    ("Aisha Rahman", "aisha@example.com"),
]

SERVICES = [
    ("Home Cleaning", "Home", "Perfect for apartments, HDBs and regular weekly cleaning.", 45, "2 - 3 Hours", "home cleaning.jpg"),
    ("Deep Cleaning", "Deep Clean", "A complete top-to-bottom cleaning for every room.", 90, "4 - 5 Hours", "deep cleaning.jpg"),
    ("Office Cleaning", "Office", "Keep your office fresh, tidy and productive.", 75, "3 Hours", "office cleaning.jpg"),
    ("Move-Out Cleaning", "Move Out", "Leave your old home sparkling before handing over the keys.", 120, "5 Hours", "moveout cleaning.jpg"),
    ("Eco Cleaning", "Eco", "Environmentally friendly cleaning using eco-safe products.", 60, "2 Hours", "eco cleaning.jpg"),
    ("Kitchen & Bathroom", "Special", "Extra attention to kitchens, toilets and bathrooms.", 55, "2 Hours", "kitchen cleaning.jpg"),
]

# (user_idx, service_idx, date, time, address, notes, status)
BOOKINGS = [
    (1, 0, "2026-06-15", "10:00–11:00", "12 Bishan St 22, #08-114, Singapore", "Focus on the kitchen please.", "Completed"),
    (1, 1, "2026-06-28", "14:00–15:00", "12 Bishan St 22, #08-114, Singapore", "", "Completed"),
    (4, 0, "2026-06-20", "09:00–10:00", "45 Tampines Ave 4, #12-330, Singapore", "Please bring eco-friendly products.", "Completed"),
    (4, 2, "2026-07-02", "13:00–14:00", "One Raffles Place, #22-01, Singapore", "After office hours only.", "Completed"),
    (3, 5, "2026-06-30", "11:00–12:00", "88 Tanjong Pagar Rd, #05-12, Singapore", "", "Completed"),
    (3, 3, "2026-07-25", "08:00–09:00", "88 Tanjong Pagar Rd, #05-12, Singapore", "Moving out, whole unit.", "Pending"),
    (2, 4, "2026-07-20", "15:00–16:00", "30 Clementi Ave 3, #10-45, Singapore", "", "Confirmed"),
    (1, 0, "2026-07-18", "10:00–11:00", "12 Bishan St 22, #08-114, Singapore", "Same as last time.", "Confirmed"),
    (4, 1, "2026-07-22", "14:00–15:00", "45 Tampines Ave 4, #12-330, Singapore", "", "Pending"),
    (2, 2, "2026-06-25", "09:00–10:00", "30 Clementi Ave 3, #10-45, Singapore", "", "Completed"),
    (3, 4, "2026-06-18", "16:00–17:00", "88 Tanjong Pagar Rd, #05-12, Singapore", "Pet-safe products please.", "Completed"),
    (0, 5, "2026-07-01", "11:00–12:00", "5 Woodlands Dr 14, #03-22, Singapore", "", "Completed"),
]

# (user_idx, service_idx, rating, title, description, staff_reply, status)
# NOTE: Aisha (user 4) deliberately has NO review for Home Cleaning (service 0),
# even though her booking of it is Completed (see BOOKINGS below) - this is what
# lets the "Write a review" button and the "leave a review" notification below
# actually have something to demo. Every OTHER completed booking already has a
# matching review, so don't add one here without also adding a fresh unreviewed
# completed booking, or the "write a review" flow won't have anything to show.
REVIEWS = [
    (1, 0, 5, "Spotless!", "Arrived on time and my flat felt brand new afterwards.", None, "Approved"),
    (1, 1, 5, "Worth every cent", "The deep clean was incredibly detailed, every corner done.", "Thanks Tristan, glad you loved it! — Sparkle Team", "Approved"),
    (4, 2, 4, "Office looks great", "Our meeting rooms have never been cleaner.", None, "Approved"),
    (3, 5, 5, "Kitchen sparkles", "Amazing attention to detail in the kitchen and bathrooms.", None, "Approved"),
    (2, 2, 4, "Reliable", "Consistent and professional every single time.", None, "Approved"),
    (3, 4, 4, "Loved the eco products", "Smelled fresh with no harsh chemicals, and pet-safe.", None, "Approved"),
    (0, 5, 4, "Solid job", "Good clean overall, would have liked more time on the grout.", None, "Pending"),
]

# helpers for notification links
def _rev(name, form=False):
    u = "/reviews?service=" + quote(name)
    return u + "#leave-review" if form else u
_BOOK = "/booking/"

# (user_idx, message, is_read, link)
NOTIFICATIONS = [
    (1, "Your Home Cleaning on 18 Jul is confirmed. See you then!", False, _BOOK),
    (1, "Thanks for reviewing Deep Cleaning - your feedback is live.", True, _rev("Deep Cleaning")),
    (4, "Your Deep Cleaning booking on 22 Jul is received and pending confirmation.", False, _BOOK),
    (4, "Your review for Office Cleaning is now published.", True, _rev("Office Cleaning")),
    (3, "Your Move-Out Cleaning booking on 25 Jul is received and pending confirmation.", False, _BOOK),
    (3, "Your review for Kitchen & Bathroom is now published.", True, _rev("Kitchen & Bathroom")),
    (2, "Your Eco Cleaning on 20 Jul is confirmed.", False, _BOOK),
    (0, "Your review for Kitchen & Bathroom is awaiting approval.", False, _rev("Kitchen & Bathroom")),
    (4, "Your Home Cleaning is complete - leave a review to help others!", False, _rev("Home Cleaning", form=True)),
]


def run():
    app = create_app()
    with app.app_context():
        db.create_all()

        if User.query.count() == 0:
            users = []
            for name, email in USERS:
                u = User(name=name, email=email, created_at=d("2026-06-01 09:00:00"))
                u.set_password("password123")
                db.session.add(u)
                users.append(u)
            db.session.commit()
        users = User.query.order_by(User.id).all()

        if Service.query.count() == 0:
            for name, cat, desc, price, dur, img in SERVICES:
                db.session.add(Service(name=name, category=cat, description=desc,
                                       price=price, duration=dur, image=img,
                                       rating=0.0, is_active=True, created_by=users[0].id))
            db.session.commit()
        services = Service.query.order_by(Service.id).all()

        if Booking.query.count() == 0:
            for ui, si, date, time, addr, notes, status in BOOKINGS:
                db.session.add(Booking(user_id=users[ui].id, service_id=services[si].id,
                                       date=date, time=time, address=addr,
                                       notes=notes, status=status))
            db.session.commit()

        if Review.query.count() == 0:
            for ui, si, rating, title, desc, reply, status in REVIEWS:
                db.session.add(Review(user_id=users[ui].id, service_id=services[si].id,
                                      rating=rating, review_title=title,
                                      review_description=desc, staff_reply=reply, status=status))
            db.session.commit()

        # Compute each service's rating from its APPROVED reviews.
        for s in services:
            approved = Review.query.filter_by(service_id=s.id, status="Approved").all()
            s.rating = round(sum(r.rating for r in approved) / len(approved), 1) if approved else 0.0
        db.session.commit()

        if Notification.query.count() == 0:
            for ui, msg, is_read, link in NOTIFICATIONS:
                db.session.add(Notification(user_id=users[ui].id, message=msg, is_read=is_read, link=link))
            db.session.commit()

        print("Demo data ready:",
              User.query.count(), "users,",
              Service.query.count(), "services,",
              Booking.query.count(), "bookings,",
              Review.query.count(), "reviews,",
              Notification.query.count(), "notifications.")
        print("Ratings:", {s.name: s.rating for s in Service.query.all()})


if __name__ == "__main__":
    run()
