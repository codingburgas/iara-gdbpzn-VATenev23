from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()


# ========== MODELS ==========
class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), default='public')  # public, dispatcher, firefighter, commander


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    location = db.Column(db.String(200))
    firefighters = db.relationship('Firefighter', backref='assigned_vehicle', lazy=True)

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50))  # tool, hose, extinguisher, etc.
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20), default='available')  # available, in_use, maintenance, damaged
    condition = db.Column(db.String(20), default='good')  # good, fair, poor, needs_repair
    last_inspected = db.Column(db.DateTime, nullable=True)
    next_inspection = db.Column(db.DateTime, nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    vehicle = db.relationship('Vehicle', backref='equipment_list')

    def __repr__(self):
        return f"<Equipment {self.name}>"

class EquipmentAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=True)
    firefighter_id = db.Column(db.Integer, db.ForeignKey('firefighter.id'), nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    returned_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='assigned')  # assigned, returned
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    equipment = db.relationship('Equipment', backref='assignments')
    incident = db.relationship('Incident', backref='equipment_assignments')
    firefighter = db.relationship('Firefighter', backref='equipment_assignments')


class Firefighter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rank = db.Column(db.String(50))
    status = db.Column(db.String(20), default='available')
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)

    # NEW: Link to User account
    user_id = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=True, unique=True)
    user = db.relationship('UserModel', foreign_keys=[user_id], backref='firefighter_profile')

    # Shift management fields
    employee_id = db.Column(db.String(20), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    hire_date = db.Column(db.DateTime, nullable=True)
    last_active = db.Column(db.DateTime, nullable=True)
    current_shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=True)

    # Relationships
    current_shift = db.relationship('Shift', foreign_keys=[current_shift_id], back_populates='firefighter')
    shifts = db.relationship('Shift', foreign_keys='Shift.firefighter_id', back_populates='firefighter')


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
    assigned_vehicle = db.relationship('Vehicle')

    # Map fields
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # Status tracking fields
    dispatched_at = db.Column(db.DateTime, nullable=True)
    on_scene_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=True)

    # Relationships
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

    # Relationships
    incident = db.relationship('Incident', backref='status_updates')
    user = db.relationship('UserModel', foreign_keys=[user_id])


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = db.relationship('UserModel', foreign_keys=[user_id])
    incident = db.relationship('Incident', foreign_keys=[incident_id])


class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firefighter_id = db.Column(db.Integer, db.ForeignKey('firefighter.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled

    # Relationship
    firefighter = db.relationship('Firefighter', foreign_keys=[firefighter_id], back_populates='shifts')

    def duration(self):
        """Return shift duration in hours"""
        if self.end_time:
            delta = self.end_time - self.start_time
            return round(delta.total_seconds() / 3600, 1)
        return None