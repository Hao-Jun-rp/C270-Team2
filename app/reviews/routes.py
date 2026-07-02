from flask import Blueprint, render_template, request, redirect, url_for

reviews_bp = Blueprint("reviews", __name__, url_prefix="/reviews", template_folder="templates")

reviews_list = [
    {"name": "Marcus", "stars": "★★★★★", "text": "The cleaner arrived on time and my home felt brand-new after the session."},
    {"name": "Tristan", "stars": "★★★★★", "text": "Very smooth booking process. Reliable, friendly, and easy to use."},
    {"name": "Hazirah", "stars": "★★★★☆", "text": "The deep clean was great. I liked how simple everything was."}
]

@reviews_bp.route("/")
def index():
    return render_template("reviews/index.html", reviews=reviews_list)

@reviews_bp.route("/submit", methods=["POST"])
def submit():
    rating = int(request.form.get("rating"))
    review = request.form.get("review")

    reviews_list.append({
        "name": "You",
        "stars": "★" * rating + "☆" * (5 - rating),
        "text": review
    })

    return redirect(url_for("reviews.index"))