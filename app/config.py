"""All the app's settings live here (owned by the team lead)."""
import os


class Config:
    # Secret key signs the login cookie. Real value comes from the .env file.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # Use a simple SQLite file as the database — no setup needed.
    SQLALCHEMY_DATABASE_URI = "sqlite:///sparkle.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
