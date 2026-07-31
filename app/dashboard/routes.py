"""
=========================================================
Dashboard Routes  (Tristan)

Routes stay lightweight: they pull everything from the service layer
and render. Business logic lives in services.py; the data now comes
from the real database via mock_data.py (renamed in spirit to the
"data layer" — see that file's header).
=========================================================
"""
from flask import Blueprint, render_template, request
from flask_login import login_required

from .services import get_dashboard_data

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/dashboard/static",
)


# =========================================================
# Dashboard Home
# =========================================================
@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def home():
    # Which cleaning tip to show first (?tip=0, ?tip=1, ...).
    current_tip = request.args.get("tip", default=0, type=int)

    # All dashboard data (bookings, summary, calendar, tips, ...) comes
    # from the service layer, scoped to the logged-in user.
    dashboard_data = get_dashboard_data(current_tip)

    return render_template("dashboard/home.html", **dashboard_data)
