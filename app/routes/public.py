from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.forms.volunteer_forms import VolunteerApplicationForm
from app.models.volunteer import VolunteerApplication
from app import db
import datetime

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def home():
    return render_template('public/index.html')


@public_bp.route('/news')
def news():
    return render_template('public/news.html')


@public_bp.route('/safety-tips')
def safety_tips():
    return render_template('public/safety_tips.html')


@public_bp.route('/contact')
def contact():
    return render_template('public/contact.html')


@public_bp.route('/volunteer')
def volunteer():
    return render_template('public/volunteer.html')


@public_bp.route('/non-emergency', methods=['GET', 'POST'])
def non_emergency():
    if request.method == 'POST':
        flash('Thank you for your report. We will review it within 24 hours.', 'success')
        return redirect(url_for('public.non_emergency'))
    return render_template('public/non_emergency.html')


@public_bp.route('/volunteer/apply', methods=['GET', 'POST'])
def volunteer_apply():
    form = VolunteerApplicationForm()

    if form.validate_on_submit():
        application = VolunteerApplication(
            full_name=form.full_name.data,
            email=form.email.data,
            phone=form.phone.data,
            age=form.age.data,
            address=form.address.data,
            motivation=form.motivation.data,
            experience=form.experience.data,
            status='pending'
        )
        db.session.add(application)
        db.session.commit()

        flash('Thank you for your interest! We will review your application and contact you soon.', 'success')
        return redirect(url_for('public.home'))

    return render_template('public/volunteer_apply.html', form=form)