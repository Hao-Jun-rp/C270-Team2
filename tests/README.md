# Tests — Full Suite

**Maintained by**
Hazirah (Listings + test suite setup)

---

# Purpose

Automated tests for the whole app, using **pytest**. Every feature has its
own test file, written by whoever owns that feature (or by Hazirah, for
Booking and Reviews).

Tests run against a temporary **in-memory database** — they never touch our
shared Aiven MySQL database, so it's safe to run them anytime without
affecting anyone else's data.

This suite is also the "test" step in Tristan's CI/CD pipeline — every push
to `main` runs all of it automatically. If anything here fails, the pipeline
stops before Docker even builds.

For running just ONE person's tests (useful when tracking down a bug in a
specific feature), see **`TESTING_BY_FEATURE.md`** instead.

---

# How to run everything

**1. Make sure your venv is active and dependencies are installed:**
```
venv\Scripts\activate
python -m pip install -r requirements.txt
```

**2. Run the whole suite:**
```
python -m pytest tests/ -v
```

You should see something like:
```
83 passed in 20s
```

If you see `FAILED` instead of `PASSED`, read the error message above it —
it points to the exact assertion that broke, and which file it's in. Use
that to find the right person's section in `TESTING_BY_FEATURE.md`.

---

# Optional: coverage report (whole app)

```
python -m pip install pytest-cov
python -m pytest tests/ --cov=app --cov-report=term-missing
```

---

# Files

| File | Feature | Owner |
|---|---|---|
| `conftest.py` | Shared setup — isolated in-memory DB for every test | Hazirah |
| `test_smoke.py` | Basic "does the app start" checks | Marcus |
| `test_auth.py` | Login, register, password reset | Marcus |
| `test_admin.py` | Booking status transitions, payment lifecycle, review moderation, **Services CRUD** | Marcus (+ Hazirah, Services CRUD section) |
| `test_listings.py` | Services catalogue, filtering, categories | Hazirah |
| `test_booking.py` | Slots, payment validation, edit/cancel rules | Hazirah (written on behalf of Ashish) |
| `test_reviews.py` | Verified-purchase rule, submission, moderation | Hazirah (written on behalf of Matthew) |
| `test_dashboard.py` | Dashboard summary/calendar data | Tristan |
| `test_notifications.py` | Notification creation | Hao Jun |

---

# Note

You'll see `DeprecationWarning` messages about `datetime.utcnow()` and
`LegacyAPIWarning` about `Query.get()` — these are unrelated to whether the
tests pass, they're just Python/SQLAlchemy nudging about older syntax
elsewhere in the app. Not something to fix urgently, and not a sign
anything is broken.

