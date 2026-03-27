from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models.notification import Notification
from app.utils import login_required

notifications_bp = Blueprint('notifications', __name__)


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