from app import db
import datetime


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    location = db.Column(db.String(200))

    # GPS Tracking fields
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    speed = db.Column(db.Float, nullable=True)
    heading = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='station')
    current_incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=True)

    # Relationships
    current_incident = db.relationship('Incident', foreign_keys=[current_incident_id])
    firefighters = db.relationship('Firefighter', backref='assigned_vehicle', lazy=True)