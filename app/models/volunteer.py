from app import db
import datetime


class VolunteerApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    address = db.Column(db.String(200), nullable=True)
    motivation = db.Column(db.Text, nullable=True)
    experience = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')
    applied_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    reviewer = db.relationship('UserModel', foreign_keys=[reviewed_by])


class TrainingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, nullable=False)
    duration_hours = db.Column(db.Integer, default=4)
    location = db.Column(db.String(200), nullable=False)
    max_participants = db.Column(db.Integer, default=20)
    instructor = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='scheduled')
    created_by = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    participants = db.relationship('TrainingParticipant', backref='training_session')
    creator = db.relationship('UserModel', foreign_keys=[created_by])


class TrainingParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(db.Integer, db.ForeignKey('training_session.id'), nullable=False)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteer_application.id'), nullable=True)
    firefighter_id = db.Column(db.Integer, db.ForeignKey('firefighter.id'), nullable=True)
    status = db.Column(db.String(20), default='registered')
    attended_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    volunteer = db.relationship('VolunteerApplication', backref='trainings')
    firefighter = db.relationship('Firefighter', backref='trainings')