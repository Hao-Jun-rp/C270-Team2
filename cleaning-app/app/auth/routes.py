"""
AUTH feature (Marcus) — the finished version.
Handles: register, login, logout, view profile, edit profile, change password.
This is also the worked example the rest of the team copies.
"""
import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..models import User

auth_bp = Blueprint("auth", __name__, template_folder="templates")

# A simple pattern to sanity-check an email looks like "something@something.something"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    # Already logged in? No need to register again.
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        # ---- Checks (stop at the first problem) ----
        if not name or not email or not password:
            flash("Please fill in every field.", "error")
        elif len(name) > 80:
            flash("Name is too long (max 80 characters).", "error")
        elif not EMAIL_RE.match(email):
            flash("Please enter a valid email address.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif password != confirm:
            flash("Those passwords don't match.", "error")
        elif User.query.filter_by(email=email).first():
            flash("That email is already registered.", "warning")
        else:
            # All good — create and save the user.
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)  # sign them in straight away
            flash("Welcome to Sparkle!", "success")
            return redirect(url_for("dashboard.home"))

        # A check failed: show the form again, keeping what they typed.
        return render_template("auth/register.html", name=name, email=email)

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard.home"))

        # Same message whether the email or password was wrong (safer).
        flash("Wrong email or password. Try again.", "error")
        return render_template("auth/login.html", email=email)

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been signed out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile")
@login_required
def profile():
    return render_template("auth/profile.html", user=current_user)


@auth_bp.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not name or not email:
        flash("Name and email can't be empty.", "error")
    elif not EMAIL_RE.match(email):
        flash("Please enter a valid email address.", "error")
    else:
        # Make sure the new email isn't already used by a DIFFERENT person.
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != current_user.id:
            flash("That email is already in use.", "warning")
        else:
            current_user.name = name
            current_user.email = email
            db.session.commit()
            flash("Profile updated.", "success")

    return redirect(url_for("auth.profile"))


@auth_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    current = request.form.get("current", "")
    new = request.form.get("new", "")
    confirm = request.form.get("confirm", "")

    if not current_user.check_password(current):
        flash("Your current password is wrong.", "error")
    elif len(new) < 6:
        flash("New password must be at least 6 characters.", "error")
    elif new != confirm:
        flash("New passwords don't match.", "error")
    else:
        current_user.set_password(new)
        db.session.commit()
        flash("Password changed.", "success")

    return redirect(url_for("auth.profile"))
