from flask import render_template
from . import listings_bp


@listings_bp.route("/listings")
def index():

    services = [
        {
            "id": 1,
            "name": "Home Cleaning",
            "image": "home cleaning.jpg",
            "category": "Home",
            "price": 45,
            "rating": 4.8,
            "duration": "2 - 3 Hours",
            "description": "Perfect for apartments, HDBs and regular weekly cleaning."
        },
        {
            "id": 2,
            "name": "Deep Cleaning",
            "image": "deep cleaning.jpg",
            "category": "Deep Clean",
            "price": 90,
            "rating": 5.0,
            "duration": "4 - 5 Hours",
            "description": "A complete top-to-bottom cleaning for every room."
        },
        {
            "id": 3,
            "name": "Office Cleaning",
            "image": "office cleaning.jpg",
            "category": "Office",
            "price": 75,
            "rating": 4.7,
            "duration": "3 Hours",
            "description": "Keep your office fresh, tidy and productive."
        },
        {
            "id": 4,
            "name": "Move-Out Cleaning",
            "image": "moveout cleaning.jpg",
            "category": "Move Out",
            "price": 120,
            "rating": 4.9,
            "duration": "5 Hours",
            "description": "Leave your old home sparkling before handing over the keys."
        },
        {
            "id": 5,
            "name": "Eco Cleaning",
            "image": "eco cleaning.jpg",
            "category": "Eco",
            "price": 60,
            "rating": 4.8,
            "duration": "2 Hours",
            "description": "Environmentally friendly cleaning using eco-safe products."
        },
        {
            "id": 6,
            "name": "Kitchen & Bathroom",
            "image": "kitchen cleaning.jpg",
            "category": "Special",
            "price": 55,
            "rating": 4.9,
            "duration": "2 Hours",
            "description": "Extra attention to kitchens, toilets and bathrooms."
        }
    ]

    categories = [
        "All",
        "Home",
        "Office",
        "Deep Clean",
        "Move Out",
        "Eco"
    ]

    return render_template(
        "listings/index.html",
        services=services,
        categories=categories
    )
