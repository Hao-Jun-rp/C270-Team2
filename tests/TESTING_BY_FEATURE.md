# Testing By Feature

Use this when something breaks and you want to check **just one feature**,
instead of running the whole suite. Find your name below, copy the command,
run it.

All commands assume your venv is active:
```
venv\Scripts\activate
```

---

## Marcus — Auth, Admin

```
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_admin.py -v
```
Covers: login/register/password reset, `@admin_required` access control,
booking status transitions (Pending → Confirmed → Completed), the demo
payment lifecycle (Authorized → Paid/Refunded), review moderation
(approving a review recalculates the service's rating), and **Services
CRUD** (create/edit/toggle a service, category validated server-side
against the fixed list, negative prices rejected, and the deactivated
service correctly disappearing from `/listings` — the actual admin-to-user
sync proven end-to-end).

---

## Hazirah — Listings

```
python -m pytest tests/test_listings.py -v
```
Covers: services load from the database, `is_active` filtering, fixed
category tabs, review counts only include Approved reviews, model defaults.

With coverage:
```
python -m pytest tests/test_listings.py -v --cov=app.listings --cov-report=term-missing
```

---

## Ashish — Booking

```
python -m pytest tests/test_booking.py -v
```
Covers: time-slot generation from a service's duration, Luhn card
validation + expiry/CVV checks, creating a booking (happy path + rejected
bad input), and the edit/cancel rules — including a Confirmed booking
reverting to Pending when edited.

With coverage:
```
python -m pytest tests/test_booking.py -v --cov=app.booking --cov-report=term-missing
```

---

## Matthew — Reviews

```
python -m pytest tests/test_reviews.py -v
```
Covers: only Approved reviews are public, the "verified purchase" rule (must
have a Completed booking to review a service), no duplicate reviews per
service, and rejecting submissions with no rating / empty text.

With coverage:
```
python -m pytest tests/test_reviews.py -v --cov=app.reviews --cov-report=term-missing
```

---

## Tristan — Dashboard

```
python -m pytest tests/test_dashboard.py -v
```

---

## Hao Jun — Notifications

```
python -m pytest tests/test_notifications.py -v
```

---

## Everyone — Smoke test

```
python -m pytest tests/test_smoke.py -v
```
The most basic check: does the app even start and does the homepage load.
If THIS fails, something is broken at a fundamental level (bad import,
missing config, etc.) — fix this before worrying about any feature-specific
failure.

---

# How to read a failure

```
FAILED tests/test_booking.py::test_editing_a_confirmed_booking_reverts_it_to_pending
```

Reading this tells you three things immediately:
1. **Which file** — `test_booking.py` → Booking feature
2. **Which behaviour** — the test name describes what should happen in plain
   English
3. **Who to talk to** — check the owner table in `README.md`, or just fix it
   yourself if it's your own file

Scroll up from `FAILED` to find the `assert` line that broke — it shows you
exactly what was expected vs. what actually happened.

---

# If you changed code and aren't sure what broke

Run everything, not just your own file — a change in one feature can
sometimes break another (e.g. changing `Service` affects Listings, Booking,
AND Reviews, since they all depend on it):

```
python -m pytest tests/ -v
```
