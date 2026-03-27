from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models.incident import Incident
from app.models.user import UserModel
from app.models.communication import Message, MessageTemplate
from app.models.firefighter import Firefighter
from app.models.notification import Notification
from app.forms.communication_forms import MessageForm, RadioLogForm, TemplateForm
from app.utils import login_required, role_required, create_notification
import datetime

communications_bp = Blueprint('communications', __name__)

@communications_bp.route('/staff/sos-check', methods=['GET'])
def sos_check():
    """Check if SOS route is registered"""
    return {"message": "Communications blueprint is working", "routes": ["/staff/sos should exist"]}

@communications_bp.route('/staff/sos-test-full', methods=['GET'])
def sos_test_full():
    """Test if the SOS route structure works"""
    return {"status": "OK", "message": "SOS route structure is ready", "note": "Use POST to send actual SOS"}

def notify_users_about_incident(incident_id, message):
    incident = Incident.query.get(incident_id)

    if incident.reported_by:
        create_notification(
            user_id=incident.reported_by,
            title=f'🚨 EMERGENCY - Incident #{incident.id}',
            message=message,
            incident_id=incident.id
        )

    if incident.assigned_vehicle:
        for firefighter in incident.assigned_vehicle.firefighters:
            user = UserModel.query.filter_by(username=firefighter.name).first()
            if user:
                create_notification(
                    user_id=user.id,
                    title=f'🚨 EMERGENCY ALERT',
                    message=message,
                    incident_id=incident.id
                )


@communications_bp.route('/staff/incident/<int:incident_id>/chat', methods=['GET', 'POST'])
@login_required
def incident_chat(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    form = MessageForm()
    templates = MessageTemplate.query.order_by(MessageTemplate.order).all()

    if form.validate_on_submit():
        message = Message(
            incident_id=incident.id,
            user_id=session.get('user_id'),
            message=form.message.data,
            message_type='broadcast' if form.is_emergency.data else 'chat',
            is_emergency=form.is_emergency.data
        )
        db.session.add(message)
        db.session.commit()

        if form.is_emergency.data:
            notify_users_about_incident(incident.id, form.message.data)
            flash('🚨 EMERGENCY BROADCAST SENT! 🚨', 'danger')
        else:
            flash('Message sent', 'success')

        return redirect(url_for('communications.incident_chat', incident_id=incident.id))

    messages = Message.query.filter_by(incident_id=incident.id).order_by(Message.created_at).all()

    return render_template('staff/communications/chat.html',
                           incident=incident,
                           form=form,
                           messages=messages,
                           templates=templates)


@communications_bp.route('/staff/incident/<int:incident_id>/chat/quick', methods=['POST'])
@login_required
def quick_message(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    template_id = request.json.get('template_id')
    template = MessageTemplate.query.get(template_id)

    if template:
        message = Message(
            incident_id=incident.id,
            user_id=session.get('user_id'),
            message=template.message,
            message_type='chat',
            is_emergency=False
        )
        db.session.add(message)
        db.session.commit()
        return {'success': True, 'message': template.message}

    return {'error': 'Template not found'}, 404


@communications_bp.route('/staff/incident/<int:incident_id>/radio', methods=['GET', 'POST'])
@login_required
def radio_log(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    form = RadioLogForm()

    if form.validate_on_submit():
        transmission = f"[{form.unit.data}] {form.message.data}"

        message = Message(
            incident_id=incident.id,
            user_id=session.get('user_id'),
            message=transmission,
            message_type='radio'
        )
        db.session.add(message)
        db.session.commit()

        flash(f'Radio transmission logged', 'info')
        return redirect(url_for('communications.radio_log', incident_id=incident.id))

    radio_messages = Message.query.filter_by(
        incident_id=incident.id,
        message_type='radio'
    ).order_by(Message.created_at.desc()).all()

    return render_template('staff/communications/radio.html',
                           incident=incident,
                           form=form,
                           radio_messages=radio_messages)


@communications_bp.route('/staff/templates')
@login_required
@role_required('dispatcher', 'commander')
def manage_templates():
    templates = MessageTemplate.query.order_by(MessageTemplate.category, MessageTemplate.order).all()
    return render_template('staff/communications/templates.html', templates=templates)


@communications_bp.route('/staff/templates/add', methods=['GET', 'POST'])
@login_required
@role_required('dispatcher', 'commander')
def add_template():
    form = TemplateForm()

    if form.validate_on_submit():
        template = MessageTemplate(
            name=form.name.data,
            message=form.message.data,
            category=form.category.data
        )
        db.session.add(template)
        db.session.commit()
        flash(f'Template "{template.name}" added!', 'success')
        return redirect(url_for('communications.manage_templates'))

    return render_template('staff/communications/template_form.html', form=form, title="Add Template")


@communications_bp.route('/staff/templates/<int:template_id>/delete', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def delete_template(template_id):
    template = MessageTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()
    flash(f'Template "{template.name}" deleted.', 'warning')
    return redirect(url_for('communications.manage_templates'))


# ========== SOS ROUTES ==========

@communications_bp.route('/staff/sos', methods=['GET', 'POST'])
def send_sos():
    """Send SOS alert from firefighter"""

    # For GET requests, return info about the endpoint
    if request.method == 'GET':
        return {
            "message": "SOS endpoint is working",
            "usage": "Send POST request with incident_id, latitude, longitude, message"
        }

    # For POST requests, handle the SOS
    data = request.get_json()
    print(f"SOS POST received: {data}")

    try:
        from app.models.firefighter import Firefighter
        from app.models.communication import SOSAlert
        from app.models.user import UserModel
        from app.models.incident import Incident
        from app.utils import create_notification
        import datetime

        firefighter = Firefighter.query.filter_by(name=session.get('user_name')).first()
        if not firefighter:
            return {'error': 'Firefighter profile not found'}, 404

        incident_id = data.get('incident_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        message = data.get('message', 'EMERGENCY! Firefighter needs immediate assistance!')

        sos = SOSAlert(
            firefighter_id=firefighter.id,
            incident_id=incident_id,
            latitude=latitude,
            longitude=longitude,
            message=message,
            status='active'
        )
        db.session.add(sos)
        db.session.commit()

        users = UserModel.query.filter(UserModel.role.in_(['dispatcher', 'commander'])).all()
        for user in users:
            create_notification(
                user_id=user.id,
                title=f'🚨 MAYDAY! SOS Alert from {firefighter.name}',
                message=f'{message}\nLocation: {latitude}, {longitude}' if latitude else message,
                incident_id=incident_id
            )

        if incident_id:
            incident = Incident.query.get(incident_id)
            if incident and incident.assigned_vehicle:
                for ff in incident.assigned_vehicle.firefighters:
                    user = UserModel.query.filter_by(username=ff.name).first()
                    if user and user.id != session.get('user_id'):
                        create_notification(
                            user_id=user.id,
                            title=f'🚨 SOS ALERT!',
                            message=f'Firefighter {firefighter.name} needs immediate assistance at incident #{incident.id}',
                            incident_id=incident_id
                        )

        return {
            'success': True,
            'sos_id': sos.id,
            'message': 'SOS alert sent! Help is on the way.'
        }

    except Exception as e:
        print(f"SOS Error: {e}")
        return {'error': str(e)}, 500


@communications_bp.route('/staff/sos/<int:sos_id>/resolve', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def resolve_sos(sos_id):
    """Resolve an SOS alert"""
    from app.models.communication import SOSAlert
    sos = SOSAlert.query.get_or_404(sos_id)

    if sos.status != 'active':
        return {'error': 'SOS already resolved'}, 400

    sos.status = 'resolved'
    sos.resolved_at = datetime.datetime.utcnow()
    sos.resolved_by = session.get('user_id')
    db.session.commit()

    # Notify the firefighter that SOS was resolved
    user = UserModel.query.filter_by(username=sos.firefighter.name).first()
    if user:
        create_notification(
            user_id=user.id,
            title='✅ SOS Alert Resolved',
            message='Your SOS alert has been acknowledged. Help is on scene.',
            incident_id=sos.incident_id
        )

    return {'success': True, 'message': 'SOS alert resolved'}


@communications_bp.route('/staff/sos/active')
@login_required
def get_active_sos():
    """Get all active SOS alerts"""
    from app.models.communication import SOSAlert
    active_sos = SOSAlert.query.filter_by(status='active').all()

    result = []
    for sos in active_sos:
        result.append({
            'id': sos.id,
            'firefighter': sos.firefighter.name,
            'incident_id': sos.incident_id,
            'latitude': sos.latitude,
            'longitude': sos.longitude,
            'message': sos.message,
            'created_at': sos.created_at.isoformat()
        })

    return {'sos_alerts': result}