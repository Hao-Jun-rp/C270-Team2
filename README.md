# 🧼 Sparkle — Cleaning Service App (C270 DevOps, AY2026S1)

**🔗 Live app:** [https://sparkle-team2.duckdns.org](https://sparkle-team2.duckdns.org)

A team project built with **Python + Flask**, deployed on **AWS EC2** behind
**Nginx + HTTPS**, provisioned with **Ansible**, containerized with **Docker**,
and shipped through a **CI/CD pipeline** that runs tests and a Trivy security
gate on every push. Each teammate owns one feature; this README explains how
the whole thing fits together and how to run it yourself.

---

## 1. See it live, or run it locally

**Just want to look at it?** Visit **[sparkle-team2.duckdns.org](https://sparkle-team2.duckdns.org)**
— no setup needed, it's a real deployment on a real domain with a real
Let's Encrypt certificate.

**Want to run it on your own machine?** Keep reading below.

---

## 2. One-time setup (do this once on your laptop)

You need **Python 3.10+** and **Git** installed.

```bash
# 1. Get the code
git clone https://github.com/Hao-Jun-rp/C270-Team2.git
cd C270-Team2

# 2. Create a "virtual environment" (a clean, private box for this project's libraries)
python -m venv venv

# 3. Turn it on
#    Windows:
venv\Scripts\activate
#    Mac / Linux:
source venv/bin/activate

# 4. Install the libraries the app needs
pip install -r requirements.txt

# 5. Create your secret key file
#    Copy .env.example to .env and put any long random text after SECRET_KEY=
```

By default the app uses a local SQLite file — no database setup needed.
See `.env.example` if you want to point it at the shared Aiven MySQL database
instead.

## 3. Run the app

```bash
python run.py
```

Open the link it prints (usually **http://127.0.0.1:5000**) in your browser.
Try **Sign up → Log in → Book a service** — the full booking flow works
end-to-end, including live notifications.

To stop the app: press **Ctrl + C** in the terminal.

### Running with Docker instead

```bash
docker compose up --build
```

This builds the production image (same one deployed to AWS) and runs it
locally on **http://localhost:8000**, including the container healthcheck.

---

## 4. What the app does

Sparkle is a home-cleaning booking platform. A customer can:
- Sign up, log in, and manage their profile
- Browse cleaning services with transparent flat pricing
- Book a service, choosing a date/time slot and payment method
- Get real-time notifications when a booking is created, confirmed, edited,
  or cancelled — visible instantly via a live-updating navbar bell
- Leave a review after a completed booking

Admins can confirm/complete bookings and approve reviews.

---

## 5. Who owns what (folder map)

```
C270-Team2/
├── app/
│   ├── __init__.py        ← builds the app  (SHARED — ask Marcus before editing)
│   ├── config.py          ← settings         (SHARED)
│   ├── extensions.py      ← db + login tools (SHARED)
│   ├── models.py          ← database tables  (SHARED)
│   ├── constants.py       ← shared fixed lists (e.g. service categories)
│   ├── static/theme.css   ← the design system (SHARED)
│   ├── templates/base.html← shared page layout (SHARED)
│   │
│   ├── auth/          ← Marcus    (login / profile / password reset)
│   ├── dashboard/     ← Tristan
│   ├── listings/      ← Hazirah
│   ├── booking/       ← Ashish    (booking flow + Docker/AWS deployment)
│   ├── reviews/       ← Matthew
│   ├── notifications/ ← Hao Jun   (real-time notifications)
│   └── monitoring/    ← Hao Jun   (/health endpoint)
├── tests/              ← automated tests (pytest)
├── ansible/            ← infrastructure-as-code provisioning (see ansible/README.md)
├── docs/               ← deployment log + CA2 enhancement notes
└── .github/workflows/  ← CI pipeline (tests + Trivy security scan)
```

**You work inside your own folder.** Each folder has:
- `routes.py` — your pages (the web addresses)
- `templates/<your-feature>/` — your HTML pages

Look at the **`auth/`** folder for a complete working example.

---

## 6. Testing

```bash
pytest
```

Runs the full suite (auth, booking, notifications, reviews, admin, listings,
dashboard, smoke tests). Tests use an isolated in-memory database — they
never touch the real shared Aiven database or the live deployment.

---

## 7. Monitoring & observability

- **`GET /health`** — returns `{"status": "ok", "database": "connected"}` and
  HTTP 200 when the app and database are both healthy, or a 503 with
  `"disconnected"` if the database is unreachable. Used by the Docker
  healthcheck and external uptime monitoring — not just a page-render check.
- **Structured logging** — the app logs to stdout using Python's `logging`
  module (not `print()`), so `docker logs` and CloudWatch pick it up
  automatically. Key events (logins, failed logins, bookings created, health
  check failures) are logged at appropriate levels (INFO/WARNING/ERROR).

---

## 8. CI/CD & security

Every push and pull request to `main` triggers:
1. **Automated tests** (`pytest`)
2. **Trivy security scan** — checks dependencies for known CVEs and the repo
   for committed secrets. Findings are reported in the workflow's Summary tab
   and saved as a downloadable artifact. **A CRITICAL-severity finding fails
   the build**, blocking the merge — this isn't just a report, it's an
   enforced gate.

See `.github/workflows/trivy.yml` for the exact configuration.

---

## 9. Deployment

Production runs on **AWS EC2** (Singapore region), behind **Nginx** with a
**Let's Encrypt** TLS certificate, running the Docker image built by CI and
pushed to Docker Hub. Full details — including every command run, security
group setup, and how secrets are managed via AWS SSM Parameter Store — are
documented in **[`docs/DEPLOYMENT_LOG.md`](docs/DEPLOYMENT_LOG.md)**.

Server provisioning is automated with **Ansible** — see
**[`ansible/README.md`](ansible/README.md)** for how to take a blank Ubuntu
machine to a fully running instance of Sparkle, and how idempotency is
proven (running the playbook twice reports zero changes on the second run).

---

## 10. The golden rules (this is what keeps merges smooth)

1. **Only edit your own folder.** Don't touch teammates' folders.
2. **The SHARED files are Marcus's.** Need a new database table or library?
   Tell Marcus — don't edit `models.py`, `config.py`, `__init__.py`, or
   `requirements.txt` yourself.
3. **Always start your work on a fresh branch:**
   ```bash
   git checkout main
   git pull origin main          # get everyone's latest work first
   git checkout -b feature/<your-feature>
   ```
4. **Use the design system.** Style with the classes in `theme.css`
   (`.btn`, `.card`, `.pill`, `.input`) and never hard-code colours — use
   `var(--color-primary)` etc.
5. **Commit small and often, with real messages.**
6. **Merge through a Pull Request** on GitHub (don't push to `main`
   directly). Get one teammate to glance at it before merging.

---

## 11. Daily flow (memorise this)

```
pull main  →  make a branch  →  build in your folder  →  commit  →  push  →  open a Pull Request
```

---

## 12. Further reading

- [`docs/DEPLOYMENT_LOG.md`](docs/DEPLOYMENT_LOG.md) — full AWS deployment record
- [`docs/CA2_ENHANCEMENTS.md`](docs/CA2_ENHANCEMENTS.md) — what changed after CA2 demo feedback
- [`ansible/README.md`](ansible/README.md) — infrastructure-as-code provisioning
- [`tests/TESTING_BY_FEATURE.md`](tests/TESTING_BY_FEATURE.md) — test coverage breakdown

Happy building! ✨
