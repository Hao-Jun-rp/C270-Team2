"""
DASHBOARD feature (Tristan) — starter stub. This is the app's landing page.
You OWN this folder.
"""
from flask import Blueprint, render_template

dashboard_bp = Blueprint("dashboard", __name__, template_folder="templates")


@dashboard_bp.route("/")
def home():
    return render_template("dashboard/home.html")
