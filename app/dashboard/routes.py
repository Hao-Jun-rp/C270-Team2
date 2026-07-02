"""
DASHBOARD feature (Tristan)
Handles:
- Dashboard homepage
- Booking list page
- Individual booking detail page

Temporary mock data used for development.
Waiting future integration with booking module.
"""

from flask import Blueprint, render_template

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    template_folder="templates"
)


# --------------------------------------------------
# TEMPORARY MOCK DATA
# TODO:
# Replace this function with booking module integration
# when booking system is completed.
# --------------------------------------------------

def get_bookings():

    return [

        {
            "id": 1,
            "service": "Home Cleaning",
            "date": "1 July 2026",
            "status": "Pending",
            "address": "123 Example Street",
            "notes": "Focus on kitchen"
        },

        {
            "id": 2,
            "service": "Deep Cleaning",
            "date": "5 July 2026",
            "status": "Confirmed",
            "address": "456 Sample Avenue",
            "notes": "Full apartment cleaning"
        },

        {
            "id": 3,
            "service": "Office Cleaning",
            "date": "10 July 2026",
            "status": "Completed",
            "address": "789 Business Road",
            "notes": "Clean meeting room"
        }

    ]

# Dashboard homepage
@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
def home():

    bookings = get_bookings()
    pending_count = 0
    confirmed_count = 0
    completed_count = 0

    for booking in bookings:

        if booking["status"] == "Pending":
            pending_count += 1

        elif booking["status"] == "Confirmed":
            confirmed_count += 1

        elif booking["status"] == "Completed":
            completed_count += 1

    return render_template(
    "dashboard/home.html",
    bookings=bookings,
    pending_count=pending_count,
    confirmed_count=confirmed_count,
    completed_count=completed_count
    )



# All bookings page

@dashboard_bp.route("/bookings")
def bookings_page():

    bookings = get_bookings()

    return render_template(
        "dashboard/bookings.html",
        bookings=bookings
    )


# Individual booking detail page

@dashboard_bp.route("/bookings/<int:booking_id>")
def booking_detail(booking_id):

    selected_booking = None
    bookings = get_bookings()

    for booking in bookings:
        if booking["id"] == booking_id:
            selected_booking = booking
            break

    return render_template(
        "dashboard/booking_detail.html",
        booking=selected_booking
    )


# --------------------------------------------------
# FUTURE INTEGRATION EXAMPLE
# DO NOT ENABLE YET
# Replace get_bookings() with booking module later
# --------------------------------------------------

"""
Example future integration:

def get_bookings():

    return Booking.query.filter_by(
        user_id=current_user.id
    ).all()

"""