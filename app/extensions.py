"""
The shared tools, created once here so every feature uses the SAME ones.
  db            -> talks to the database
  login_manager -> handles "who is logged in"
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
