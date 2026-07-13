from flask import Blueprint, render_template, request, redirect, url_for

reviews_bp = Blueprint("reviews", __name__)

review_list = [
    {"name": "John", "stars": 5, "text": "Excellent service!"},
    {"name": "Sarah", "stars": 4, "text": "Friendly and professional staff."},
    {"name": "Daniel", "stars": 5, "text": "Highly recommended!"}
]


@reviews_bp.route("/")
def index():
    review_count = len(review_list)

    if review_count > 0:
        average_rating = sum(
            review["stars"] for review in review_list
        ) / review_count
    else:
        average_rating = 0

    return render_template(
        "reviews/index.html",
        reviews=review_list,
        average_rating=average_rating,
        review_count=review_count
    )


@reviews_bp.route("/submit", methods=["POST"])
def submit():
    rating = request.form.get("rating", type=int)
    review_text = request.form.get("review", "").strip()

    if rating is None or rating < 1 or rating > 5:
        return redirect(url_for("reviews.index"))

    if not review_text:
        return redirect(url_for("reviews.index"))

    review_list.insert(0, {
        "name": "Anonymous",
        "stars": rating,
        "text": review_text
    })

    return redirect(url_for("reviews.index"))