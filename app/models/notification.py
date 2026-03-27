from app import db
import datetime


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

    def __repr__(self):
        return f"<Notification {self.id}: {self.title}>"