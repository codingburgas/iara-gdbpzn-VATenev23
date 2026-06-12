from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models.firefighter import Firefighter
from app.models.vehicle import Vehicle
from app.models.user import UserModel
from app.models.shift import Shift
from app.models.incident import Incident
from app.utils import (login_required, role_required, create_notification,
                       start_vehicle_route, _set_crew_status)
import datetime

firefighters_bp = Blueprint('personnel', __name__)


# ========== PERFORMANCE SCORE (Module 17) ==========
def compute_performance(firefighter, days=30):
    """Score a firefighter from existing operational data — no extra tables.

    Points: +10 per incident their unit responded to, +5 per completed task
    (+2 on-time bonus, -2 late), -3 per overdue pending task, +1 per shift
    hour in the window (capped at 40), -5 per SOS alert they raised."""
    from app.models.task import Task
    from app.models.communication import SOSAlert

    now = datetime.datetime.utcnow()
    window_start = now - datetime.timedelta(days=days)

    # Incidents the firefighter's unit was dispatched to.
    incidents_responded = 0
    if firefighter.vehicle_id:
        incidents_responded = Incident.query.filter(
            Incident.assigned_vehicle_id == firefighter.vehicle_id,
            Incident.dispatched_at.isnot(None)
        ).count()

    # Tasks
    completed_tasks = Task.query.filter_by(assigned_to=firefighter.id, status='completed').all()
    on_time = sum(1 for t in completed_tasks
                  if t.deadline and t.completed_at and t.completed_at <= t.deadline)
    late = sum(1 for t in completed_tasks
               if t.deadline and t.completed_at and t.completed_at > t.deadline)
    overdue_pending = Task.query.filter(
        Task.assigned_to == firefighter.id,
        Task.status.in_(['pending', 'in_progress']),
        Task.deadline.isnot(None),
        Task.deadline < now
    ).count()

    # Shift hours inside the window
    shift_hours = 0.0
    for s in firefighter.shifts:
        if s.end_time and s.start_time >= window_start:
            shift_hours += (s.end_time - s.start_time).total_seconds() / 3600
    shift_hours = round(min(shift_hours, 40.0), 1)

    sos_count = SOSAlert.query.filter_by(firefighter_id=firefighter.id).count()

    score = (incidents_responded * 10
             + len(completed_tasks) * 5 + on_time * 2 - late * 2
             - overdue_pending * 3
             + int(shift_hours)
             - sos_count * 5)

    if score >= 80:
        band, band_class = 'Elite', 'success'
    elif score >= 50:
        band, band_class = 'Strong', 'primary'
    elif score >= 20:
        band, band_class = 'Developing', 'warning'
    else:
        band, band_class = 'Building', 'secondary'

    return {
        'score': score,
        'band': band,
        'band_class': band_class,
        'incidents': incidents_responded,
        'tasks_done': len(completed_tasks),
        'on_time': on_time,
        'late': late,
        'overdue': overdue_pending,
        'shift_hours': shift_hours,
        'sos': sos_count,
    }


@firefighters_bp.route('/staff/performance')
@login_required
@role_required('commander')
def performance_leaderboard():
    """Commander leaderboard ranking firefighters by operational performance."""
    days = request.args.get('days', 30, type=int)
    rows = []
    for f in Firefighter.query.all():
        perf = compute_performance(f, days=days)
        rows.append({'firefighter': f, 'perf': perf})
    rows.sort(key=lambda r: r['perf']['score'], reverse=True)

    return render_template('staff/personnel/performance.html', rows=rows, days=days)


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


@firefighters_bp.route('/staff/firefighter/my-status', methods=['POST'])
@login_required
@role_required('firefighter', 'commander')
def update_my_status():
    """Firefighter updates their own availability status from their dashboard."""
    firefighter = Firefighter.query.filter_by(user_id=session.get('user_id')).first()
    if not firefighter:
        return jsonify({'success': False, 'error': 'Firefighter profile not found'}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get('status')

    allowed = {'available', 'on_break', 'on_duty', 'off_duty'}
    if new_status not in allowed:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    firefighter.status = new_status
    db.session.commit()
    return jsonify({'success': True, 'status': new_status})


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


@firefighters_bp.route('/staff/vehicle/<int:vehicle_id>/assign-incident/<int:incident_id>', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def assign_vehicle_to_incident(vehicle_id, incident_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    incident = Incident.query.get_or_404(incident_id)

    vehicle.current_incident_id = incident.id

    # Start a live road route if we know where the incident is.
    if incident.latitude is not None and incident.longitude is not None:
        start_vehicle_route(vehicle, incident.latitude, incident.longitude)
    else:
        vehicle.status = 'en_route'
        _set_crew_status(vehicle, 'on_duty')

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