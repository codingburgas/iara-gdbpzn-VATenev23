from app import db
import datetime


class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firefighter_id = db.Column(db.Integer, db.ForeignKey('firefighter.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled

    # Relationship
    firefighter = db.relationship('Firefighter', foreign_keys=[firefighter_id], back_populates='shifts')

    def duration(self):
        """Return shift duration in hours"""
        if self.end_time:
            delta = self.end_time - self.start_time
            return round(delta.total_seconds() / 3600, 1)
        return None

    def __repr__(self):
        return f"<Shift {self.id}: {self.firefighter.name} - {self.status}>"