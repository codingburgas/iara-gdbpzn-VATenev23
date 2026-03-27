from flask import Blueprint, render_template
from app.models.incident import Incident
from app.models.vehicle import Vehicle
from app.utils import login_required, role_required

map_bp = Blueprint('map', __name__)


@map_bp.route('/staff/map')
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def incident_map():
    incidents = Incident.query.filter(Incident.status != 'Closed').all()
    vehicles = Vehicle.query.all()

    return render_template('staff/map/incidents.html',
                           incidents=incidents,
                           vehicles=vehicles)