from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models.firefighter import Firefighter
from app.models.vehicle import Vehicle
from app.models.user import UserModel
from app.models.shift import Shift
from app.models.incident import Incident
from app.utils import login_required, role_required, create_notification
import datetime
from math import radians, sin, cos, sqrt, atan2

firefighters_bp = Blueprint('personnel', __name__)


@firefighters_bp.route('/staff/firefighters')
@login_required
@role_required('dispatcher', 'commander')
def list_firefighters():
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    vehicle_filter = request.args.get('vehicle', '')

    ff_query = Firefighter.query

    if search_query:
        ff_query = ff_query.filter(
            db.or_(
                Firefighter.name.ilike(f'%{search_query}%'),
                Firefighter.rank.ilike(f'%{search_query}%')
            )
        )

    if status_filter:
        ff_query = ff_query.filter(Firefighter.status == status_filter)

    if vehicle_filter:
        if vehicle_filter == 'unassigned':
            ff_query = ff_query.filter(Firefighter.vehicle_id.is_(None))
        else:
            ff_query = ff_query.filter(Firefighter.vehicle_id == vehicle_filter)

    all_firefighters = ff_query.all()

    v_query = Vehicle.query
    if search_query:
        v_query = v_query.filter(
            db.or_(
                Vehicle.type.ilike(f'%{search_query}%'),
                Vehicle.location.ilike(f'%{search_query}%')
            )
        )

    all_vehicles = v_query.all()
    all_statuses = ['available', 'on_duty', 'off_duty', 'training', 'sick', 'vacation']

    return render_template('staff/personnel/firefighters.html',
                           firefighters=all_firefighters,
                           vehicles=all_vehicles,
                           all_statuses=all_statuses,
                           search_query=search_query,
                           status_filter=status_filter,
                           vehicle_filter=vehicle_filter)


@firefighters_bp.route('/staff/firefighter/<int:firefighter_id>/assign', methods=['GET', 'POST'])
@login_required
@role_required('commander', 'dispatcher')
def assign_firefighter(firefighter_id):
    firefighter = Firefighter.query.get_or_404(firefighter_id)
    vehicles = Vehicle.query.all()

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        if vehicle_id:
            firefighter.vehicle_id = vehicle_id
            db.session.commit()
            flash(f'{firefighter.name} assigned to vehicle successfully!', 'success')
        else:
            firefighter.vehicle_id = None
            db.session.commit()
            flash(f'{firefighter.name} unassigned from vehicle.', 'info')

        return redirect(url_for('personnel.list_firefighters'))

    return render_template('staff/personnel/assign_firefighter.html',
                           firefighter=firefighter,
                           vehicles=vehicles)


@firefighters_bp.route('/staff/shifts')
@login_required
@role_required('dispatcher', 'commander')
def shift_management():
    active_shifts = Shift.query.filter_by(status='active').all()
    today = datetime.datetime.now().date()
    today_shifts = Shift.query.filter(
        db.func.date(Shift.start_time) == today
    ).order_by(Shift.start_time.desc()).all()

    available_firefighters = Firefighter.query.filter_by(status='available').all()

    return render_template('staff/personnel/shifts.html',
                           active_shifts=active_shifts,
                           today_shifts=today_shifts,
                           available_firefighters=available_firefighters,
                           datetime=datetime)


@firefighters_bp.route('/staff/shifts/start', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def start_shift():
    firefighter_id = request.form.get('firefighter_id')
    firefighter = Firefighter.query.get(firefighter_id)

    if not firefighter:
        flash('Firefighter not found', 'danger')
        return redirect(url_for('personnel.shift_management'))

    active_shift = Shift.query.filter_by(
        firefighter_id=firefighter_id,
        status='active'
    ).first()

    if active_shift:
        active_shift.status = 'completed'
        active_shift.end_time = datetime.datetime.utcnow()

    new_shift = Shift(
        firefighter_id=firefighter_id,
        start_time=datetime.datetime.utcnow(),
        status='active'
    )
    db.session.add(new_shift)

    firefighter.status = 'on_duty'
    firefighter.current_shift_id = new_shift.id
    firefighter.last_active = datetime.datetime.utcnow()

    db.session.commit()

    flash(f'Shift started for {firefighter.name}', 'success')
    return redirect(url_for('personnel.shift_management'))


@firefighters_bp.route('/staff/shifts/end/<int:shift_id>', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def end_shift(shift_id):
    shift = Shift.query.get_or_404(shift_id)

    if shift.status != 'active':
        flash('Shift is already ended', 'warning')
        return redirect(url_for('personnel.shift_management'))

    shift.status = 'completed'
    shift.end_time = datetime.datetime.utcnow()

    if shift.firefighter:
        shift.firefighter.status = 'available'
        shift.firefighter.current_shift_id = None

    db.session.commit()

    flash(f'Shift ended for {shift.firefighter.name}', 'success')
    return redirect(url_for('personnel.shift_management'))


@firefighters_bp.route('/staff/firefighter/<int:firefighter_id>/status', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def update_firefighter_status(firefighter_id):
    firefighter = Firefighter.query.get_or_404(firefighter_id)
    new_status = request.form.get('status')

    if new_status:
        firefighter.status = new_status
        db.session.commit()
        flash(f'{firefighter.name} status updated to {new_status}', 'success')

    return redirect(url_for('personnel.shift_management'))


@firefighters_bp.route('/staff/import-data')
@login_required
@role_required('dispatcher', 'commander')
def import_data():
    try:
        from data import firefighters, vehicles

        Firefighter.query.delete()
        Vehicle.query.delete()

        for v in vehicles:
            vehicle = Vehicle(
                id=v['id'],
                type=v['type'],
                location=v['location'],
                latitude=v.get('latitude'),
                longitude=v.get('longitude'),
                status=v.get('status', 'station')
            )
            db.session.add(vehicle)

        db.session.commit()

        for f in firefighters:
            firefighter = Firefighter(
                id=f['id'],
                name=f['name'],
                rank=f['rank'],
                status=f['status'],
                vehicle_id=f['vehicle_id']
            )
            db.session.add(firefighter)

        db.session.commit()

        flash(f'Successfully imported {len(vehicles)} vehicles and {len(firefighters)} firefighters!', 'success')

    except Exception as e:
        flash(f'Error importing data: {str(e)}', 'danger')
        print(f"Error: {e}")

    return redirect(url_for('personnel.list_firefighters'))


@firefighters_bp.route('/staff/vehicle-tracking')
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def vehicle_tracking():
    vehicles = Vehicle.query.all()
    incidents = Incident.query.filter(Incident.status != 'Closed').all()

    return render_template('staff/personnel/vehicle_tracking.html',
                           vehicles=vehicles,
                           incidents=incidents)


@firefighters_bp.route('/staff/vehicle/<int:vehicle_id>/update-location', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def update_vehicle_location(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    data = request.get_json()

    if 'latitude' in data and 'longitude' in data:
        vehicle.latitude = data['latitude']
        vehicle.longitude = data['longitude']
        vehicle.last_updated = datetime.datetime.utcnow()

        if 'status' in data:
            vehicle.status = data['status']

        db.session.commit()

        return {'success': True, 'message': f'{vehicle.type} location updated'}

    return {'error': 'Missing coordinates'}, 400


@firefighters_bp.route('/staff/vehicle/<int:vehicle_id>/assign-incident/<int:incident_id>', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def assign_vehicle_to_incident(vehicle_id, incident_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    incident = Incident.query.get_or_404(incident_id)

    vehicle.status = 'en_route'
    vehicle.current_incident_id = incident.id

    if not incident.assigned_vehicle_id:
        incident.assigned_vehicle_id = vehicle.id

    db.session.commit()

    flash(f'{vehicle.type} dispatched to {incident.title}', 'success')

    for firefighter in vehicle.firefighters:
        user = UserModel.query.filter_by(username=firefighter.name).first()
        if user:
            create_notification(
                user_id=user.id,
                title=f'Dispatch Alert',
                message=f'Your unit has been dispatched to {incident.title}',
                incident_id=incident.id
            )

    return redirect(url_for('incidents.detail', incident_id=incident_id))


@firefighters_bp.route('/staff/vehicle/<int:vehicle_id>/eta/<int:incident_id>')
@login_required
def calculate_eta(vehicle_id, incident_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    incident = Incident.query.get_or_404(incident_id)

    if not vehicle.latitude or not vehicle.longitude or not incident.latitude or not incident.longitude:
        return {'eta': 'N/A', 'error': 'Missing coordinates'}

    R = 6371

    lat1 = radians(vehicle.latitude)
    lon1 = radians(vehicle.longitude)
    lat2 = radians(incident.latitude)
    lon2 = radians(incident.longitude)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    speed = vehicle.speed or 60
    eta_minutes = (distance / speed) * 60

    return {
        'distance': round(distance, 1),
        'eta_minutes': round(eta_minutes, 1),
        'eta_text': f"{int(eta_minutes)} min" if eta_minutes < 60 else f"{int(eta_minutes / 60)}h {int(eta_minutes % 60)}min"
    }