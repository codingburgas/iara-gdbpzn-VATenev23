from app import db
import datetime


class Firefighter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rank = db.Column(db.String(50))
    status = db.Column(db.String(20), default='available')
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    station_id = db.Column(db.Integer, db.ForeignKey('fire_station.id'), nullable=True)

    # Link to User account
    user_id = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=True, unique=True)
    user = db.relationship('UserModel', foreign_keys=[user_id], backref='firefighter_profile')

    # Shift management
    employee_id = db.Column(db.String(20), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    hire_date = db.Column(db.DateTime, nullable=True)
    last_active = db.Column(db.DateTime, nullable=True)
    current_shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=True)

    # Relationships
    current_shift = db.relationship('Shift', foreign_keys=[current_shift_id], back_populates='firefighter')
    shifts = db.relationship('Shift', foreign_keys='Shift.firefighter_id', back_populates='firefighter')