from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models.volunteer import VolunteerApplication, TrainingSession, TrainingParticipant
from app.models.user import UserModel
from app.models.firefighter import Firefighter
from app.forms.volunteer_forms import ApplicationReviewForm, TrainingForm
from app.utils import login_required, role_required, create_notification
import datetime

volunteers_bp = Blueprint('volunteers', __name__)


@volunteers_bp.route('/staff/volunteers')
@login_required
@role_required('commander', 'dispatcher')
def applications_list():
    applications = VolunteerApplication.query.order_by(VolunteerApplication.applied_at.desc()).all()

    stats = {
        'total': len(applications),
        'pending': sum(1 for a in applications if a.status == 'pending'),
        'approved': sum(1 for a in applications if a.status == 'approved'),
        'trained': sum(1 for a in applications if a.status == 'trained')
    }

    return render_template('staff/volunteers/applications.html',
                           applications=applications,
                           stats=stats)


@volunteers_bp.route('/staff/volunteer/<int:app_id>', methods=['GET', 'POST'])
@login_required
@role_required('commander')
def review_application(app_id):
    application = VolunteerApplication.query.get_or_404(app_id)
    form = ApplicationReviewForm()

    if form.validate_on_submit():
        application.status = form.status.data
        application.notes = form.notes.data
        application.reviewed_by = session.get('user_id')
        application.reviewed_at = datetime.datetime.utcnow()
        db.session.commit()

        if form.status.data == 'approved':
            create_notification(
                user_id=application.reviewed_by,
                title=f'Volunteer Application Approved',
                message=f'{application.full_name} has been approved for training',
                incident_id=None
            )

        flash(f'Application for {application.full_name} updated to {form.status.data}', 'success')
        return redirect(url_for('volunteers.applications_list'))

    form.status.data = application.status
    form.notes.data = application.notes

    return render_template('staff/volunteers/review.html',
                           application=application,
                           form=form)


@volunteers_bp.route('/staff/trainings')
@login_required
@role_required('commander')
def trainings_list():
    upcoming = TrainingSession.query.filter(
        TrainingSession.date > datetime.datetime.utcnow(),
        TrainingSession.status != 'cancelled'
    ).order_by(TrainingSession.date).all()

    past = TrainingSession.query.filter(
        TrainingSession.date <= datetime.datetime.utcnow()
    ).order_by(TrainingSession.date.desc()).all()

    return render_template('staff/volunteers/trainings.html',
                           upcoming=upcoming,
                           past=past)


@volunteers_bp.route('/staff/training/add', methods=['GET', 'POST'])
@login_required
@role_required('commander')
def add_training():
    form = TrainingForm()

    if form.validate_on_submit():
        training = TrainingSession(
            title=form.title.data,
            description=form.description.data,
            date=form.date.data,
            duration_hours=form.duration_hours.data,
            location=form.location.data,
            max_participants=form.max_participants.data,
            instructor=form.instructor.data,
            created_by=session.get('user_id')
        )
        db.session.add(training)
        db.session.commit()

        flash(f'Training "{training.title}" scheduled!', 'success')
        return redirect(url_for('volunteers.trainings_list'))

    return render_template('staff/volunteers/training_form.html', form=form, title="Schedule Training")


@volunteers_bp.route('/staff/training/<int:training_id>/enroll')
@login_required
@role_required('commander')
def enroll_volunteers(training_id):
    training = TrainingSession.query.get_or_404(training_id)
    approved_volunteers = VolunteerApplication.query.filter_by(status='approved').all()

    return render_template('staff/volunteers/enroll.html',
                           training=training,
                           volunteers=approved_volunteers)