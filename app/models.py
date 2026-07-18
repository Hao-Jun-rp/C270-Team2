"""
DATABASE TABLES (shared file - owned by Marcus / team lead).

A "model" is one table. Every feature links to a user via `user_id`,
and anything about a service links via `service_id`. We NEVER store a
service as free text - always the service_id, so bookings and reviews
can point at the exact same service row.

RULES FOR THE TEAM
  - Only Marcus edits this file. Message him before changing it.
  - Link to a person with:   user_id    -> ForeignKey("user.id")
  - Link to a service with:  service_id -> ForeignKey("service.id")
    (SQLAlchemy names the tables `user` and `service`, lowercase.)
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db, login_manager


# Flask-Login uses this to remember who is logged in between page loads.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============================================================
#  User table  (Marcus)  ->  table name: "user"
# ============================================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    # role decides what a user can do:
    #   "customer" -> normal user (book, review, etc.)  [default]
    #   "admin"    -> can reach /admin: confirm bookings, approve reviews,
    #                 manage services. Set on the seeded admin account.
    role = db.Column(db.String(20), nullable=False, default="customer")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # We never store the raw password - only a scrambled "hash".
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def initials(self):
        """M for 'Marcus', MX for 'Marcus Xue' - used by the navbar avatar."""
        parts = self.name.split()
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][0].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @property
    def display_id(self):
        """Readable label for the UI, e.g. U001. The real id stays an integer."""
        return f"U{self.id:03d}"

    @property
    def is_admin(self):
        """True for admin accounts. Used by @admin_required and the navbar
        (the 'Admin' link only shows when this is True)."""
        return self.role == "admin"


# ============================================================
#  Service table  (Hazirah - listings)  ->  table name: "service"
#  This is the "hub" that bookings and reviews both link to.
# ============================================================
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Float, default=0.0)     # AGGREGATE score shown on cards.
                                                  # Recompute from Review rows when
                                                  # a review is added/approved.
    image = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)  # optional: which admin added it
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def display_id(self):
        return f"S{self.id:03d}"


# ============================================================
#  Booking table  (Ashish - booking)  ->  table name: "booking"
#  CHANGED: `service` (text) is now `service_id` (a real link).
# ============================================================
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("service.id"), nullable=False)
    # Real DATE type (was free text). Real date sorting/filtering + clean
    # "is this in the past" checks. `time` stays a slot LABEL ("09:00–12:00")
    # on purpose — it's a discrete booking slot (a range), not a timestamp.
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    # Agreed status words: Pending / Confirmed / Completed / Cancelled

    # --- Payment (demo only — we never store card numbers/CVV) ---
    # payment_status lifecycle (demo): PayNow/Card -> "Authorized (demo)" at
    # booking, captured to "Paid (demo)" on admin Confirm, "Refunded (demo)" on
    # cancel. Cash -> "Unpaid" until Completed -> "Paid (cash on completion)".
    #   NOTE: must be long enough for the longest of those (25 chars) — MySQL
    #   enforces column length (SQLite silently ignored it), so keep headroom.
    payment_method = db.Column(db.String(20), nullable=True)
    payment_status = db.Column(db.String(40), nullable=False, default="Unpaid")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # These let templates do  booking.service.name  and  booking.user.name
    user = db.relationship("User", backref="bookings")
    service = db.relationship("Service", backref="bookings")

    @property
    def display_id(self):
        return f"B{self.id:03d}"


# ============================================================
#  Review table  (Matthew - reviews)  ->  table name: "review"
#  FIXED: customer_id/"customer" -> user_id/"user" (there is no Customer table).
# ============================================================
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("service.id"), nullable=False)

    rating = db.Column(db.Integer, nullable=False)              # 1..5
    review_title = db.Column(db.String(100), nullable=True)     # optional (form may not collect it)
    review_description = db.Column(db.Text, nullable=False)

    staff_reply = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    # Agreed status words: Pending / Approved / Hidden

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="reviews")
    service = db.relationship("Service", backref="reviews")

    @property
    def display_id(self):
        return f"R{self.id:03d}"


# ============================================================
#  Notification table  (Hao Jun - notifications)  ->  table name: "notification"
#  ADDED: this base table was missing; the NotificationLog FK depended on it.
# ============================================================
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    link = db.Column(db.String(200), nullable=True)   # where clicking it takes you
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="notifications")

    @property
    def display_id(self):
        return f"N{self.id:03d}"


# ------------------------------------------------------------
#  OPTIONAL / ADVANCED (Hao Jun): keep only if you actually need
#  an audit trail of delivery attempts. It links to Notification
#  above, so it now resolves correctly. Delete if not needed.
# ------------------------------------------------------------
# class NotificationLog(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     notification_id = db.Column(db.Integer, db.ForeignKey("notification.id"), nullable=False)
#     event = db.Column(db.String(20), nullable=False)     # created/sent/failed/read/cancelled
#     channel = db.Column(db.String(20), nullable=True)    # in_app/email/sms/push
#     success = db.Column(db.Boolean, nullable=False, default=True)
#     error_message = db.Column(db.String(255), nullable=True)
#     logged_at = db.Column(db.DateTime, default=datetime.utcnow)
#     notification = db.relationship("Notification", backref="logs")