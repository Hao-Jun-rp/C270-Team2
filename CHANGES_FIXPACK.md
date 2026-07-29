# Sparkle Fix Pack — post-CA2 (July 2026)

Drop-in replacement for the whole project folder. Three fixes from the demo
feedback + one structural repair, all verified end-to-end.

## What changed

### 1. FIXED — "Service tab crashes after admin adds a service"
**Root cause:** `listings/index.html` built the image path with
`'images/' + service.image`. A service added without an image has
`image = None`, and `'images/' + None` throws a TypeError — so the public
listings page crashed for EVERYONE the moment any imageless service existed.
**Fix:** the template now checks `{% if service.image %}` and shows a branded
teal placeholder (the service's initial) when there is no image.
File: `app/listings/templates/listings/index.html`

### 2. CHANGED — Payment logic ("Pending but already Paid?")
PayNow/Card payments are now **authorized, not captured, at booking time**:

| Event                          | payment_status (PayNow/Card) | (Cash)  |
|--------------------------------|------------------------------|---------|
| Customer books                 | **Authorized (demo)**        | Unpaid  |
| Admin confirms                 | **Paid (demo)** (captured)   | Unpaid  |
| Customer edits confirmed booking (reverts to Pending) | back to **Authorized (demo)** | Unpaid |
| Booking cancelled (either side)| **Refunded (demo)**          | Unpaid  |
| Admin completes                | Paid (demo)                  | **Paid (cash on completion)** |

So a Pending booking is never "Paid" any more — the money is only reserved,
and captured when we commit to the job. This mirrors how real card
authorization/capture works and answers the teacher's question directly.
Files: `app/booking/routes.py`, `app/admin/routes.py`, `app/models.py` (comment)

**No database rebuild needed** — no schema change (the column already fits the
new labels). Old rows keep their old labels, which is harmless; run
`python reset_and_seed.py` if you want pristine demo data (⚠️ wipes shared DB).

### 3. NEW — Forgot / reset password
- "Forgot password?" link on the login page → `/forgot`.
- Enter your email → the app generates a **signed, 30-minute reset link**
  (using `itsdangerous`, the same signing library Flask uses for sessions —
  already installed, no new dependency).
- Demo mode: the link is displayed on screen. In production, the one
  `render_template` call would become `send_email(...)` — say exactly this in
  the demo, it's the honest and correct engineering answer.
- The link opens a reset form (same ≥6-char + confirm rules as registration),
  re-hashes with Werkzeug, and rejects expired or tampered tokens.
Files: `app/auth/routes.py` (+ new `forgot.html`, `reset.html`,
link added in `login.html`)

### 4. REMOVED — the nested duplicate project folder
The repo contained a full second copy of the app at
`cleaning-app/cleaning-app/`. It was not just clutter: **pytest refuses to run
with it present** (duplicate `test_smoke.py` module names), which would break
the CI pipeline in Phase 2. This zip ships without it.

⚠️ Extracting a zip does NOT delete files, so also remove it from your local
repo once:
```
git rm -r cleaning-app
git commit -m "Remove duplicated nested project folder (breaks pytest/CI)"
```

## What was verified (28 automated checks, all passing)
- All Python compiles; every `url_for()` in live templates resolves.
- Admin adds a service with no image AND a brand-new category → listings
  renders fine for both logged-in and anonymous users (the original crash).
- Full payment lifecycle: authorize → capture on confirm → re-release on
  customer edit → refund on cancel; cash flow unchanged.
- Forgot-password: link generated, bad email handled, short/mismatched
  passwords rejected, valid reset works, old password stops working, new one
  logs in, tampered tokens rejected.
- Brand-new registered user: every page renders with empty-state data.
- Full render sweep of every page as anonymous / customer / admin.
- pytest passes (once the duplicate folder is removed).

## Setup (unchanged)
Same as before: your existing venv still works. Nothing new to install.
`python run.py` to start; `python reset_and_seed.py` to rebuild demo data.
