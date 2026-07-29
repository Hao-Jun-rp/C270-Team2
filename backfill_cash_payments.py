"""
One-off data fix: mark PAST completed CASH bookings as paid.

Why this exists: the app only started flipping Cash bookings to "paid" when
they're marked Completed AFTER that feature was added. Any booking that was
already Completed before then (including seeded demo data) is still stuck on
"Unpaid" even though the cash was collected. This script corrects those
existing rows in place — no full reseed, nothing else touched.

Safe to run more than once (it only touches rows that still need fixing).

  Stop the dev server first, then from the cleaning-app folder:
      python backfill_cash_payments.py
"""
from app import create_app
from app.extensions import db
from app.models import Booking

app = create_app()
with app.app_context():
    stuck = (Booking.query
             .filter_by(status="Completed", payment_method="Cash",
                        payment_status="Unpaid")
             .all())
    for b in stuck:
        b.payment_status = "Paid (cash on completion)"
    db.session.commit()
    print(f"Updated {len(stuck)} completed cash booking(s) to paid.")
    for b in stuck:
        print(f"  {b.display_id}: {b.service.name} on {b.date} -> {b.payment_status}")
