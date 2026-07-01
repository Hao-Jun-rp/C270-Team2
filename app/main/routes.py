"""
MAIN (Marcus / lead) — owns the site entry point.
"/" shows the landing page to visitors, or sends logged-in users to their dashboard.
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

main_bp = Blueprint("main", __name__, template_folder="templates")


@main_bp.route("/")
def index():
    # Logged in? You don't need the sales pitch — go to your dashboard.
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))
    return render_template("main/landing.html")
