from app import db
import datetime

class FireStation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    
    # Capacity management
    max_vehicles = db.Column(db.Integer, default=5)
    max_personnel = db.Column(db.Integer, default=20)
    
    # Location for mapping
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    vehicles = db.relationship('Vehicle', backref='station', lazy=True)
    personnel = db.relationship('Firefighter', backref='station', lazy=True)

    def __repr__(self):
        return f'<FireStation {self.name}>'
