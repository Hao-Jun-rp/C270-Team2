"""
=========================================================
Dashboard Services

Business Logic Layer

Architecture

routes.py
    ↓
services.py
    ↓
mock_data.py
    ↓
(Database in the future)

=========================================================

IMPORTANT FOR FUTURE INTEGRATION

Marcus:

This file should remain the ONLY place containing
dashboard business logic.

When the database is ready:

DO NOT edit routes.py.

Simply replace the functions inside mock_data.py
(or rename it to repository/database layer).

The dashboard will continue working automatically.

=========================================================
"""


from datetime import datetime

from .mock_data import (
    get_bookings,
    get_recent_activity,
    get_cleaning_tips,
    get_latest_review
)


# =========================================================
# SUMMARY
# =========================================================

def get_summary(bookings):

    return {

        "upcoming": len([
            booking
            for booking in bookings
            if booking["status"] == "Confirmed"
        ]),

        "pending": len([
            booking
            for booking in bookings
            if booking["status"] == "Pending"
        ]),

        "completed": len([
            booking
            for booking in bookings
            if booking["status"] == "Completed"
        ])

    }


# =========================================================
# NEXT BOOKING
# =========================================================

def get_next_booking(bookings):

    for booking in bookings:

        if booking["status"] == "Confirmed":

            return booking

    return None


# =========================================================
# UPCOMING BOOKINGS
# =========================================================

def get_upcoming_bookings(bookings):

    """First 3 FUTURE bookings that are Pending or Confirmed,
    nearest date first. (Fixed by Marcus: previously this only
    showed Confirmed bookings, so users whose bookings are all
    Pending saw an empty state.) Dates arrive as '13 Jul 2026'."""

    today = datetime.now().date()

    upcoming = []

    for booking in bookings:

        if booking["status"] not in ("Pending", "Confirmed"):
            continue

        try:
            booking_date = datetime.strptime(
                booking["date"], "%d %b %Y"
            ).date()
        except (ValueError, TypeError):
            continue

        if booking_date >= today:
            upcoming.append((booking_date, booking))

    upcoming.sort(key=lambda pair: pair[0])

    return [booking for _, booking in upcoming[:3]]


# =========================================================
# CALENDAR
# =========================================================

def get_calendar_data():

    """
    =====================================================
    Returns booking events in FullCalendar format.

    Marcus:
    Replace get_bookings() with database query only.
    No frontend changes will be required.
    =====================================================
    """

    bookings = get_bookings()

    events = []

    month_lookup = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12
    }

    for booking in bookings:

        try:

            day, month, year = booking["date"].split()

            month_number = month_lookup[month]

            start_date = (
                f"{year}-"
                f"{month_number:02d}-"
                f"{int(day):02d}"
            )

        except Exception:

            continue

        events.append({

            "title": booking["service"],

            "start": start_date,

            "extendedProps": {

                "status": booking["status"],

                "time": booking["time"],

                "cleaner": booking["cleaner"],

                "address": booking["address"],

                "notes": booking["notes"],

                "price": booking["price"],

                "duration": booking["duration"]
}

        })

    return events


# =========================================================
# DASHBOARD DATA
# =========================================================

def get_dashboard_data(current_tip=0):

    """
    =====================================================
    Main dashboard service.

    Routes should only call this function.

    Any future dashboard feature should be added here.

    =====================================================
    """

    bookings = get_bookings()

    tips = get_cleaning_tips()

    if current_tip < 0:

        current_tip = 0

    if current_tip >= len(tips):

        current_tip = len(tips) - 1

    return {

        "bookings": bookings,

        "summary": get_summary(bookings),

        "next_booking": get_next_booking(bookings),

        "upcoming_bookings": get_upcoming_bookings(bookings),

        "activities": get_recent_activity(),

        "latest_review": get_latest_review(),

        "calendar": get_calendar_data(),

        "tips": tips,

        "current_tip": current_tip

    }
