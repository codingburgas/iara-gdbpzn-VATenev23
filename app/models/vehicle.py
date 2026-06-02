from app import db
import datetime


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    location = db.Column(db.String(200))

    # GPS Tracking fields
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    speed = db.Column(db.Float, nullable=True)
    heading = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='station')
    station_id = db.Column(db.Integer, db.ForeignKey('fire_station.id'), nullable=True)
    current_incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=True)

    # Live route tracking (set when the vehicle is dispatched to an incident)
    route_polyline = db.Column(db.Text, nullable=True)      # JSON list of [lat, lng] along the road
    route_started_at = db.Column(db.DateTime, nullable=True)  # when the vehicle began driving
    route_total_seconds = db.Column(db.Float, nullable=True)  # animation duration (sped up for demo)
    route_real_seconds = db.Column(db.Float, nullable=True)   # real OSRM driving time, for ETA display
    route_distance_m = db.Column(db.Float, nullable=True)     # real route distance in meters
    route_dest_lat = db.Column(db.Float, nullable=True)
    route_dest_lng = db.Column(db.Float, nullable=True)

    # Relationships
    current_incident = db.relationship('Incident', foreign_keys=[current_incident_id])
    firefighters = db.relationship('Firefighter', backref='assigned_vehicle', lazy=True)