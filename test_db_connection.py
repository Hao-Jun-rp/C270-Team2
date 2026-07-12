"""
Quick check that your DATABASE_URL actually connects — run this BEFORE seeding,
so a wrong password or missing cert fails here with a clear message instead of
halfway through creating tables.

    python test_db_connection.py

Prints the database it connected to (password hidden) and the server version.
"""
from sqlalchemy import text

from app import create_app
from app.extensions import db

app = create_app()
with app.app_context():
    url = db.engine.url
    print("Trying:", url.render_as_string(hide_password=True))
    try:
        with db.engine.connect() as conn:
            version = conn.execute(text("SELECT VERSION()")).scalar()
        backend = db.engine.url.get_backend_name()
        print(f"SUCCESS — connected to {backend}.")
        print("Server version:", version)
    except Exception as e:
        print("FAILED to connect:")
        print(" ", type(e).__name__, "-", e)
        print("\nChecklist: DATABASE_URL correct? password right? "
              "CA cert path valid? your IP allowed in Aiven?")
