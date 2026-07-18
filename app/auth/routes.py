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


# ---------------------------------------------------------------------------
# FORGOT / RESET PASSWORD (demo-friendly, no email server needed)
#
# Real systems email the user a signed, time-limited reset link. We use the
# exact same mechanism (itsdangerous, which Flask itself uses for sessions)
# but DISPLAY the link on screen instead of emailing it, so the demo never
# depends on an SMTP server. In production, the render_template call in
# forgot_password() would be replaced by send_email(user.email, reset_link).
# ---------------------------------------------------------------------------
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

RESET_TOKEN_MAX_AGE = 30 * 60   # links die after 30 minutes


def _reset_serializer():
    """A serializer that signs tokens with the app's SECRET_KEY, so a token
    can't be forged or tampered with. The 'salt' namespaces these tokens so
    they can never be confused with any other signed value in the app."""
    from flask import current_app
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"],
                                  salt="sparkle-password-reset")


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    # Logged-in users have the normal "change password" page in their profile.
    if current_user.is_authenticated:
        return redirect(url_for("auth.profile"))

    reset_link = None
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            # NOTE: a production app would show the same vague message either
            # way (so attackers can't probe which emails exist). We show the
            # honest error to keep the demo easy to follow.
            flash("No account found with that email.", "error")
        else:
            token = _reset_serializer().dumps({"uid": user.id})
            reset_link = url_for("auth.reset_password", token=token,
                                 _external=True)
            flash("Reset link generated - it works for 30 minutes.", "success")
    return render_template("auth/forgot.html", reset_link=reset_link,
                           email=email)


@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    # 1) The token must be genuine (signed by US) and younger than 30 min.
    try:
        data = _reset_serializer().loads(token, max_age=RESET_TOKEN_MAX_AGE)
    except SignatureExpired:
        flash("That reset link has expired - request a new one below.", "error")
        return redirect(url_for("auth.forgot_password"))
    except BadSignature:
        flash("That reset link is invalid - request a new one below.", "error")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.get(data.get("uid"))
    if not user:
        flash("That account no longer exists.", "error")
        return redirect(url_for("auth.forgot_password"))

    # 2) Same password rules as registration.
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            user.set_password(password)   # re-hashed with Werkzeug, as always
            db.session.commit()
            flash("Password updated! You can log in with it now.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/reset.html", token=token, user=user)
