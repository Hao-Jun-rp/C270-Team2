"""
listings feature (Hazirah) — starter stub. Build your pages here.
You OWN this folder. You should rarely need to touch anyone else's.
"""
from flask import Blueprint, render_template

listings_bp = Blueprint("listings", __name__, url_prefix="/listings", template_folder="templates")


@listings_bp.route("/")
def index():
    return render_template("listings/index.html")
