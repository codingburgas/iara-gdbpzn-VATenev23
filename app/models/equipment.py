from app import db
import datetime


class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20), default='available')
    condition = db.Column(db.String(20), default='good')
    last_inspected = db.Column(db.DateTime, nullable=True)
    next_inspection = db.Column(db.DateTime, nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    vehicle = db.relationship('Vehicle', backref='equipment_list')


class EquipmentAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=True)
    firefighter_id = db.Column(db.Integer, db.ForeignKey('firefighter.id'), nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    returned_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='assigned')
    notes = db.Column(db.Text, nullable=True)

    equipment = db.relationship('Equipment', backref='assignments')
    incident = db.relationship('Incident', backref='equipment_assignments')
    firefighter = db.relationship('Firefighter', backref='equipment_assignments')