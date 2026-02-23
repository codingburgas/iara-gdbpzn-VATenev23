# models.py
from app import db

class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

class Firefighter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rank = db.Column(db.String(50))
    status = db.Column(db.String(20), default='available')  # available, on_duty, vacation, sick
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    location = db.Column(db.String(200))
    firefighters = db.relationship('Firefighter', backref='vehicle', lazy=True)

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50))  # fire, rescue, hazmat, etc.
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='reported')  # reported, dispatched, on_scene, closed
    reported_at = db.Column(db.DateTime, default=db.func.current_timestamp())