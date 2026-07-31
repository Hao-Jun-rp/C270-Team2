# Dashboard Feature

**Author**
Tristan Wong

---

# Purpose

The Dashboard serves as the user's landing page after logging in.

Rather than duplicating functionality from other modules, it provides a concise overview of the user's bookings, recent activities, reviews and quick access to other modules.

The current implementation uses mock data through a service layer so that future database integration can be completed with minimal frontend changes.

---

# Dashboard Sections

## Overview

* Greeting
* Booking Summary
* Interactive Booking Calendar (FullCalendar)
* Next Booking

## Bookings

* Upcoming Bookings
* Empty State (shown when no bookings exist)

## Activity

* Recent Activity
* Latest Review
* Cleaning Tips
* Quick Actions

---

# Folder Structure

```
dashboard/

├── routes.py
├── services.py
├── mock_data.py
├── README.md
│
├── static/
│   ├── dashboard.css
│   └── dashboard.js
│
└── templates/
    └── dashboard/
        ├── home.html
        │
        └── partials/
            ├── overview/
            │   ├── greeting.html
            │   ├── summary.html
            │   ├── calendar.html
            │   ├── booking_status_legend.html
            │   └── next_booking.html
            │
            ├── bookings/
            │   ├── upcoming_bookings.html
            │   └── empty_state.html
            │
            └── activity/
                ├── recent_activity.html
                ├── review_preview.html
                ├── cleaning_tip.html
                └── quick_actions.html
```

---

# Current Architecture

```
Browser
      │
      ▼

dashboard.js
      │
      ▼

home.html
      │
      ▼

routes.py
      │
      ▼

services.py
      │
      ▼

mock_data.py
      │
      ▼

(Mock Database)

(Future)

Database
```

The Dashboard follows a layered architecture.

* **routes.py** only handles routing.
* **services.py** contains all business logic.
* **mock_data.py** currently supplies temporary data.
* Templates only display data.
* dashboard.js handles frontend interactions only.

---

# Current Features

## Greeting

Displays the authenticated user's name when logged in.

Falls back to **Guest** otherwise.

---

## Booking Summary

Displays:

* Upcoming bookings
* Pending bookings
* Completed bookings
* Total bookings

---

## Interactive Booking Calendar

Implemented using FullCalendar.

Features:

* Monthly calendar
* Previous / Next month navigation
* Today button
* Booking colour indicators
* Click booking to view details
* Selected Booking card updates dynamically
* Supports one year before and after current month

Calendar event data is supplied by:

```
services.py

↓

get_calendar_data()

↓

dashboard.js
```

---

## Next Booking

Displays the nearest confirmed booking.

---

## Upcoming Bookings

Displays the first three upcoming bookings.

Users can navigate to the full Booking module.

---

## Recent Activity

Displays the latest activity items.

Future integration should connect this section to the Notification module.

---

## Latest Review

Displays the latest submitted review.

Future integration should connect this section to the Review module.

---

## Cleaning Tips

Displays rotating cleaning tips.

Navigation is handled entirely in JavaScript.

---

## Quick Actions

Provides shortcuts to:

* Listings
* Booking
* Notifications
* Reviews

---

# Current Data Source

The dashboard currently uses:

```
mock_data.py
```

Available mock datasets:

* Bookings
* Cleaning Tips
* Recent Activity
* Latest Review

---

# Database Integration Guide (Marcus)

## IMPORTANT

Most database integration should ONLY require editing:

```
dashboard/mock_data.py
```

or replacing it with a repository/database layer.

The remaining Dashboard should continue working without frontend modifications.

---

## Files Marcus SHOULD Edit

### mock_data.py

Replace:

```
get_bookings()
```

with Booking database queries.

Replace:

```
get_recent_activity()
```

with Notification queries.

Replace:

```
get_latest_review()
```

with Review queries.

Replace:

```
get_cleaning_tips()
```

if tips are later stored inside the database.

---

### services.py

Only edit this file if:

* Booking model field names differ
* New dashboard statistics are required
* Additional business logic is added
* Calendar event formatting changes

Current important functions:

* get_summary()
* get_next_booking()
* get_upcoming_bookings()
* get_calendar_data()
* get_dashboard_data()

---

## Files Marcus SHOULD NOT Edit

Normally there should be no need to modify:

```
routes.py
```

Routes should remain lightweight.

---

No changes should normally be required in:

```
home.html
```

or any files inside:

```
templates/dashboard/
```

unless the UI itself changes.

---

No changes should normally be required in:

```
dashboard.js
```

The calendar automatically consumes whatever events are returned by:

```
services.py
```

provided each event follows the format:

```python
{
    "title": "...",
    "start": "YYYY-MM-DD",

    "extendedProps": {
        "status": "...",
        "time": "...",
        "cleaner": "...",
        "address": "...",
        "notes": "...",
        "price": ...,
        "duration": "..."
    }
}
```

---

# Route Dependencies

The Dashboard currently expects the following routes to exist:

```
dashboard.home
booking.index
listings.index
notifications.index
reviews.index
```

If these route names change, update the corresponding:

```
url_for(...)
```

statements inside the templates.

---

# Authentication

Current greeting supports:

```
current_user.name
```

If authentication changes, only update:

```
greeting.html
```

---

# Future Improvements

Possible enhancements:

* AJAX calendar loading
* Drag-and-drop bookings
* Calendar filters
* Responsive mobile calendar
* Booking search
* Charts and analytics
* Notification badges
* Dynamic cleaning tips from database

---

# Current Status

✅ Modular architecture

✅ Service layer

✅ Mock data implementation

✅ Interactive FullCalendar integration

✅ Dynamic Selected Booking card

✅ Booking Summary

✅ Next Booking

✅ Upcoming Bookings

✅ Recent Activity

✅ Latest Review

✅ Cleaning Tips

✅ Quick Actions

✅ Ready for Booking database integration

✅ Ready for Notification integration

✅ Ready for Review integration


--- Extra Note (For Marcus): ---
The dashboard has been designed so that database integration should primarily occur in mock_data.py (or its replacement repository layer). If the Booking, Notification, or Review models expose different field names, update the transformation logic inside services.py. Avoid modifying routes.py, dashboard.js, or the HTML templates unless the application's UI or route names change. This separation keeps business logic independent from presentation and minimizes merge conflicts with other modules.