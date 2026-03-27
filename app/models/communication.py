from app import db
import datetime


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='chat')
    is_emergency = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    incident = db.relationship('Incident', backref='messages')
    user = db.relationship('UserModel', foreign_keys=[user_id])


class MessageTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), default='general')
    order = db.Column(db.Integer, default=0)


class SOSAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firefighter_id = db.Column(db.Integer, db.ForeignKey('firefighter.id'), nullable=False)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, resolved, cancelled
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=True)

    # Relationships
    firefighter = db.relationship('Firefighter', foreign_keys=[firefighter_id])
    incident = db.relationship('Incident', foreign_keys=[incident_id])
    resolver = db.relationship('UserModel', foreign_keys=[resolved_by])

    def __repr__(self):
        return f"<SOSAlert {self.id}: {self.firefighter.name}>"