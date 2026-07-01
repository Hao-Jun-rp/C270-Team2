"""
DATABASE TABLES (shared file — owned by Marcus / team lead).
A "model" is one table. The User table is here because almost every
feature connects to a user (bookings, reviews, notifications...).
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
#  User table  (Marcus)
# ============================================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # We never store the raw password — only a scrambled "hash".
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def initials(self):
        """M for 'Marcus', MX for 'Marcus Xue' — used by the navbar avatar."""
        parts = self.name.split()
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][0].upper()
        return (parts[0][0] + parts[-1][0]).upper()


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================================
#  ADD YOUR FEATURE'S TABLES BELOW
#  Message Marcus before editing this file so merges stay clean.
#  Examples to copy (uncomment and edit):
#
#  class Service(db.Model):          # Hazirah - listings
#      id = db.Column(db.Integer, primary_key=True)
#      title = db.Column(db.String(120), nullable=False)
#      price = db.Column(db.Float, nullable=False)
#
#  class Booking(db.Model):          # Ashish - booking
#      id = db.Column(db.Integer, primary_key=True)
#      user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
#      service_id = db.Column(db.Integer, db.ForeignKey("service.id"))
#      date = db.Column(db.DateTime)
# ============================================================
