from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, Response
from app import db
from app.models.incident import Incident, StatusUpdate
from app.models.vehicle import Vehicle
from app.models.user import UserModel
from app.forms.incident_forms import IncidentForm, StatusUpdateForm
from app.utils import login_required, role_required, create_notification, generate_incident_pdf
import datetime
import csv
from io import StringIO

incidents_bp = Blueprint('incidents', __name__)


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
        flash(f'Incident reported successfully! {vehicle.type} has been dispatched.', 'success')
        return redirect(url_for('incidents.list_incidents'))

    return render_template('staff/incidents/report.html', form=form, vehicles=vehicles)


@incidents_bp.route('/staff/incident/<int:incident_id>', methods=['GET', 'POST'])
@login_required
def detail(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    form = StatusUpdateForm()
    status_history = StatusUpdate.query.filter_by(incident_id=incident_id).order_by(StatusUpdate.timestamp.desc()).all()

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

    return render_template('staff/incidents/detail.html',
                           incident=incident,
                           form=form,
                           status_history=status_history)


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
    elif new_status == 'On Scene' and not incident.on_scene_at:
        incident.on_scene_at = now
    elif new_status == 'Closed' and not incident.closed_at:
        incident.closed_at = now

    db.session.commit()

    create_notification(
        user_id=incident.reported_by,
        title=f'Incident #{incident.id} Status Updated',
        message=f'Status changed from {old_status} to {new_status}',
        incident_id=incident.id
    )

    return {'success': True, 'new_status': new_status}


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