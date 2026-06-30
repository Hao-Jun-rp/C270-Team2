"""
reviews feature (Matthew) — starter stub. Build your pages here.
You OWN this folder. You should rarely need to touch anyone else's.
"""
from flask import Blueprint, render_template

reviews_bp = Blueprint("reviews", __name__, url_prefix="/reviews", template_folder="templates")


@reviews_bp.route("/")
def index():
    return render_template("reviews/index.html")
