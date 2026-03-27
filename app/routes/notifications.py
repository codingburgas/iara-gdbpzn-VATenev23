from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models.notification import Notification
from app.models.firefighter import Firefighter
from app.models.user import UserModel
from app.models.incident import Incident
from app.models.communication import SOSAlert
from app.utils import login_required, role_required, create_notification
import datetime

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/staff/test')
def test():
    return "Notifications blueprint is working!"

@notifications_bp.route('/staff/notifications')
@login_required
def view_notifications():
    notifications = Notification.query.filter_by(
        user_id=session.get('user_id')
    ).order_by(Notification.created_at.desc()).all()

    for n in notifications:
        n.is_read = True
    db.session.commit()

    return render_template('staff/notifications/list.html', notifications=notifications)


@notifications_bp.route('/staff/notifications/count')
@login_required
def notification_count():
    count = Notification.query.filter_by(
        user_id=session.get('user_id'),
        is_read=False
    ).count()
    return {'count': count}


@notifications_bp.route('/staff/notifications/clear', methods=['POST'])
@login_required
def clear_notifications():
    Notification.query.filter_by(
        user_id=session.get('user_id'),
        is_read=True
    ).delete()
    db.session.commit()
    return redirect(url_for('notifications.view_notifications'))


# ========== SOS ROUTES ==========

@notifications_bp.route('/staff/sos', methods=['POST'])
@login_required
def send_sos():
    """Send SOS alert from firefighter"""
    data = request.get_json()

    firefighter = Firefighter.query.filter_by(name=session.get('user_name')).first()
    if not firefighter:
        return {'error': 'Firefighter profile not found'}, 404

    incident_id = data.get('incident_id')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    message = data.get('message', 'EMERGENCY! Firefighter needs immediate assistance!')

    # Create SOS alert
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

    # Notify all dispatchers and commanders
    users = UserModel.query.filter(UserModel.role.in_(['dispatcher', 'commander'])).all()
    for user in users:
        create_notification(
            user_id=user.id,
            title=f'🚨 MAYDAY! SOS Alert from {firefighter.name}',
            message=f'{message}\nLocation: {latitude}, {longitude}' if latitude else message,
            incident_id=incident_id
        )

    # If incident exists, notify all assigned firefighters
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


@notifications_bp.route('/staff/sos/<int:sos_id>/resolve', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def resolve_sos(sos_id):
    """Resolve an SOS alert"""
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


@notifications_bp.route('/staff/sos/active')
@login_required
def get_active_sos():
    """Get all active SOS alerts"""
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