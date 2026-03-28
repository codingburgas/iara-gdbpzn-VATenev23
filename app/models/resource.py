from app import db
import datetime


class ResourceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)  # water, fuel, equipment, personnel, other
    quantity = db.Column(db.String(100), nullable=True)  # e.g., "5000 liters", "3 firefighters"
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, approved, fulfilled, rejected
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    fulfilled_at = db.Column(db.DateTime, nullable=True)
    fulfilled_by = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    incident = db.relationship('Incident', backref='resource_requests')
    requester = db.relationship('UserModel', foreign_keys=[requester_id], backref='requests_made')
    fulfiller = db.relationship('UserModel', foreign_keys=[fulfilled_by], backref='requests_fulfilled')

    def __repr__(self):
        return f"<ResourceRequest {self.id}: {self.resource_type}>"