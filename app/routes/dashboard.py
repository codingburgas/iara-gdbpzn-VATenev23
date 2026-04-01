from flask import Blueprint, render_template, session, redirect, url_for, request
from app import db
from app.models.incident import Incident
from app.models.user import UserModel
from app.models.vehicle import Vehicle
from app.models.firefighter import Firefighter
from app.utils import login_required, role_required, get_weather
import datetime
from sqlalchemy import extract, func

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
    # Burgas, Bulgaria coordinates
    weather = get_weather(42.5048, 27.4626)

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

    return render_template('staff/dashboard/commander.html', stats=stats, weather=weather)


# ========== ANALYTICS ROUTES ==========
@dashboard_bp.route('/commander/analytics')
@login_required
@role_required('commander')
def analytics_dashboard():
    """Advanced analytics dashboard for commanders"""
    from app.models.task import Task
    from app.models.resource import ResourceRequest

    # Get date range from query params (default last 30 days)
    days = request.args.get('days', 30, type=int)
    date_from = datetime.datetime.now() - datetime.timedelta(days=days)

    # ========== INCIDENT STATISTICS ==========
    total_incidents = Incident.query.count()
    active_incidents = Incident.query.filter(Incident.status != 'Closed').count()
    closed_incidents = Incident.query.filter_by(status='Closed').count()

    # Incidents by type - create simple lists directly
    type_labels = []
    type_values = []
    incidents_by_type_query = db.session.query(
        Incident.incident_type,
        func.count(Incident.id)
    ).filter(Incident.reported_at >= date_from).group_by(Incident.incident_type).all()

    for item in incidents_by_type_query:
        type_labels.append(item[0])
        type_values.append(item[1])

    # Incidents by status - create simple lists directly
    status_labels = []
    status_values = []
    incidents_by_status_query = db.session.query(
        Incident.status,
        func.count(Incident.id)
    ).group_by(Incident.status).all()

    for item in incidents_by_status_query:
        status_labels.append(item[0])
        status_values.append(item[1])

    # Daily incidents
    daily_incidents = []
    for i in range(days, -1, -1):
        date = datetime.datetime.now() - datetime.timedelta(days=i)
        count = Incident.query.filter(
            func.date(Incident.reported_at) == date.date()
        ).count()
        daily_incidents.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })

    # Monthly incidents
    monthly_incidents = []
    for i in range(11, -1, -1):
        date = datetime.datetime.now() - datetime.timedelta(days=30 * i)
        count = Incident.query.filter(
            extract('year', Incident.reported_at) == date.year,
            extract('month', Incident.reported_at) == date.month
        ).count()
        monthly_incidents.append({
            'month': date.strftime('%b %Y'),
            'count': count
        })

    # ========== RESPONSE TIME STATISTICS ==========
    incidents_with_dispatch = Incident.query.filter(
        Incident.dispatched_at.isnot(None),
        Incident.reported_at.isnot(None)
    ).all()

    response_times = []
    for inc in incidents_with_dispatch:
        diff = inc.dispatched_at - inc.reported_at
        response_times.append(diff.total_seconds() / 60)

    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    max_response_time = max(response_times) if response_times else 0
    min_response_time = min(response_times) if response_times else 0

    # Response time by incident type
    response_by_type = []
    for type_name in ['fire', 'rescue', 'accident', 'hazmat', 'other']:
        type_incidents = [inc for inc in incidents_with_dispatch if inc.incident_type == type_name]
        if type_incidents:
            avg = sum([(inc.dispatched_at - inc.reported_at).total_seconds() / 60 for inc in type_incidents]) / len(
                type_incidents)
            response_by_type.append({'type': type_name, 'avg_time': round(avg, 1)})

    # ========== TASK STATISTICS ==========
    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status='completed').count()
    pending_tasks = Task.query.filter(Task.status.in_(['pending', 'in_progress'])).count()
    task_completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Tasks by priority - create simple lists
    task_priority_labels = []
    task_priority_values = []
    tasks_by_priority_query = db.session.query(
        Task.priority,
        func.count(Task.id)
    ).group_by(Task.priority).all()

    for item in tasks_by_priority_query:
        task_priority_labels.append(item[0])
        task_priority_values.append(item[1])

    # ========== RESOURCE STATISTICS ==========
    total_requests = ResourceRequest.query.count()
    fulfilled_requests = ResourceRequest.query.filter_by(status='fulfilled').count()
    pending_requests = ResourceRequest.query.filter_by(status='pending').count()
    request_fulfillment_rate = (fulfilled_requests / total_requests * 100) if total_requests > 0 else 0

    # Requests by type - create simple lists
    request_type_labels = []
    request_type_values = []
    requests_by_type_query = db.session.query(
        ResourceRequest.resource_type,
        func.count(ResourceRequest.id)
    ).group_by(ResourceRequest.resource_type).all()

    for item in requests_by_type_query:
        request_type_labels.append(item[0])
        request_type_values.append(item[1])

    # ========== PERSONNEL STATISTICS ==========
    from app.models.firefighter import Firefighter
    total_firefighters = Firefighter.query.count()
    available_firefighters = Firefighter.query.filter_by(status='available').count()
    on_duty_firefighters = Firefighter.query.filter_by(status='on_duty').count()

    # ========== VEHICLE STATISTICS ==========
    from app.models.vehicle import Vehicle
    total_vehicles = Vehicle.query.count()
    available_vehicles = Vehicle.query.filter_by(status='station').count()
    en_route_vehicles = Vehicle.query.filter_by(status='en_route').count()
    on_scene_vehicles = Vehicle.query.filter_by(status='on_scene').count()

    # ========== USER STATISTICS ==========
    from app.models.user import UserModel
    total_users = UserModel.query.count()
    user_role_labels = []
    user_role_values = []
    users_by_role_query = db.session.query(
        UserModel.role,
        func.count(UserModel.id)
    ).group_by(UserModel.role).all()

    for item in users_by_role_query:
        user_role_labels.append(item[0])
        user_role_values.append(item[1])

    # ========== RESPONSE TIME TREND (last 7 days) ==========
    response_trend = []
    for i in range(6, -1, -1):
        date = datetime.datetime.now() - datetime.timedelta(days=i)
        day_incidents = Incident.query.filter(
            func.date(Incident.reported_at) == date.date()
        ).all()
        day_response_times = []
        for inc in day_incidents:
            if inc.dispatched_at:
                diff = inc.dispatched_at - inc.reported_at
                day_response_times.append(diff.total_seconds() / 60)
        avg = sum(day_response_times) / len(day_response_times) if day_response_times else 0
        response_trend.append({
            'date': date.strftime('%a'),
            'avg_time': round(avg, 1)
        })

    # Prepare data for charts as simple lists
    chart_data = {
        'incident_type_labels': type_labels,
        'incident_type_values': type_values,
        'incident_status_labels': status_labels,
        'incident_status_values': status_values,
        'daily_incidents': daily_incidents,
        'monthly_incidents': monthly_incidents,
        'task_priority_labels': task_priority_labels,
        'task_priority_values': task_priority_values,
        'request_type_labels': request_type_labels,
        'request_type_values': request_type_values,
        'response_by_type': response_by_type,
        'response_trend': response_trend,
        'user_role_labels': user_role_labels,
        'user_role_values': user_role_values
    }

    stats = {
        'total_incidents': total_incidents,
        'active_incidents': active_incidents,
        'closed_incidents': closed_incidents,
        'avg_response_time': round(avg_response_time, 1),
        'max_response_time': round(max_response_time, 1),
        'min_response_time': round(min_response_time, 1),
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'task_completion_rate': round(task_completion_rate, 1),
        'total_requests': total_requests,
        'fulfilled_requests': fulfilled_requests,
        'pending_requests': pending_requests,
        'request_fulfillment_rate': round(request_fulfillment_rate, 1),
        'total_firefighters': total_firefighters,
        'available_firefighters': available_firefighters,
        'on_duty_firefighters': on_duty_firefighters,
        'total_vehicles': total_vehicles,
        'available_vehicles': available_vehicles,
        'en_route_vehicles': en_route_vehicles,
        'on_scene_vehicles': on_scene_vehicles,
        'total_users': total_users
    }

    return render_template('staff/dashboard/analytics.html',
                           stats=stats,
                           chart_data=chart_data,
                           days=days)