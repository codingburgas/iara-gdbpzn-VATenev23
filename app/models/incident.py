from app import db
import datetime


class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    incident_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Reported')
    reported_by = db.Column(db.Integer, db.ForeignKey('user_model.id'))
    reported_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    assigned_vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)

    # Map fields
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # Status tracking
    dispatched_at = db.Column(db.DateTime, nullable=True)
    on_scene_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=True)

    # Relationships
    assigned_vehicle = db.relationship('Vehicle', foreign_keys=[assigned_vehicle_id])
    reporter = db.relationship('UserModel', foreign_keys=[reported_by], backref='reported_incidents')
    updater = db.relationship('UserModel', foreign_keys=[updated_by], backref='updated_incidents')


class StatusUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=False)
    old_status = db.Column(db.String(20), nullable=False)
    new_status = db.Column(db.String(20), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    incident = db.relationship('Incident', backref='status_updates')
    user = db.relationship('UserModel', foreign_keys=[user_id])