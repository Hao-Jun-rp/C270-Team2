"""
=========================================================
Dashboard Data Layer  (integrated with the real database)

Originally this file returned hardcoded mock data. Tristan built the
dashboard so that ALL data came through these four functions, with a
note that database integration should happen HERE and nowhere else
(services.py, the partials and the calendar keep working unchanged).

Marcus has now done that integration: each function below returns the
SAME shape it used to, but the values come from the real database,
scoped to the currently logged-in user.

  routes.py  ->  services.py  ->  mock_data.py  ->  DATABASE

The filename is kept as mock_data.py only so services.py's imports
don't change. It is no longer mock data.
=========================================================
"""
from datetime import datetime

from flask_login import current_user

from ..models import Booking, Notification, Review


# =========================================================
# Small helpers
# =========================================================

def _display_date(iso_date):
    """Turn a stored '2026-07-13' into '13 Jul 2026'.

    The calendar (services.get_calendar_data) splits this on spaces and
    expects  day / month-abbrev / year , so this exact format matters.
    Falls back to the raw string if it isn't ISO for some reason.
    """
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d %b %Y")
    except (ValueError, TypeError):
        return iso_date or ""


def _tidy_price(price):
    """Show 45 instead of 45.0, but keep 45.5 as-is."""
    try:
        return int(price) if float(price).is_integer() else price
    except (ValueError, TypeError):
        return price


def _humanise(dt):
    """Turn a datetime into 'Just now' / '5 minutes ago' / '3 days ago'."""
    if not dt:
        return ""
    seconds = (datetime.utcnow() - dt).total_seconds()
    if seconds < 60:
        return "Just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(hours // 24)
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    return dt.strftime("%d %b %Y")


def _activity_title(message):
    """Derive a short heading from a notification's message text.

    Order matters: a *pending* message says "received and pending
    confirmation", which contains the word "confirmation" — so we must
    check the pending wording BEFORE the confirmed wording, and match on
    specific phrases rather than the bare substring "confirm".
    """
    text = (message or "").lower()
    if "pending confirmation" in text or "received" in text:
        return "Booking Received"
    if "is confirmed" in text or "booking is confirmed" in text:
        return "Booking Confirmed"
    if "complete" in text:
        return "Booking Completed"
    if "awaiting approval" in text:
        return "Review Submitted"
    if "review" in text or "feedback" in text:
        return "Review Update"
    if "booking" in text:
        return "Booking Update"
    return "Notification"


# =========================================================
# BOOKINGS  ->  every booking belonging to the current user
# =========================================================

def get_bookings():
    """Real bookings for the logged-in user, oldest first.

    Returns the same list-of-dicts shape the dashboard already expects.
    (There is no 'cleaner' column in the database yet, so we show a
    sensible placeholder until that feature exists.)
    """
    if not current_user.is_authenticated:
        return []

    rows = (Booking.query
            .filter_by(user_id=current_user.id)
            .order_by(Booking.date.asc())
            .all())

    bookings = []
    for b in rows:
        service_name = b.service.name if b.service else "Service"
        price = b.service.price if b.service else 0
        duration = b.service.duration if b.service else ""
        bookings.append({
            "id": b.id,
            "service": service_name,
            "date": _display_date(b.date),
            "time": b.time,
            "status": b.status,
            "address": b.address,
            # No cleaner-assignment feature exists yet, so we don't invent
            # a name. Key kept (empty) because services.py's calendar
            # builder reads it; nothing displays it in the UI anymore.
            "cleaner": "",
            "notes": b.notes or "",
            "price": _tidy_price(price),
            "duration": duration,
        })
    return bookings


# =========================================================
# RECENT ACTIVITY  ->  the current user's latest notifications
# =========================================================

def get_recent_activity():
    if not current_user.is_authenticated:
        return []

    rows = (Notification.query
            .filter_by(user_id=current_user.id)
            .order_by(Notification.created_at.desc())
            .limit(5)
            .all())

    return [{
        "title": _activity_title(n.message),
        "description": n.message,
        "time": _humanise(n.created_at),
    } for n in rows]


# =========================================================
# CLEANING TIPS  ->  static app content (not user data)
# =========================================================

def get_cleaning_tips():
    """These are general app content, not database records, so they stay
    as a fixed list. (Could become a CleaningTip table later.)"""
    return [
        {
            "title": "Declutter First",
            "message":
            "Clear tables, floors and countertops before "
            "your cleaner arrives to maximise cleaning efficiency.",
        },
        {
            "title": "Separate Fragile Items",
            "message":
            "Store fragile decorations and valuables safely "
            "before the cleaning session begins.",
        },
        {
            "title": "Secure Your Pets",
            "message":
            "Keeping pets in a safe room helps both your cleaner "
            "and your furry friends stay safe.",
        },
        {
            "title": "Prepare Special Instructions",
            "message":
            "Leave notes for rooms or areas requiring "
            "extra attention.",
        },
        {
            "title": "Ventilate After Cleaning",
            "message":
            "Open windows for several minutes after cleaning "
            "to improve indoor air quality.",
        },
        {
            "title": "Regular Cleaning Saves Time",
            "message":
            "Scheduling regular cleaning prevents dirt build-up "
            "and reduces future cleaning effort.",
        },
    ]


# =========================================================
# REVIEW PREVIEW  ->  the current user's most recent review
# =========================================================

def get_latest_review():
    if not current_user.is_authenticated:
        return None

    r = (Review.query
         .filter_by(user_id=current_user.id)
         .order_by(Review.created_at.desc())
         .first())

    if not r:
        return None

    return {
        "service": r.service.name if r.service else "Service",
        "rating": r.rating,
        "comment": r.review_description or r.review_title or "",
        "date": _humanise(r.created_at),
    }