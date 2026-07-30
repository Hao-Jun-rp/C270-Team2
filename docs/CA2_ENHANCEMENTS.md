# CA2 Enhancements & Corrections (post-demo)

Changes made to Sparkle after the CA2 demo, in response to demo feedback,
testing, and issues found while preparing for the Final Assessment. This file
is the source material for the "CA2 Enhancements" section of the FA slides
(5% of the team grade).

## In response to CA2 demo feedback

### 1. Service-add crash on the public listings page
`listings/index.html` built the image path with `'images/' + service.image`.
A service added without an image stores `None`, so string concatenation threw
and the whole public listings page crashed for everyone.
**Fix:** `{% if service.image %}` guard with a branded placeholder for
imageless services.

### 2. Payment lifecycle reworked ("Pending but already Paid?")
At CA2, PayNow/Card bookings showed **Paid** while still **Pending** — which
an assessor rightly questioned. Payments (demo-only, no card data stored) now
follow a realistic authorize/capture flow:

- PayNow/Card: **Authorized (demo)** at booking → **Paid (demo)** when the
  admin confirms → **Refunded (demo)** on cancellation.
- Editing a Confirmed booking reverts it to Pending and releases the capture
  back to Authorized.
- Cash: **Unpaid** → **Paid (cash on completion)** when marked Completed.

No schema change, so no database rebuild was needed.

### 3. Forgot / reset password
Requested at the demo. Implemented with a signed, 30-minute-expiry token via
`itsdangerous` (already a Flask dependency — no new package). In demo mode the
reset link is shown on screen; in production the single `render_template` call
becomes a `send_email(...)` call. Expired or tampered tokens are rejected.

## Corrections from testing / code review

### 4. Category validation (Hazirah)
Service categories were previously derived from whatever text an admin typed.
They are now a fixed list in `app/constants.py`, enforced server-side, with a
dropdown in the admin form.

### 5. Test isolation: smoke tests hit the live database
`tests/test_smoke.py` called bare `create_app()`; since `config.py` runs
`load_dotenv()`, on any machine with a `.env` the smoke tests connected to the
**real shared Aiven database**. Now all tests use the shared `client` fixture
(in-memory SQLite). Three smoke tests added (404 page, login page, dashboard
redirect when logged out).

### 6. `pytest.ini` added: utility script collected as a test
`test_db_connection.py` in the project root is a connectivity checker, not a
test — but its name matches pytest's `test_*.py` pattern, so plain `pytest`
imported it and its module-level code connected to the real database, making
the suite fail whenever Aiven was slow. `testpaths = tests` restricts
collection to real, isolated tests.

### 7. docker-compose: empty `SECRET_KEY` crash
Compose substitutes an *unset* shell variable with an *empty string*, so
`SECRET_KEY=${SECRET_KEY}` silently started Flask with `SECRET_KEY=""` and
login crashed at runtime. Compose now uses `env_file: .env` so a variable is
either genuinely present or genuinely absent. A container healthcheck was
added at the same time.

### 8. Dockerfile hardening (Ashish)
Removed ~300MB of unnecessary apt build tools (we use pure-Python PyMySQL,
not `mysqlclient`), added a non-root `appuser`, and configured gunicorn with
2 workers, a timeout, and access/error logs to stdout for `docker logs` /
CloudWatch.

### 9. Repository hygiene
Removed a duplicated nested project folder that broke pytest collection,
plus two dead legacy templates left over from the dashboard rework.
