"""
AUTH feature (Marcus) — a COMPLETE working example for the team to copy.
A "blueprint" is just one feature's bundle of pages (routes).
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..models import User

# This name "auth" is used in links like url_for("auth.login")
auth_bp = Blueprint("auth", __name__, template_folder="templates")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if User.query.filter_by(email=email).first():
            flash("That email is already registered.", "warning")
            return redirect(url_for("auth.register"))

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created - welcome to Sparkle!", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard.home"))
        flash("Wrong email or password. Try again.", "error")

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
    # current_user is whoever is logged in right now.
    return render_template("auth/profile.html", user=current_user)
