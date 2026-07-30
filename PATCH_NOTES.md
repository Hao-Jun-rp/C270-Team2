# Sparkle — DevOps patch (apply over your project folder)

Unzip this **inside your project folder** (the one containing `run.py`,
`app/`, `requirements.txt`). It overwrites 3 files:

```
Dockerfile              <- replaced
docker-compose.yml      <- replaced
tests/test_smoke.py     <- replaced
pytest.ini              <- NEW
```

Nothing else is touched. Hazirah's `conftest.py` and `test_listings.py` are
left exactly as they are.

## Check it worked

```
python -m pytest -q
```
You should see **14 passed** (was 11 — the new smoke file adds 3 tests).

---

## What changed and why

### 1. `tests/test_smoke.py` — was running against the SHARED Aiven database
The old version called `create_app()` with no arguments. `app/config.py` calls
`load_dotenv()`, so on any machine with a `.env` file this test connected to
the **real shared team database** instead of a test one — and on a CI runner it
silently created an `instance/sparkle.db` file.

Now it uses the `client` fixture from `conftest.py`, so it runs against a
throwaway in-memory database like the rest of the suite. Also added 3 tests:
a 404 check, the login page, and that `/dashboard` redirects when logged out.

### 2. `docker-compose.yml` — empty SECRET_KEY crash
Docker Compose replaces an **unset** variable with an **empty string**. So
`SECRET_KEY=${SECRET_KEY}` with nothing set started the container with
`SECRET_KEY=""`, and Flask throws *"session is unavailable because no secret
key was set"* the moment anyone logs in.

Now it uses `env_file: .env`, so a variable is either genuinely present or
genuinely absent. Also added a `healthcheck`, and a commented-out local MySQL
service for a fully self-contained `docker compose up`.

### 3. `Dockerfile` — smaller, and no longer runs as root
- Removed `build-essential`, `pkg-config`, `default-libmysqlclient-dev`
  (~300MB). Those are needed for `mysqlclient`; we use **PyMySQL**, which is
  pure Python, and `cryptography` ships prebuilt wheels. Faster CI builds.
- Added a non-root `appuser` — if the app is ever compromised, the attacker
  isn't root inside the container.
- Gunicorn now runs 2 workers with a timeout, and sends access/error logs to
  stdout so `docker logs` (and later AWS CloudWatch) can collect them.
- Kept everything that was already right: layer caching, no secrets in the
  image, port 8000.

---

## Still to decide as a team

**Registry name.** `docker-compose.yml` still says `sparkle-app:latest`.
If you go with AWS ECR the tag becomes
`<account-id>.dkr.ecr.<region>.amazonaws.com/sparkle-app:latest`.
Tristan's pipeline and the deploy step both need the same string.

**Healthcheck endpoint.** The compose healthcheck currently pings `/`.
Swap it to `/health` once Hao Jun's endpoint is merged.

### 4. `pytest.ini` (NEW) — stop `pytest` connecting to the shared database
`test_db_connection.py` in the project root is a **utility script**, not a
test — but its filename matches pytest's `test_*.py` pattern, so running
plain `pytest` imported it and its module-level code **connected to the real
Aiven database**. That made the test suite depend on Aiven being up.

`pytest.ini` restricts collection to the `tests/` folder, so `pytest` only
runs real isolated tests.

**Optional tidy-up:** also rename the script so it can never be picked up:
```
git mv test_db_connection.py check_db_connection.py
```
(then run it as `python check_db_connection.py`)
