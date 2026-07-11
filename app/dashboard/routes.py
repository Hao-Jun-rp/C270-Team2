"""
=========================================================
Dashboard Routes

Dashboard Feature (Tristan)

Routes should remain lightweight.

Business logic belongs inside services.py.

Mock data belongs inside mock_data.py.

=========================================================
"""

from flask import Blueprint, render_template, request

from .services import get_dashboard_data

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/dashboard/static"
)


# =========================================================
# Dashboard Home
# =========================================================

@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
def home():

    # -----------------------------------------------------
    # Cleaning Tip Navigation
    #
    # Current implementation uses a query parameter:
    #   /dashboard?tip=0
    #   /dashboard?tip=1
    #
    # Future:
    # Replace with JavaScript carousel if desired.
    # -----------------------------------------------------

    current_tip = request.args.get(
        "tip",
        default=0,
        type=int
    )

    # -----------------------------------------------------
    # Get ALL dashboard data from the service layer.
    #
    # IMPORTANT:
    # Routes should NOT contain business logic.
    # Future developers should update services.py instead.
    # -----------------------------------------------------

    dashboard_data = get_dashboard_data(current_tip)

    # -----------------------------------------------------
    # Render Dashboard
    # -----------------------------------------------------

    return render_template(

        "dashboard/home.html",

        **dashboard_data

    )