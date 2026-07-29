Sparkle — Logic Review build (customer cancel/edit, verified reviews, admin guard, live badge, real dates)
=========================================================================================================

Extract this over your cleaning-app folder (replace when asked). Your venv,
.git, instance and .env are NOT in this zip, so they stay as they are.

*** YOU MUST REBUILD THE DATABASE ***
Booking.date changed from text to a real DATE column, so the table must be
recreated:
    - Stop the app.
    - venv\Scripts\activate
    - python reset_and_seed.py     (if on shared Aiven, ONE person runs this)
    - python run.py

WHAT WAS BUILT (from the decisions in SPARKLE_LOGIC_REVIEW.md)

C1 — Customers can now CANCEL and EDIT their own bookings
  - On "My bookings", Pending/Confirmed bookings show Edit + Cancel buttons.
  - Edit: change date, time, address, notes (NOT service — to change service,
    cancel and rebook, as you decided). Same validation as booking (no past
    dates/slots, slot must fit the service).
  - Editing a CONFIRMED booking sends it back to Pending for admin
    re-confirmation (with a notification). Editing a Pending one stays Pending.
  - Cancel: sets status to Cancelled (Pending/Confirmed only) + notifies.
  - Ownership enforced: you can only touch your own booking, and only while
    it's Pending/Confirmed (Completed/Cancelled are locked).

C2 — Reviews now require a completed booking ("verified purchase")
  - The reviews-page dropdown only lists services you've COMPLETED and not yet
    reviewed. If you have none, a friendly note explains you can review after a
    completed clean.
  - The server also enforces it: submitting a review for a service you haven't
    completed is rejected. Duplicate reviews still blocked.
  - Added the optional Title field on the review form (P2).

I1 — Admin booking status transitions are now enforced server-side
  - Only sensible moves are allowed: Pending→Confirmed/Cancelled,
    Confirmed→Completed/Cancelled. Completed and Cancelled are final.
  - A crafted request trying Completed→Pending etc. is rejected.

I2 — Live admin badge (no refresh)
  - The "Admin" nav link shows a red badge with how many bookings + reviews
    need attention, and it updates itself every 30s (same polling style as the
    notification bell). No manual refresh needed.

I3 — Booking date is now a real DATE type (was free text)
  - Proper date storage/sorting. `time` stays a slot label ("09:00–12:00")
    on purpose — it's a discrete slot (a range), not a single timestamp.

POLISH
  P1  Registration caps name at 80 chars (form + server) so it can't overflow
      the DB column on MySQL.
  P3  Fixed a stale "run python seed.py" comment (it's seed_demo.py now).
  P4  Removed dead notify_booking_confirmed() helper.
  P5  (pagination) — skipped for now, per your note.
  P6  (CSRF) — noted as out of scope, per your note.

FILES CHANGED
  app\models.py                         Booking.date -> Date
  app\booking\routes.py                 cancel + edit + shared validation
  app\booking\templates\booking\index.html        Edit/Cancel buttons, date tiles
  app\booking\templates\booking\editbooking.html   NEW edit form
  app\reviews\routes.py                 verified-purchase rule + reviewable list + title
  app\reviews\templates\reviews\index.html         filtered dropdown, title field, empty state
  app\admin\routes.py                   transition guard + /admin/api/pending-count
  app\templates\base.html               live admin badge + poll
  app\dashboard\mock_data.py            _display_date handles real dates
  app\auth\routes.py, register.html     name length cap
  app\listings\routes.py                stale comment fix
  app\notifications\routes.py           removed dead helper
  seed_demo.py                          seeds real date objects

QUICK TEST (after reseeding, as aisha@example.com / password123)
  1. My bookings -> a Pending/Confirmed booking shows Edit + Cancel.
  2. Edit a Confirmed booking's time -> it flips to Pending ("re-confirmation").
  3. Cancel a booking -> status Cancelled + a notification.
  4. Reviews page -> dropdown only lists services you completed & haven't
     reviewed; if none, you see the "after a completed clean" note.
  5. As Marcus (admin) -> the Admin nav shows a live count badge; try to
     move a Completed booking -> it's refused.
