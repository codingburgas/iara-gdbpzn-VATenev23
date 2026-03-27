from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from werkzeug.security import generate_password_hash, check_password_hash
from app.forms.auth_forms import RegisterForm, LoginForm
from app.models.user import UserModel
from app.models.firefighter import Firefighter
from app import db
from app.utils import login_required, role_required
import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/portal')
@auth_bp.route('/dispatch')
@auth_bp.route('/staff')
def portal_redirect():
    """Hidden staff portal entry points"""
    return redirect(url_for('auth.staff_login'))


@auth_bp.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    """Professional staff login page"""
    form = LoginForm()
    if form.validate_on_submit():
        user = UserModel.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password, form.password.data):
            session['user_id'] = user.id
            session['user_name'] = user.username
            session['user_role'] = user.role
            session['logged_in'] = True
            session['workstation'] = request.remote_addr

            print(f"STAFF LOGIN: {user.username} ({user.role}) from {request.remote_addr}")
            flash(f'Welcome to Emergency Operations Portal, {user.username}', 'success')

            if user.role == 'dispatcher':
                return redirect(url_for('dashboard.dispatcher_dashboard'))
            elif user.role == 'firefighter':
                return redirect(url_for('dashboard.firefighter_dashboard'))
            elif user.role == 'commander':
                return redirect(url_for('dashboard.commander_dashboard'))
            else:
                return redirect(url_for('dashboard.staff_dashboard'))
        else:
            flash('Invalid credentials. This attempt has been logged.', 'danger')
            return redirect(url_for('auth.staff_login'))

    return render_template('staff/auth/login.html', form=form)


@auth_bp.route('/staff/register', methods=['GET', 'POST'])
@login_required
@role_required('commander')
def staff_register():
    """Registration for staff - creates both User and Firefighter records"""
    form = RegisterForm()

    if form.validate_on_submit():
        existing_user = UserModel.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('auth.staff_register'))

        hashed_password = generate_password_hash(form.password.data)
        new_user = UserModel(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            role=form.role.data
        )
        db.session.add(new_user)
        db.session.flush()

        if form.role.data == 'firefighter' and form.full_name.data:
            firefighter = Firefighter(
                name=form.full_name.data,
                rank=form.rank.data or 'Firefighter',
                status='available',
                employee_id=form.employee_id.data,
                phone=form.phone.data,
                hire_date=datetime.datetime.utcnow(),
                user_id=new_user.id
            )
            db.session.add(firefighter)
            flash(f'Firefighter {form.full_name.data} created and linked to account!', 'success')

        db.session.commit()

        flash(f'Registration successful! {form.role.data.capitalize()} account created.', 'success')
        return redirect(url_for('personnel.list_firefighters'))

    return render_template('staff/auth/register.html', form=form)


@auth_bp.route('/staff/logout')
def staff_logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.staff_login'))