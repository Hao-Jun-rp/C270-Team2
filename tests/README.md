# Tests

**Author**
Hazirah (Listings feature)

---

# Purpose

Automated tests for the Listings feature, using **pytest**. These check that
services load correctly from the database, `is_active` filtering works,
categories are generated dynamically, and review counts are calculated
correctly.

Tests run against a temporary **in-memory database** — they never touch our
shared Aiven MySQL database, so it's safe to run them anytime without
affecting anyone else's data.

These tests are also the "test" step in Tristan's CI/CD pipeline — every
push to `main` runs this suite automatically.

---

# How to run

**1. Make sure your venv is active and dependencies are installed:**
```
venv\Scripts\activate
python -m pip install -r requirements.txt
```

**2. Run all tests:**
```
python -m pytest tests/ -v
```

**3. Run just the listings tests:**
```
python -m pytest tests/test_listings.py -v
```

You should see something like:
```
9 passed in 0.76s
```

If you see `FAILED` instead of `PASSED` for any test, read the error message
above it — it'll point to the exact assertion that broke, which usually means
something in `listings/routes.py` or the `Service`/`Review` models changed
in a way that broke expected behaviour.

---

# Optional: coverage report

Shows exactly which lines of `listings/routes.py` are actually exercised by
the tests.

```
python -m pip install pytest-cov
python -m pytest tests/test_listings.py -v --cov=app.listings --cov-report=term-missing
```

---

# Files

| File | What it does |
|---|---|
| `conftest.py` | Shared setup — creates a fresh, isolated in-memory database for each test |
| `test_listings.py` | The actual test cases for the Listings feature |
| `test_smoke.py` | Marcus's basic "does the app start" check |

---

# Note

You'll see some `DeprecationWarning` messages about `datetime.utcnow()` when
running these — that's unrelated to the tests themselves (it's coming from
`models.py`), and doesn't mean anything is broken.
