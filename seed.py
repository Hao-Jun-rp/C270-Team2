"""
seed.py — puts starter data into the database.

Right now it fills the SERVICE CATALOG (your 6 cleaning services) so the
Services page (and later the Booking page) can read real rows from the
database instead of a hardcoded Python list.

HOW TO RUN — from the cleaning-app folder, with your venv active:
    python seed.py

Safe to run more than once: it skips any service that's already there.
"""
from app import create_app
from app.extensions import db
from app.models import Service

# These are the same 6 services that used to be hardcoded in listings/routes.py.
SERVICES = [
    {"name": "Home Cleaning",      "category": "Home",       "price": 45,  "rating": 4.8,
     "duration": "2 - 3 Hours", "image": "home cleaning.jpg",
     "description": "Perfect for apartments, HDBs and regular weekly cleaning."},

    {"name": "Deep Cleaning",      "category": "Deep Clean", "price": 90,  "rating": 5.0,
     "duration": "4 - 5 Hours", "image": "deep cleaning.jpg",
     "description": "A complete top-to-bottom cleaning for every room."},

    {"name": "Office Cleaning",    "category": "Office",     "price": 75,  "rating": 4.7,
     "duration": "3 Hours",     "image": "office cleaning.jpg",
     "description": "Keep your office fresh, tidy and productive."},

    {"name": "Move-Out Cleaning",  "category": "Move Out",   "price": 120, "rating": 4.9,
     "duration": "5 Hours",     "image": "moveout cleaning.jpg",
     "description": "Leave your old home sparkling before handing over the keys."},

    {"name": "Eco Cleaning",       "category": "Eco",        "price": 60,  "rating": 4.8,
     "duration": "2 Hours",     "image": "eco cleaning.jpg",
     "description": "Environmentally friendly cleaning using eco-safe products."},

    {"name": "Kitchen & Bathroom", "category": "Special",    "price": 55,  "rating": 4.9,
     "duration": "2 Hours",     "image": "kitchen cleaning.jpg",
     "description": "Extra attention to kitchens, toilets and bathrooms."},
]


def run():
    app = create_app()
    with app.app_context():
        db.create_all()  # make sure the tables exist before we add rows

        added = 0
        for row in SERVICES:
            # Skip a service that's already in the table (so re-running is safe).
            if Service.query.filter_by(name=row["name"]).first():
                continue
            db.session.add(Service(**row))
            added += 1

        db.session.commit()  # save the changes to the database file
        print(f"Seed complete. Added {added} new service(s). "
              f"Total services now: {Service.query.count()}.")


if __name__ == "__main__":
    run()
