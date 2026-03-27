from app.models.user import UserModel
from app.models.vehicle import Vehicle
from app.models.firefighter import Firefighter
from app.models.incident import Incident, StatusUpdate
from app.models.notification import Notification
from app.models.shift import Shift
from app.models.equipment import Equipment, EquipmentAssignment
from app.models.communication import Message, MessageTemplate
from app.models.volunteer import VolunteerApplication, TrainingSession, TrainingParticipant
from app import db

__all__ = [
    'db', 'UserModel', 'Vehicle', 'Firefighter', 'Incident',
    'StatusUpdate', 'Notification', 'Shift', 'Equipment',
    'EquipmentAssignment', 'Message', 'MessageTemplate',
    'VolunteerApplication', 'TrainingSession', 'TrainingParticipant'
]