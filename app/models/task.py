from app import db
import datetime


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('firefighter.id'), nullable=True)
    assigned_to_vehicle = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, cancelled
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    deadline = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    incident = db.relationship('Incident', backref='tasks')
    assignee = db.relationship('Firefighter', foreign_keys=[assigned_to], backref='assigned_tasks')
    assignee_vehicle = db.relationship('Vehicle', foreign_keys=[assigned_to_vehicle])
    creator = db.relationship('UserModel', foreign_keys=[created_by], backref='created_tasks')
    completer = db.relationship('UserModel', foreign_keys=[completed_by], backref='completed_tasks')

    def __repr__(self):
        return f"<Task {self.id}: {self.title}>"