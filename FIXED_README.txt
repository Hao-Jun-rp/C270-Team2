Sparkle — full project (admin error fixed + all features)
=========================================================

WHAT WAS BROKEN
  Clicking "Admin" threw an error because the six admin TEMPLATE files
  (app\admin\templates\admin\*.html) had been deleted from your project
  folder. The admin blueprint, routes and models were all fine — but with
  no templates to render, every admin page crashed with "TemplateNotFound".

WHAT I FIXED / RESTORED IN THIS ZIP
  - Restored all 6 admin templates (dashboard, bookings, reviews, services,
    service_form, and the shared status pill).
  - Re-applied the clickable STAR RATING widget on the reviews page (it had
    reverted to the old 5-radio-button "MCQ" version).
  - Kept your cash-on-completion payment fix in app\admin\routes.py.

EVERY FEATURE FROM OUR SESSIONS IS PRESENT AND VERIFIED
  [x] Dashboard reads real data from the database (not mock)
  [x] Recent-activity titles correct ("Booking Received" vs "Confirmed")
  [x] "Upcoming Bookings" shows Pending + Confirmed (future), Next Booking removed
  [x] Cleaner name removed from the calendar's selected-booking card
  [x] Booking payment step (PayNow / Card / Cash) with validation
  [x] Time slots fit each service's real duration
  [x] Past time slots rejected (can't book a slot that already started today)
  [x] Clickable star rating on the reviews page
  [x] Admin area: confirm/complete/cancel bookings, approve/hide reviews
      (+ staff reply, rating recompute), full service CRUD
  [x] Cash bookings become "Paid (cash on completion)" when Completed
  (All Python compiles; all 31 templates parse.)

HOW TO INSTALL (Windows)
  1. Extract this folder OVER your existing cleaning-app folder, replacing
     files when asked. (Your venv\, .git\, instance\ and .env are NOT in this
     zip, so they stay exactly as they are.)
  2. Rebuild the database — the schema includes the admin `role` column:
        - Stop the app.
        - venv\Scripts\activate
        - python reset_and_seed.py      (drops, recreates, reseeds in one go)
  3. python run.py  ->  http://127.0.0.1:5000

  Admin login:  marcus@sparkle.sg  /  password123   (see the teal "Admin" link)
  Customer test: aisha@example.com  /  password123

NOTE ON GIT
  The admin templates were deleted and that deletion was committed. After
  copying these files in, commit them so GitHub gets them too:
        git add app/admin/templates app/reviews/templates/reviews/index.html
        git commit -m "Restore admin templates + clickable star rating"
