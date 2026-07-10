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
