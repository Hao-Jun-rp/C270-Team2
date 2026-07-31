"""All the app's settings live here (owned by the team lead)."""
import os

# Load a local .env file if python-dotenv is installed (pip install python-dotenv).
# .env is gitignored — never commit it.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # If DATABASE_URL is set (in .env), use that shared database (e.g. MySQL on Aiven).
    # If not, fall back to the local SQLite file — no setup needed.
    #   shared: mysql+pymysql://user:pass@host:port/dbname
    #   local:  sqlite:///sparkle.db
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///sparkle.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---- Shared MySQL (Aiven) needs an encrypted TLS connection ----
    # Local SQLite needs none of this, so we only add options for MySQL.
    # MYSQL_SSL_CA points at Aiven's CA certificate (download it from the
    # Aiven console). Defaults to certs/aiven-ca.pem so if you drop the file
    # there you don't even need the env var.
    #   pool_pre_ping reconnects dropped idle connections (Aiven's free tier
    #   closes idle ones), so you don't hit "MySQL server has gone away".
    SQLALCHEMY_ENGINE_OPTIONS = {}
    if SQLALCHEMY_DATABASE_URI.startswith("mysql"):
        _ca = os.environ.get("MYSQL_SSL_CA", "certs/aiven-ca.pem")
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {"ssl": {"ca": _ca}},
            "pool_pre_ping": True,
        }

    # ---- Session cookie hardening ----
    # Secure=True tells the browser to send the session cookie ONLY over HTTPS.
    # Correct in production, but it would break local development over
    # http://localhost, so it is opt-in via an env var set only on the server.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    # Blocks JavaScript from reading the cookie (mitigates session theft via XSS).
    SESSION_COOKIE_HTTPONLY = True
    # Not sent on cross-site POSTs, which blunts CSRF. "Lax" still allows
    # normal link navigation, so logging in and browsing are unaffected.
    SESSION_COOKIE_SAMESITE = "Lax"
