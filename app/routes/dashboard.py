from flask import Blueprint, render_template, session, redirect, url_for
from app import db
from app.models.incident import Incident
from app.models.user import UserModel
from app.models.vehicle import Vehicle
from app.models.firefighter import Firefighter
from app.utils import login_required, role_required
import datetime
from sqlalchemy import extract

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/staff/dashboard')
@login_required
def staff_dashboard():
    return render_template('staff/dashboard/staff.html')


@dashboard_bp.route('/dashboard')
@login_required
def dynamic_dashboard():
    """Redirect to the appropriate dashboard based on user role"""
    user_role = session.get('user_role')

    if user_role == 'dispatcher':
        return redirect(url_for('dashboard.dispatcher_dashboard'))
    elif user_role == 'firefighter':
        return redirect(url_for('dashboard.firefighter_dashboard'))
    elif user_role == 'commander':
        return redirect(url_for('dashboard.commander_dashboard'))
    else:
        return redirect(url_for('dashboard.staff_dashboard'))


@dashboard_bp.route('/dispatcher/dashboard')
@login_required
@role_required('dispatcher', 'commander')
def dispatcher_dashboard():
    active_incidents = Incident.query.filter(Incident.status != 'Closed').count()
    available_vehicles = Vehicle.query.count()
    total_firefighters = Firefighter.query.count()
    recent_incidents = Incident.query.order_by(Incident.reported_at.desc()).limit(5).all()

    return render_template('staff/dashboard/dispatcher.html',
                           active_incidents=active_incidents,
                           available_vehicles=available_vehicles,
                           total_firefighters=total_firefighters,
                           recent_incidents=recent_incidents)


@dashboard_bp.route('/firefighter/dashboard')
@login_required
@role_required('firefighter', 'commander')
def firefighter_dashboard():
    from app.models.task import Task

    # Find firefighter by user_id (better than by name)
    firefighter = Firefighter.query.filter_by(user_id=session.get('user_id')).first()

    # If not found by user_id, try by name (fallback)
    if not firefighter:
        firefighter = Firefighter.query.filter_by(name=session.get('user_name')).first()

    my_incidents = []
    my_tasks = []

    if firefighter:
        # Get incidents assigned to this firefighter's vehicle
        if firefighter.vehicle_id:
            my_incidents = Incident.query.filter_by(assigned_vehicle_id=firefighter.vehicle_id).all()
        # Get tasks assigned to this firefighter
        my_tasks = Task.query.filter_by(
            assigned_to=firefighter.id,
            status='pending'
        ).order_by(Task.priority.desc(), Task.deadline).all()

        print(f"Firefighter found: {firefighter.name}, vehicle: {firefighter.vehicle_id}")
    else:
        print(f"No firefighter found for user: {session.get('user_name')} (ID: {session.get('user_id')})")

    return render_template('staff/dashboard/firefighter.html',
                           incidents=my_incidents,
                           firefighter=firefighter,
                           tasks=my_tasks)

@dashboard_bp.route('/commander/dashboard')
@login_required
@role_required('commander')
def commander_dashboard():
    fire_count = Incident.query.filter_by(incident_type='fire').count()
    rescue_count = Incident.query.filter_by(incident_type='rescue').count()
    accident_count = Incident.query.filter_by(incident_type='accident').count()
    hazmat_count = Incident.query.filter_by(incident_type='hazmat').count()
    other_count = Incident.query.filter_by(incident_type='other').count()

    months = []
    monthly_counts = []

    for i in range(5, -1, -1):
        date = datetime.datetime.now() - datetime.timedelta(days=30 * i)
        month_name = date.strftime('%b')
        months.append(month_name)

        count = Incident.query.filter(
            extract('month', Incident.reported_at) == date.month,
            extract('year', Incident.reported_at) == date.year
        ).count()
        monthly_counts.append(count)

    units_in_field = Incident.query.filter(Incident.status.in_(['Dispatched', 'On Scene'])).count()
    last_incident = Incident.query.order_by(Incident.reported_at.desc()).first()
    last_incident_time = last_incident.reported_at.strftime('%H:%M %d/%m') if last_incident else 'No incidents'

    stats = {
        'total_incidents': Incident.query.count(),
        'active_incidents': Incident.query.filter(Incident.status != 'Closed').count(),
        'available_firefighters': Firefighter.query.filter_by(status='available').count(),
        'total_vehicles': Vehicle.query.count(),
        'total_users': UserModel.query.count(),
        'fire_count': fire_count,
        'rescue_count': rescue_count,
        'accident_count': accident_count,
        'hazmat_count': hazmat_count,
        'other_count': other_count,
        'months': months,
        'monthly_counts': monthly_counts,
        'units_in_field': units_in_field,
        'last_incident_time': last_incident_time
    }

    return render_template('staff/dashboard/commander.html', stats=stats)