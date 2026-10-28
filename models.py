from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='hotel')
    hotel_id = db.Column(db.String(50), nullable=True)


class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    photo_url = db.Column(db.String(256), nullable=True)
    last_meal_at = db.Column(db.DateTime, nullable=True)


class Redemption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(36), unique=True, nullable=False)
    child_uuid = db.Column(db.String(36), db.ForeignKey('child.uuid'), nullable=False)
    hotel_id = db.Column(db.String(50), nullable=False)
    scanned_at = db.Column(db.DateTime, nullable=False)
    conflict = db.Column(db.Boolean, default=False)