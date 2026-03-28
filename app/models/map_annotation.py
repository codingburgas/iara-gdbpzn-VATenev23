from app import db
import datetime


class MapAnnotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=False)
    annotation_type = db.Column(db.String(20), nullable=False)  # fire_front, wind, perimeter, hotspot
    geometry = db.Column(db.Text, nullable=False)  # GeoJSON string
    color = db.Column(db.String(20), default='#ff0000')
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    incident = db.relationship('Incident', backref='annotations')
    user = db.relationship('UserModel', foreign_keys=[user_id])

    def __repr__(self):
        return f"<MapAnnotation {self.id}: {self.annotation_type}>"