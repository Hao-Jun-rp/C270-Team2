"""
One-command database reset + reseed.

USE THIS whenever the database SCHEMA changed (a new column or table) and you
start getting errors like:  "no such column: user.role".

It DROPS every table, recreates them from the current models.py, and fills in
fresh demo data — so you don't have to hunt for and delete the .db file by hand.

  ⚠️  STOP THE DEV SERVER FIRST.
      Close any window running `python run.py` (or press Ctrl+C in it),
      otherwise the database file is locked and this can't run.

Run from the cleaning-app folder with your venv active:
      python reset_and_seed.py
"""
from app import create_app
from app.extensions import db

app = create_app()
with app.app_context():
    from app import models  # noqa: F401  (registers every table)
    db.drop_all()
    db.create_all()
    print("Schema rebuilt: all tables dropped and recreated from models.py.")

# Now fill the fresh, correct schema with demo data.
import seed_demo
seed_demo.run()
print("Done — fresh demo data seeded. You can start the app with: python run.py")
