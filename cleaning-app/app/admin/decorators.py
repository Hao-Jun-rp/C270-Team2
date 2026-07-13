"""
@admin_required — the gate that protects every /admin page.

Logic (checked on every request to a decorated view):
  1. Not logged in?        -> send to the login page (Flask-Login handles it),
                              remembering where they were going.
  2. Logged in, NOT admin? -> refuse: flash a message and send them back to
                              their normal dashboard. (No scary error page.)
  3. Logged in AND admin?  -> allow the view to run.

Put @admin_required BELOW @login-style behaviour is unnecessary here because
this decorator already covers the "not logged in" case itself.
"""
from functools import wraps

from flask import redirect, url_for, flash, request
from flask_login import current_user


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            # Bounce to login, then come back here after a successful login.
            return redirect(url_for("auth.login", next=request.path))
        if not current_user.is_admin:
            flash("That area is for staff only.", "error")
            return redirect(url_for("dashboard.home"))
        return view(*args, **kwargs)
    return wrapped
