from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, Response
from app import db
from app.models.incident import Incident, StatusUpdate
from app.models.vehicle import Vehicle
from app.models.user import UserModel
from app.models.firefighter import Firefighter
from app.models.communication import Message, SOSAlert
from app.forms.incident_forms import IncidentForm, StatusUpdateForm
from app.utils import (login_required, role_required, create_notification, generate_incident_pdf,
                       get_weather, geocode_address, start_vehicle_route, release_incident_units)
import datetime
import csv
from io import StringIO

incidents_bp = Blueprint('incidents', __name__)


def build_incident_timeline(incident):
    """Merge every recorded event on an incident into one chronological feed.

    Sources: the report itself, StatusUpdate rows, silent milestones (e.g.
    auto-dispatch at report time writes timestamps but no StatusUpdate),
    tasks, radio traffic, emergency messages and SOS alerts.
    """
    events = []

    def add(ts, icon, tone, title, body=None, actor=None):
        if ts:
            events.append({'ts': ts, 'icon': icon, 'tone': tone,
                           'title': title, 'body': body, 'actor': actor})

    add(incident.reported_at, 'fa-bullhorn', 'reported', 'Incident reported',
        incident.description,
        incident.reporter.username if incident.reporter else None)

    updates = StatusUpdate.query.filter_by(incident_id=incident.id).all()
    logged_statuses = {u.new_status for u in updates}
    status_style = {
        'Reported':   ('fa-bullhorn', 'reported'),
        'Dispatched': ('fa-truck-fast', 'dispatched'),
        'On Scene':   ('fa-fire', 'onscene'),
        'Contained':  ('fa-shield-halved', 'success'),
        'Closed':     ('fa-flag-checkered', 'closed'),
    }
    for u in updates:
        icon, tone = status_style.get(u.new_status, ('fa-pen', 'closed'))
        add(u.timestamp, icon, tone,
            f'Status changed: {u.old_status} → {u.new_status}',
            u.comment, u.user.username if u.user else 'System')

    if incident.dispatched_at and 'Dispatched' not in logged_statuses:
        unit = incident.assigned_vehicle.type if incident.assigned_vehicle else 'Unit'
        add(incident.dispatched_at, 'fa-truck-fast', 'dispatched',
            f'{unit} dispatched', 'Unit routed to the incident location', 'System')
    if incident.on_scene_at and 'On Scene' not in logged_statuses:
        add(incident.on_scene_at, 'fa-fire', 'onscene', 'Units arrived on scene',
            None, 'System')
    if incident.closed_at and 'Closed' not in logged_statuses:
        add(incident.closed_at, 'fa-flag-checkered', 'closed', 'Incident closed',
            None, 'System')

    for t in incident.tasks:
        add(t.created_at, 'fa-list-check', 'dispatched',
            f'Task created: {t.title}', t.description,
            t.creator.username if t.creator else None)
        if t.completed_at:
            add(t.completed_at, 'fa-circle-check', 'success',
                f'Task completed: {t.title}', None,
                t.completer.username if t.completer else None)

    for m in Message.query.filter_by(incident_id=incident.id).all():
        if m.message_type == 'radio':
            add(m.created_at, 'fa-walkie-talkie', 'closed', 'Radio transmission',
                m.message, m.user.username if m.user else None)
        elif m.is_emergency:
            add(m.created_at, 'fa-triangle-exclamation', 'danger',
                'Emergency message', m.message,
                m.user.username if m.user else None)

    for s in SOSAlert.query.filter_by(incident_id=incident.id).all():
        ff = s.firefighter.name if s.firefighter else 'Firefighter'
        add(s.created_at, 'fa-tower-broadcast', 'danger',
            f'SOS alert from {ff}', s.message, ff)
        if s.resolved_at:
            add(s.resolved_at, 'fa-circle-check', 'success', 'SOS alert resolved',
                None, s.resolver.username if s.resolver else None)

    events.sort(key=lambda e: e['ts'], reverse=True)
    return events


def incident_response_metrics(incident):
    """Key durations of the incident lifecycle, formatted for display."""
    def fmt(delta):
        secs = int(delta.total_seconds())
        if secs < 0:
            return None
        if secs < 3600:
            return f'{secs // 60}m {secs % 60:02d}s'
        return f'{secs // 3600}h {(secs % 3600) // 60:02d}m'

    metrics = []
    if incident.reported_at and incident.dispatched_at:
        v = fmt(incident.dispatched_at - incident.reported_at)
        if v:
            metrics.append(('Time to dispatch', v))
    if incident.dispatched_at and incident.on_scene_at:
        v = fmt(incident.on_scene_at - incident.dispatched_at)
        if v:
            metrics.append(('Travel time', v))
    if incident.reported_at:
        end = incident.closed_at or datetime.datetime.utcnow()
        v = fmt(end - incident.reported_at)
        if v:
            metrics.append(('Total duration' if incident.closed_at else 'Ongoing for', v))
    return metrics


@incidents_bp.route('/staff/incidents')
@login_required
def list_incidents():
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Incident.query

    if search_query:
        query = query.filter(
            db.or_(
                Incident.title.ilike(f'%{search_query}%'),
                Incident.location.ilike(f'%{search_query}%'),
                Incident.description.ilike(f'%{search_query}%')
            )
        )

    if status_filter:
        query = query.filter(Incident.status == status_filter)

    if type_filter:
        query = query.filter(Incident.incident_type == type_filter)

    if date_from:
        date_from_obj = datetime.datetime.strptime(date_from, '%Y-%m-%d')
        query = query.filter(Incident.reported_at >= date_from_obj)

    if date_to:
        date_to_obj = datetime.datetime.strptime(date_to, '%Y-%m-%d') + datetime.timedelta(days=1)
        query = query.filter(Incident.reported_at <= date_to_obj)

    all_incidents = query.order_by(Incident.reported_at.desc()).all()

    all_statuses = db.session.query(Incident.status).distinct().all()
    all_types = db.session.query(Incident.incident_type).distinct().all()

    return render_template('staff/incidents/list.html',
                           incidents=all_incidents,
                           all_statuses=[s[0] for s in all_statuses],
                           all_types=[t[0] for t in all_types],
                           search_query=search_query,
                           status_filter=status_filter,
                           type_filter=type_filter,
                           date_from=date_from,
                           date_to=date_to)


@incidents_bp.route('/staff/report_incident', methods=['GET', 'POST'])
@login_required
@role_required('dispatcher', 'commander')
def report_incident():
    form = IncidentForm()
    vehicles = Vehicle.query.all()
    form.vehicle_id.choices = [(v.id, f"{v.type} - {v.location}") for v in vehicles]

    if not form.vehicle_id.choices:
        form.vehicle_id.choices = [(0, 'No vehicles available - Import data first!')]

    if form.validate_on_submit():
        if form.vehicle_id.data == 0:
            flash('Please import vehicles first!', 'danger')
            return redirect(url_for('incidents.report_incident'))

        lat = None
        lon = None
        if form.latitude.data and form.longitude.data:
            try:
                lat = float(form.latitude.data)
                lon = float(form.longitude.data)
            except:
                flash('Invalid coordinates format. Using default.', 'warning')

        # If coordinates weren't supplied, geocode the location so the dispatched
        # unit can be routed to it on the live map.
        if (lat is None or lon is None) and form.location.data:
            g_lat, g_lon = geocode_address(form.location.data)
            if g_lat is not None:
                lat, lon = g_lat, g_lon

        new_incident = Incident(
            title=form.title.data,
            location=form.location.data,
            latitude=lat,
            longitude=lon,
            incident_type=form.incident_type.data,
            description=form.description.data,
            reported_by=session.get('user_id'),
            status='Reported',
            assigned_vehicle_id=form.vehicle_id.data
        )

        db.session.add(new_incident)
        db.session.commit()

        vehicle = Vehicle.query.get(form.vehicle_id.data)

        # Dispatch the chosen unit and start its live route to the incident.
        if vehicle and lat is not None and lon is not None:
            start_vehicle_route(vehicle, lat, lon)
            vehicle.current_incident_id = new_incident.id
            new_incident.status = 'Dispatched'
            new_incident.dispatched_at = datetime.datetime.utcnow()
            db.session.commit()
            flash(f'Incident reported. {vehicle.type} is en route — track it live on the incident map.', 'success')
            return redirect(url_for('incidents.detail', incident_id=new_incident.id))

        flash(f'Incident reported successfully! {vehicle.type} has been assigned.', 'success')
        return redirect(url_for('incidents.detail', incident_id=new_incident.id))

    return render_template('staff/incidents/report.html', form=form, vehicles=vehicles)


@incidents_bp.route('/staff/incident/<int:incident_id>', methods=['GET', 'POST'])
@login_required
def detail(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    form = StatusUpdateForm()

    if form.validate_on_submit():
        if form.new_status.data != incident.status:
            update = StatusUpdate(
                incident_id=incident.id,
                user_id=session.get('user_id'),
                old_status=incident.status,
                new_status=form.new_status.data,
                comment=form.comment.data
            )
            db.session.add(update)

            old_status = incident.status
            incident.status = form.new_status.data
            incident.updated_by = session.get('user_id')

            now = datetime.datetime.utcnow()
            if form.new_status.data == 'Dispatched' and not incident.dispatched_at:
                incident.dispatched_at = now
            elif form.new_status.data == 'On Scene' and not incident.on_scene_at:
                incident.on_scene_at = now
            elif form.new_status.data == 'Closed' and not incident.closed_at:
                incident.closed_at = now
                release_incident_units(incident)

            db.session.commit()

            create_notification(
                user_id=incident.reported_by,
                title=f'Incident #{incident.id} Status Updated',
                message=f'Status changed from {old_status} to {form.new_status.data}',
                incident_id=incident.id
            )

            if incident.assigned_vehicle:
                for firefighter in incident.assigned_vehicle.firefighters:
                    user = UserModel.query.filter_by(username=firefighter.name).first()
                    if user:
                        create_notification(
                            user_id=user.id,
                            title=f'Incident #{incident.id} Update',
                            message=f'Your assigned incident is now {form.new_status.data}',
                            incident_id=incident.id
                        )

            flash(f'Incident status updated to {form.new_status.data}', 'success')
            return redirect(url_for('incidents.detail', incident_id=incident.id))
        else:
            flash('Status unchanged', 'info')

    weather = None
    if incident.latitude and incident.longitude:
        weather = get_weather(incident.latitude, incident.longitude)

    # Open incidents that could still be linked under this one if it is major.
    linkable = []
    if incident.is_major:
        linkable = Incident.query.filter(
            Incident.id != incident.id,
            Incident.status != 'Closed',
            Incident.parent_incident_id.is_(None),
            Incident.is_major.is_(False)
        ).order_by(Incident.reported_at.desc()).all()

    return render_template('staff/incidents/detail.html',
                           incident=incident,
                           form=form,
                           timeline=build_incident_timeline(incident),
                           response_metrics=incident_response_metrics(incident),
                           linkable=linkable,
                           weather=weather)


@incidents_bp.route('/staff/incident/<int:incident_id>/quick-status', methods=['POST'])
@login_required
def quick_status_update(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    new_status = request.json.get('status')

    if not new_status:
        return {'error': 'No status provided'}, 400

    update = StatusUpdate(
        incident_id=incident.id,
        user_id=session.get('user_id'),
        old_status=incident.status,
        new_status=new_status,
        comment='Quick update from list view'
    )
    db.session.add(update)

    old_status = incident.status
    incident.status = new_status
    incident.updated_by = session.get('user_id')

    now = datetime.datetime.utcnow()
    if new_status == 'Dispatched' and not incident.dispatched_at:
        incident.dispatched_at = now
        # Start the live route for the assigned unit.
        if incident.assigned_vehicle and incident.latitude is not None and incident.longitude is not None:
            start_vehicle_route(incident.assigned_vehicle, incident.latitude, incident.longitude)
            incident.assigned_vehicle.current_incident_id = incident.id
    elif new_status == 'On Scene' and not incident.on_scene_at:
        incident.on_scene_at = now
    elif new_status == 'Closed' and not incident.closed_at:
        incident.closed_at = now
        release_incident_units(incident)

    db.session.commit()

    create_notification(
        user_id=incident.reported_by,
        title=f'Incident #{incident.id} Status Updated',
        message=f'Status changed from {old_status} to {new_status}',
        incident_id=incident.id
    )

    return {'success': True, 'new_status': new_status}


# ========== MAJOR INCIDENT MODE ==========
@incidents_bp.route('/staff/incident/<int:incident_id>/declare-major', methods=['POST'])
@login_required
@role_required('commander')
def declare_major(incident_id):
    """Promote an incident to a Major Incident so related incidents can be
    linked under it as one command structure."""
    incident = Incident.query.get_or_404(incident_id)

    if incident.parent_incident_id:
        flash('This incident is part of another major incident — unlink it first.', 'warning')
        return redirect(url_for('incidents.detail', incident_id=incident_id))

    incident.is_major = True
    db.session.add(StatusUpdate(
        incident_id=incident.id,
        user_id=session.get('user_id'),
        old_status=incident.status,
        new_status=incident.status,
        comment='Declared a MAJOR INCIDENT — related incidents now report under this command'
    ))
    db.session.commit()

    flash(f'Incident #{incident.id} declared a Major Incident.', 'success')
    return redirect(url_for('incidents.detail', incident_id=incident_id))


@incidents_bp.route('/staff/incident/<int:incident_id>/link-child', methods=['POST'])
@login_required
@role_required('commander')
def link_child(incident_id):
    """Attach another incident as a child of this major incident."""
    parent = Incident.query.get_or_404(incident_id)
    child_id = request.form.get('child_id', type=int)
    child = Incident.query.get_or_404(child_id) if child_id else None

    if not parent.is_major:
        flash('Declare this incident as major before linking others.', 'warning')
    elif not child or child.id == parent.id:
        flash('Pick a different incident to link.', 'warning')
    elif child.is_major or child.children:
        flash('Cannot link another major incident — unlink its children first.', 'warning')
    else:
        child.parent_incident_id = parent.id
        db.session.add(StatusUpdate(
            incident_id=child.id,
            user_id=session.get('user_id'),
            old_status=child.status,
            new_status=child.status,
            comment=f'Linked under Major Incident #{parent.id} ({parent.title})'
        ))
        db.session.commit()
        flash(f'Incident #{child.id} is now part of Major Incident #{parent.id}.', 'success')

    return redirect(url_for('incidents.detail', incident_id=incident_id))


@incidents_bp.route('/staff/incident/<int:incident_id>/unlink', methods=['POST'])
@login_required
@role_required('commander')
def unlink_child(incident_id):
    """Detach a child incident from its major incident."""
    child = Incident.query.get_or_404(incident_id)
    parent = child.parent

    if parent:
        child.parent_incident_id = None
        db.session.add(StatusUpdate(
            incident_id=child.id,
            user_id=session.get('user_id'),
            old_status=child.status,
            new_status=child.status,
            comment=f'Unlinked from Major Incident #{parent.id}'
        ))
        db.session.commit()
        flash(f'Incident #{child.id} unlinked from Major Incident #{parent.id}.', 'success')
        return redirect(url_for('incidents.detail', incident_id=parent.id))

    return redirect(url_for('incidents.detail', incident_id=incident_id))


@incidents_bp.route('/staff/incident/<int:incident_id>/pdf')
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def incident_pdf(incident_id):
    from flask import send_file
    incident = Incident.query.get_or_404(incident_id)

    try:
        pdf_buffer = generate_incident_pdf(incident)
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"incident_{incident_id}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('incidents.detail', incident_id=incident_id))


@incidents_bp.route('/staff/incident/<int:incident_id>/pdf/view')
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def view_incident_pdf(incident_id):
    from flask import send_file
    incident = Incident.query.get_or_404(incident_id)

    try:
        pdf_buffer = generate_incident_pdf(incident)
        return send_file(
            pdf_buffer,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('incidents.detail', incident_id=incident_id))


@incidents_bp.route('/staff/incidents/export')
@login_required
@role_required('commander')
def export_incidents():
    si = StringIO()
    cw = csv.writer(si)

    cw.writerow(['ID', 'Title', 'Location', 'Type', 'Status',
                 'Reported At', 'Reported By', 'Assigned Vehicle'])

    incidents = Incident.query.order_by(Incident.reported_at.desc()).all()

    for i in incidents:
        cw.writerow([
            i.id,
            i.title,
            i.location,
            i.incident_type,
            i.status,
            i.reported_at.strftime('%Y-%m-%d %H:%M'),
            i.reporter.username if i.reporter else 'Unknown',
            i.assigned_vehicle.type if i.assigned_vehicle else 'Unassigned'
        ])

    output = si.getvalue()
    si.close()

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=incidents_export.csv"}
    )


# ========== TASK MANAGEMENT ROUTES ==========

@incidents_bp.route('/staff/incident/<int:incident_id>/tasks')
@login_required
def incident_tasks(incident_id):
    """View all tasks for an incident"""
    from app.models.task import Task
    incident = Incident.query.get_or_404(incident_id)
    tasks = Task.query.filter_by(incident_id=incident_id).order_by(Task.created_at.desc()).all()

    # Get firefighters for assignment dropdown
    firefighters = Firefighter.query.filter_by(status='available').all()

    return render_template('staff/incidents/tasks.html',
                           incident=incident,
                           tasks=tasks,
                           firefighters=firefighters)


@incidents_bp.route('/staff/incident/<int:incident_id>/tasks/add', methods=['GET', 'POST'])
@login_required
@role_required('dispatcher', 'commander')
def add_task(incident_id):
    """Add a new task to an incident"""
    from app.models.task import Task
    from app.forms.incident_forms import TaskForm

    incident = Incident.query.get_or_404(incident_id)
    form = TaskForm()

    # Populate assignee choices
    firefighters = Firefighter.query.all()
    form.assigned_to.choices = [(0, '-- Not Assigned --')] + [(f.id, f"{f.name} ({f.rank})") for f in firefighters]

    if form.validate_on_submit():
        # Parse deadline if provided
        deadline = None
        if form.deadline.data:
            try:
                deadline = datetime.datetime.strptime(form.deadline.data, '%Y-%m-%d %H:%M')
            except:
                flash('Invalid deadline format. Use YYYY-MM-DD HH:MM', 'warning')

        task = Task(
            title=form.title.data,
            description=form.description.data,
            incident_id=incident.id,
            assigned_to=form.assigned_to.data if form.assigned_to.data != 0 else None,
            created_by=session.get('user_id'),
            priority=form.priority.data,
            deadline=deadline,
            notes=form.notes.data,
            status='pending'
        )

        db.session.add(task)
        db.session.commit()

        # Create notification for assigned firefighter
        if task.assigned_to:
            user = UserModel.query.filter_by(username=task.assignee.name).first()
            if user:
                create_notification(
                    user_id=user.id,
                    title=f'New Task Assigned',
                    message=f'You have been assigned: {task.title} for incident #{incident.id}',
                    incident_id=incident.id
                )

        flash(f'Task "{task.title}" created successfully!', 'success')
        return redirect(url_for('incidents.incident_tasks', incident_id=incident.id))

    return render_template('staff/incidents/add_task.html',
                           incident=incident,
                           form=form)


@incidents_bp.route('/staff/task/<int:task_id>')
@login_required
def task_detail(task_id):
    """View task details"""
    from app.models.task import Task
    from app.forms.incident_forms import TaskStatusForm

    task = Task.query.get_or_404(task_id)
    form = TaskStatusForm()

    return render_template('staff/incidents/task_detail.html',
                           task=task,
                           form=form)


@incidents_bp.route('/staff/task/<int:task_id>/update', methods=['POST'])
@login_required
def update_task_status(task_id):
    """Update task status"""
    from app.models.task import Task
    from app.forms.incident_forms import TaskStatusForm

    task = Task.query.get_or_404(task_id)
    form = TaskStatusForm()

    if form.validate_on_submit():
        old_status = task.status
        task.status = form.status.data
        task.notes = (
                                 task.notes or '') + f"\n\n{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} - Status changed to {form.status.data}: {form.notes.data}" if form.notes.data else task.notes

        if form.status.data == 'completed' and not task.completed_at:
            task.completed_at = datetime.datetime.utcnow()
            task.completed_by = session.get('user_id')

        db.session.commit()

        # Notify creator
        create_notification(
            user_id=task.created_by,
            title=f'Task Status Updated',
            message=f'Task "{task.title}" changed from {old_status} to {task.status}',
            incident_id=task.incident_id
        )

        flash(f'Task status updated to {task.status}', 'success')
        return redirect(url_for('incidents.task_detail', task_id=task.id))

    return redirect(url_for('incidents.task_detail', task_id=task.id))


@incidents_bp.route('/staff/task/<int:task_id>/delete', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def delete_task(task_id):
    """Delete a task"""
    from app.models.task import Task

    task = Task.query.get_or_404(task_id)
    incident_id = task.incident_id

    db.session.delete(task)
    db.session.commit()

    flash(f'Task "{task.title}" deleted.', 'warning')
    return redirect(url_for('incidents.incident_tasks', incident_id=incident_id))


# ========== RESOURCE REQUEST ROUTES ==========

@incidents_bp.route('/staff/incident/<int:incident_id>/resources')
@login_required
def incident_resources(incident_id):
    """View resource requests for an incident"""
    from app.models.resource import ResourceRequest

    incident = Incident.query.get_or_404(incident_id)
    requests = ResourceRequest.query.filter_by(incident_id=incident_id).order_by(
        ResourceRequest.created_at.desc()).all()

    return render_template('staff/incidents/resources.html',
                           incident=incident,
                           requests=requests)


@incidents_bp.route('/staff/incident/<int:incident_id>/resources/request', methods=['GET', 'POST'])
@login_required
def request_resource(incident_id):
    """Create a new resource request"""
    from app.models.resource import ResourceRequest
    from app.forms.incident_forms import ResourceRequestForm

    incident = Incident.query.get_or_404(incident_id)
    form = ResourceRequestForm()

    if form.validate_on_submit():
        request = ResourceRequest(
            incident_id=incident.id,
            requester_id=session.get('user_id'),
            resource_type=form.resource_type.data,
            quantity=form.quantity.data,
            description=form.description.data,
            priority=form.priority.data,
            status='pending'
        )
        db.session.add(request)
        db.session.commit()

        # Notify commanders and dispatchers
        users = UserModel.query.filter(UserModel.role.in_(['commander', 'dispatcher'])).all()
        for user in users:
            create_notification(
                user_id=user.id,
                title=f'New Resource Request',
                message=f'Request for {form.resource_type} at incident #{incident.id}',
                incident_id=incident.id
            )

        flash(f'Resource request submitted!', 'success')
        return redirect(url_for('incidents.incident_resources', incident_id=incident.id))

    return render_template('staff/incidents/request_resource.html',
                           incident=incident,
                           form=form)


@incidents_bp.route('/staff/resource/<int:request_id>/update', methods=['POST'])
@login_required
@role_required('commander', 'dispatcher')
def update_resource_request(request_id):
    """Update resource request status"""
    from app.models.resource import ResourceRequest
    from app.forms.incident_forms import ResourceRequestResponseForm

    request = ResourceRequest.query.get_or_404(request_id)
    form = ResourceRequestResponseForm()

    if form.validate_on_submit():
        old_status = request.status
        request.status = form.status.data
        request.notes = form.notes.data

        if form.status.data == 'fulfilled' and not request.fulfilled_at:
            request.fulfilled_at = datetime.datetime.utcnow()
            request.fulfilled_by = session.get('user_id')

        db.session.commit()

        # Notify requester
        create_notification(
            user_id=request.requester_id,
            title=f'Resource Request Updated',
            message=f'Your request for {request.resource_type} changed from {old_status} to {request.status}',
            incident_id=request.incident_id
        )

        flash(f'Request #{request.id} updated to {request.status}', 'success')
        return redirect(url_for('incidents.incident_resources', incident_id=request.incident_id))

    return redirect(url_for('incidents.incident_resources', incident_id=request.incident_id))