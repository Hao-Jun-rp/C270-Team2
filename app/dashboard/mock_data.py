"""
=========================================================
Dashboard Mock Data

Temporary data source for the Dashboard feature.

---------------------------------------------------------

Current Architecture

routes.py
    ↓
services.py
    ↓
mock_data.py

---------------------------------------------------------

Future Integration (Marcus)

Replace ALL functions in this file with actual
database queries.

The rest of the dashboard should continue working
without requiring changes.

=========================================================
"""


# =========================================================
# BOOKINGS
# =========================================================

def get_bookings():

    return [

        {
            "id": 1,
            "service": "Deep Clean",
            "date": "15 Jan 2027",
            "time": "10:00 AM",
            "status": "Confirmed",
            "address": "12 Orchard Road",
            "cleaner": "John Tan",
            "notes": "Bring eco-friendly products.",
            "price": 89,
            "duration": "2 Hours"
        },

        {
            "id": 2,
            "service": "Standard Clean",
            "date": "22 Jan 2027",
            "time": "2:00 PM",
            "status": "Pending",
            "address": "88 Clementi Ave",
            "cleaner": "Pending Assignment",
            "notes": "",
            "price": 59,
            "duration": "1 Hour"
        },

        {
            "id": 3,
            "service": "Eco Clean",
            "date": "28 Jan 2027",
            "time": "9:00 AM",
            "status": "Confirmed",
            "address": "45 Jurong East Street",
            "cleaner": "Sarah Lim",
            "notes": "Focus on kitchen.",
            "price": 69,
            "duration": "1.5 Hours"
        },

        {
            "id": 4,
            "service": "Move-out Clean",
            "date": "4 Feb 2027",
            "time": "1:00 PM",
            "status": "Completed",
            "address": "100 Punggol Drive",
            "cleaner": "Michael Lee",
            "notes": "",
            "price": 129,
            "duration": "4 Hours"
        }

    ]


# =========================================================
# RECENT ACTIVITY
# =========================================================

def get_recent_activity():

    return [

        {
            "title": "Booking Confirmed",
            "time": "Today"
        },

        {
            "title": "Cleaner Assigned",
            "time": "Yesterday"
        },

        {
            "title": "Review Submitted",
            "time": "3 days ago"
        }

    ]


# =========================================================
# CLEANING TIPS
# =========================================================

def get_cleaning_tips():

    return [

        {
            "title": "Declutter First",
            "message":
            "Clear tables, floors and countertops before "
            "your cleaner arrives to maximise cleaning efficiency."
        },

        {
            "title": "Separate Fragile Items",
            "message":
            "Store fragile decorations and valuables safely "
            "before the cleaning session begins."
        },

        {
            "title": "Secure Your Pets",
            "message":
            "Keeping pets in a safe room helps both your cleaner "
            "and your furry friends stay safe."
        },

        {
            "title": "Prepare Special Instructions",
            "message":
            "Leave notes for rooms or areas requiring "
            "extra attention."
        },

        {
            "title": "Ventilate After Cleaning",
            "message":
            "Open windows for several minutes after cleaning "
            "to improve indoor air quality."
        },

        {
            "title": "Regular Cleaning Saves Time",
            "message":
            "Scheduling regular cleaning prevents dirt build-up "
            "and reduces future cleaning effort."
        }

    ]


# =========================================================
# REVIEW PREVIEW
# =========================================================

def get_latest_review():

    return {

        "service": "Eco Clean",

        "rating": 5,

        "comment": "Cleaner was punctual and very thorough.",

        "date": "2 days ago"

    }