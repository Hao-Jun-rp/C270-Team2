"""
booking feature (Ashish) — starter stub. Build your pages here.
You OWN this folder. You should rarely need to touch anyone else's.
"""
from flask import Blueprint, render_template

booking_bp = Blueprint("booking", __name__, url_prefix="/booking", template_folder="templates")


@booking_bp.route("/")
def index():
    return render_template("booking/index.html")
