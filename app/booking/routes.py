from flask import Blueprint, render_template
from flask_login import login_required, current_user

booking_bp = Blueprint("booking", __name__, template_folder="templates", url_prefix="/booking")

MOCK_BOOKINGS = [
    {
        "id": 1,
        "service": "Deep Clean",
        "date": "2027-01-15",
        "time": "10:00–11:00",
        "status": "Confirmed",
        "address": "12 Orchard Road, Singapore",
        "notes": "Please bring eco products."
    },
    {
        "id": 2,
        "service": "Standard Clean",
        "date": "2027-01-22",
        "time": "14:00–15:00",
        "status": "Pending",
        "address": "88 Tanjong Pagar, Singapore",
        "notes": ""
    }
]

@booking_bp.route("/")
@login_required
def index():
    return render_template("booking/index.html", bookings=MOCK_BOOKINGS)

@booking_bp.route("/add")
@login_required
def add_booking():
    return render_template("booking/addbooking.html")
