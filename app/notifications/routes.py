"""
notifications feature (Hao Jun) — starter stub. Build your pages here.
You OWN this folder. You should rarely need to touch anyone else's.
"""
from flask import Blueprint, render_template

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications", template_folder="templates")


@notifications_bp.route("/")
def index():
    return render_template("notifications/index.html")
