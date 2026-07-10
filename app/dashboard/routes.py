"""
DASHBOARD feature (Tristan)
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
# Replace with booking module integration later
# Pull booking data dynamically from booking module
# --------------------------------------------------

def get_bookings():

    return [

        {
            "id": 1,
            "service": "Deep Clean",
            "date": "15 Jan 2027",
            "status": "Confirmed"
        },

        {
            "id": 2,
            "service": "Standard Clean",
            "date": "22 Jan 2027",
            "status": "Pending"
        },

        {
            "id": 3,
            "service": "Eco Clean",
            "date": "28 Jan 2027",
            "status": "Confirmed"
        }

    ]


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
def home():

    bookings = get_bookings()

    return render_template(
        "dashboard/home.html",
        bookings=bookings
    )


# --------------------------------------------------
# FUTURE INTEGRATION
# Replace get_bookings() with Ashish booking module
# once booking data becomes database-driven
# --------------------------------------------------

"""
Future integration example:

def get_bookings():

    return Booking.query.filter_by(
        user_id=current_user.id
    ).limit(3).all()

"""