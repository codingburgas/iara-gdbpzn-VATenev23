from flask import Flask, render_template, redirect, url_for, flash, session, request, send_file, Response
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

from models import db, UserModel, Vehicle, Firefighter, Incident, StatusUpdate, Notification, Shift, Equipment, EquipmentAssignment, Message, MessageTemplate
from forms import (RegisterForm, LoginForm, IncidentForm, StatusUpdateForm,
                   ShiftStartForm, ShiftEndForm, FirefighterStatusForm,
                   EquipmentForm, EquipmentCheckoutForm, EquipmentReturnForm,
                   MessageForm, RadioLogForm, TemplateForm)
from utils import login_required, role_required, duration_filter, geocode_address, create_notification, generate_incident_pdf

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

bootstrap = Bootstrap(app)
db.init_app(app)

# Register template filters
app.template_filter('duration')(duration_filter)


def get_avg_response_time():
    """Calculate average time from reported to dispatched"""
    incidents = Incident.query.filter(Incident.dispatched_at.isnot(None)).all()
    if not incidents:
        return "N/A"

    total = 0
    count = 0
    for i in incidents:
        if i.dispatched_at and i.reported_at:
            diff = i.dispatched_at - i.reported_at
            total += diff.total_seconds() / 60  # minutes
            count += 1

    if count == 0:
        return "N/A"

    avg = total / count
    return f"{avg:.1f} min"
# ========== PUBLIC WEBSITE ROUTES ==========
@app.route('/')
def home():
    return render_template('public/index.html')


@app.route('/news')
def news():
    return render_template('public/news.html')


@app.route('/safety-tips')
def safety_tips():
    return render_template('public/safety_tips.html')


@app.route('/contact')
def contact():
    return render_template('public/contact.html')


@app.route('/volunteer')
def volunteer():
    return render_template('public/volunteer.html')


@app.route('/non-emergency', methods=['GET', 'POST'])
def non_emergency():
    if request.method == 'POST':
        flash('Thank you for your report. We will review it within 24 hours.', 'success')
        return redirect(url_for('non_emergency'))
    return render_template('public/non_emergency.html')


# ========== STAFF PORTAL ROUTES ==========
@app.route('/portal')
@app.route('/dispatch')
@app.route('/staff')
def portal_redirect():
    """Hidden staff portal entry points"""
    return redirect(url_for('staff_login'))


@app.route('/staff/login', methods=['GET', 'POST'])
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

            # Redirect based on role
            if user.role == 'dispatcher':
                return redirect(url_for('dispatcher_dashboard'))
            elif user.role == 'firefighter':
                return redirect(url_for('firefighter_dashboard'))
            elif user.role == 'commander':
                return redirect(url_for('commander_dashboard'))
            else:
                return redirect(url_for('staff_dashboard'))
        else:
            flash('Invalid credentials. This attempt has been logged.', 'danger')
            return redirect(url_for('staff_login'))

    return render_template('staff/login.html', form=form)


@app.route('/staff/register', methods=['GET', 'POST'])
@login_required
@role_required('commander')  # Only commanders can register new staff
def staff_register():
    """Registration for staff - now creates both User and Firefighter records"""
    form = RegisterForm()

    if form.validate_on_submit():
        existing_user = UserModel.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('staff_register'))

        # Create user account
        hashed_password = generate_password_hash(form.password.data)
        new_user = UserModel(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            role=form.role.data
        )
        db.session.add(new_user)
        db.session.flush()  # Get the user ID without committing yet

        # If registering a firefighter, create firefighter record
        if form.role.data == 'firefighter' and form.full_name.data:
            firefighter = Firefighter(
                name=form.full_name.data,
                rank=form.rank.data or 'Firefighter',
                status='available',
                employee_id=form.employee_id.data,
                phone=form.phone.data,
                hire_date=datetime.datetime.utcnow(),
                user_id=new_user.id  # Link to user account
            )
            db.session.add(firefighter)
            flash(f'Firefighter {form.full_name.data} created and linked to account!', 'success')

        db.session.commit()

        flash(f'Registration successful! {form.role.data.capitalize()} account created.', 'success')
        return redirect(url_for('staff_firefighters'))

    return render_template('staff/register.html', form=form)


@app.route('/staff/dashboard')
@login_required
def staff_dashboard():
    return render_template('staff/dashboard.html')


@app.route('/staff/map')
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def incident_map():
    """Display interactive map with all incidents"""
    incidents = Incident.query.filter(Incident.status != 'Closed').all()
    vehicles = Vehicle.query.all()

    return render_template('staff/map_view.html',
                           incidents=incidents,
                           vehicles=vehicles)


# ========== EQUIPMENT MANAGEMENT ROUTES ==========
@app.route('/staff/equipment')
@login_required
@role_required('dispatcher', 'commander')
def equipment_list():
    """View all equipment"""
    all_equipment = Equipment.query.all()
    vehicles = Vehicle.query.all()
    return render_template('staff/equipment_list.html',
                           equipment=all_equipment,
                           vehicles=vehicles)


@app.route('/staff/vehicle/<int:vehicle_id>/update-location', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def update_vehicle_location(vehicle_id):
    """Update vehicle GPS location"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    data = request.get_json()

    if 'latitude' in data and 'longitude' in data:
        vehicle.latitude = data['latitude']
        vehicle.longitude = data['longitude']
        vehicle.last_updated = datetime.datetime.utcnow()

        # Update status based on location relative to incident
        if 'status' in data:
            vehicle.status = data['status']

        db.session.commit()

        return {'success': True, 'message': f'{vehicle.type} location updated'}

    return {'error': 'Missing coordinates'}, 400


@app.route('/staff/vehicle/<int:vehicle_id>/assign-incident/<int:incident_id>', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def assign_vehicle_to_incident(vehicle_id, incident_id):
    """Assign a vehicle to an incident and update its status"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    incident = Incident.query.get_or_404(incident_id)

    vehicle.status = 'en_route'
    vehicle.current_incident_id = incident.id

    # Update incident with assigned vehicle if not already set
    if not incident.assigned_vehicle_id:
        incident.assigned_vehicle_id = vehicle.id

    db.session.commit()

    flash(f'{vehicle.type} dispatched to {incident.title}', 'success')

    # Create notification for firefighters on this vehicle
    for firefighter in vehicle.firefighters:
        user = UserModel.query.filter_by(username=firefighter.name).first()
        if user:
            create_notification(
                user_id=user.id,
                title=f'Dispatch Alert',
                message=f'Your unit has been dispatched to {incident.title}',
                incident_id=incident.id
            )

    return redirect(url_for('incident_detail', incident_id=incident.id))


@app.route('/staff/vehicle/<int:vehicle_id>/eta/<int:incident_id>')
@login_required
def calculate_eta(vehicle_id, incident_id):
    """Calculate ETA from vehicle to incident"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    incident = Incident.query.get_or_404(incident_id)

    if not vehicle.latitude or not vehicle.longitude or not incident.latitude or not incident.longitude:
        return {'eta': 'N/A', 'error': 'Missing coordinates'}

    # Calculate distance using Haversine formula
    from math import radians, sin, cos, sqrt, atan2

    R = 6371  # Earth radius in km

    lat1 = radians(vehicle.latitude)
    lon1 = radians(vehicle.longitude)
    lat2 = radians(incident.latitude)
    lon2 = radians(incident.longitude)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    # Assume average speed 60 km/h for emergency vehicles
    speed = vehicle.speed or 60
    eta_minutes = (distance / speed) * 60

    return {
        'distance': round(distance, 1),
        'eta_minutes': round(eta_minutes, 1),
        'eta_text': f"{int(eta_minutes)} min" if eta_minutes < 60 else f"{int(eta_minutes / 60)}h {int(eta_minutes % 60)}min"
    }


@app.route('/staff/vehicle-tracking')
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def vehicle_tracking():
    """View vehicle GPS tracking"""
    vehicles = Vehicle.query.all()
    incidents = Incident.query.filter(Incident.status != 'Closed').all()

    return render_template('staff/vehicle_tracking.html',
                           vehicles=vehicles,
                           incidents=incidents)
@app.route('/staff/equipment/add', methods=['GET', 'POST'])
@login_required
@role_required('commander')
def add_equipment():
    """Add new equipment"""
    form = EquipmentForm()

    # Populate vehicle choices
    vehicles = Vehicle.query.all()
    form.vehicle_id.choices = [(0, 'None - Not assigned')] + [(v.id, f"{v.type} - {v.location}") for v in vehicles]

    if form.validate_on_submit():
        equipment = Equipment(
            name=form.name.data,
            type=form.type.data,
            model=form.model.data,
            serial_number=form.serial_number.data,
            status=form.status.data,
            condition=form.condition.data,
            vehicle_id=form.vehicle_id.data if form.vehicle_id.data != 0 else None,
            notes=form.notes.data,
            last_inspected=datetime.datetime.utcnow()
        )

        # Set next inspection date (default 6 months)
        equipment.next_inspection = datetime.datetime.utcnow() + datetime.timedelta(days=180)

        db.session.add(equipment)
        db.session.commit()

        flash(f'Equipment {equipment.name} added successfully!', 'success')
        return redirect(url_for('equipment_list'))

    return render_template('staff/equipment_form.html', form=form, title="Add Equipment")


@app.route('/dashboard')
@login_required
def dynamic_dashboard():
    """Redirect to the appropriate dashboard based on user role"""
    user_role = session.get('user_role')

    if user_role == 'dispatcher':
        return redirect(url_for('dispatcher_dashboard'))
    elif user_role == 'firefighter':
        return redirect(url_for('firefighter_dashboard'))
    elif user_role == 'commander':
        return redirect(url_for('commander_dashboard'))
    else:
        return redirect(url_for('staff_dashboard'))

@app.route('/staff/equipment/<int:equipment_id>')
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def equipment_detail(equipment_id):
    """View equipment details"""
    equipment = Equipment.query.get_or_404(equipment_id)
    assignments = EquipmentAssignment.query.filter_by(equipment_id=equipment_id).order_by(
        EquipmentAssignment.assigned_at.desc()).all()

    return render_template('staff/equipment_detail.html',
                           equipment=equipment,
                           assignments=assignments)


@app.route('/staff/equipment/<int:equipment_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('commander')
def edit_equipment(equipment_id):
    """Edit equipment details"""
    equipment = Equipment.query.get_or_404(equipment_id)
    form = EquipmentForm(obj=equipment)

    vehicles = Vehicle.query.all()
    form.vehicle_id.choices = [(0, 'None - Not assigned')] + [(v.id, f"{v.type} - {v.location}") for v in vehicles]

    if form.validate_on_submit():
        equipment.name = form.name.data
        equipment.type = form.type.data
        equipment.model = form.model.data
        equipment.serial_number = form.serial_number.data
        equipment.status = form.status.data
        equipment.condition = form.condition.data
        equipment.vehicle_id = form.vehicle_id.data if form.vehicle_id.data != 0 else None
        equipment.notes = form.notes.data

        db.session.commit()
        flash('Equipment updated successfully!', 'success')
        return redirect(url_for('equipment_detail', equipment_id=equipment.id))

    return render_template('staff/equipment_form.html', form=form, equipment=equipment, title="Edit Equipment")


@app.route('/staff/equipment/<int:equipment_id>/checkout', methods=['GET', 'POST'])
@login_required
@role_required('dispatcher', 'commander')
def checkout_equipment(equipment_id):
    """Check out equipment for an incident"""
    equipment = Equipment.query.get_or_404(equipment_id)
    form = EquipmentCheckoutForm()

    # Populate choices
    form.equipment_id.choices = [(equipment.id, equipment.name)]
    form.incident_id.choices = [(0, 'None')] + [(i.id, f"#{i.id} - {i.title}") for i in
                                                Incident.query.filter(Incident.status != 'Closed').all()]
    form.firefighter_id.choices = [(0, 'None')] + [(f.id, f"{f.name} ({f.rank})") for f in Firefighter.query.all()]

    if form.validate_on_submit():
        assignment = EquipmentAssignment(
            equipment_id=equipment.id,
            incident_id=form.incident_id.data if form.incident_id.data != 0 else None,
            firefighter_id=form.firefighter_id.data if form.firefighter_id.data != 0 else None,
            notes=form.notes.data,
            status='assigned'
        )

        equipment.status = 'in_use'

        db.session.add(assignment)
        db.session.commit()

        # Create notification
        if form.incident_id.data != 0:
            incident = Incident.query.get(form.incident_id.data)
            create_notification(
                user_id=incident.reported_by,
                title=f'Equipment Checked Out',
                message=f'{equipment.name} checked out for incident #{incident.id}',
                incident_id=incident.id
            )

        flash(f'{equipment.name} checked out successfully!', 'success')
        return redirect(url_for('equipment_detail', equipment_id=equipment.id))

    return render_template('staff/equipment_checkout.html', form=form, equipment=equipment)


@app.route('/staff/equipment/<int:assignment_id>/return', methods=['GET', 'POST'])
@login_required
@role_required('dispatcher', 'commander')
def return_equipment(assignment_id):
    """Return checked out equipment"""
    assignment = EquipmentAssignment.query.get_or_404(assignment_id)
    equipment = assignment.equipment
    form = EquipmentReturnForm()

    if form.validate_on_submit():
        assignment.returned_at = datetime.datetime.utcnow()
        assignment.status = 'returned'
        assignment.notes = (assignment.notes or '') + f"\nReturn notes: {form.notes.data}"

        equipment.status = 'available'
        equipment.condition = form.condition.data
        equipment.last_inspected = datetime.datetime.utcnow()

        db.session.commit()

        flash(f'{equipment.name} returned successfully!', 'success')
        return redirect(url_for('equipment_detail', equipment_id=equipment.id))

    return render_template('staff/equipment_return.html', form=form, equipment=equipment, assignment=assignment)


@app.route('/staff/incident/<int:incident_id>', methods=['GET', 'POST'])
@login_required
def incident_detail(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    form = StatusUpdateForm()

    # Get status history
    status_history = StatusUpdate.query.filter_by(incident_id=incident_id).order_by(StatusUpdate.timestamp.desc()).all()

    if form.validate_on_submit():
        # Check if status actually changed
        if form.new_status.data != incident.status:
            # Create status update record
            update = StatusUpdate(
                incident_id=incident.id,
                user_id=session.get('user_id'),
                old_status=incident.status,
                new_status=form.new_status.data,
                comment=form.comment.data
            )
            db.session.add(update)

            # Update incident
            old_status = incident.status
            incident.status = form.new_status.data
            incident.updated_by = session.get('user_id')

            # Set timestamps based on status
            now = datetime.datetime.utcnow()
            if form.new_status.data == 'Dispatched' and not incident.dispatched_at:
                incident.dispatched_at = now
            elif form.new_status.data == 'On Scene' and not incident.on_scene_at:
                incident.on_scene_at = now
            elif form.new_status.data == 'Closed' and not incident.closed_at:
                incident.closed_at = now

            db.session.commit()

            # Create notification for relevant users
            create_notification(
                user_id=incident.reported_by,
                title=f'Incident #{incident.id} Status Updated',
                message=f'Status changed from {old_status} to {form.new_status.data}',
                incident_id=incident.id
            )

            if incident.assigned_vehicle:
                for firefighter in incident.assigned_vehicle.firefighters:
                    # Find user with this firefighter name
                    user = UserModel.query.filter_by(username=firefighter.name).first()
                    if user:
                        create_notification(
                            user_id=user.id,
                            title=f'Incident #{incident.id} Update',
                            message=f'Your assigned incident is now {form.new_status.data}',
                            incident_id=incident.id
                        )

            flash(f'Incident status updated to {form.new_status.data}', 'success')
            return redirect(url_for('incident_detail', incident_id=incident.id))
        else:
            flash('Status unchanged', 'info')

    return render_template('staff/incident_detail.html',
                           incident=incident,
                           form=form,
                           status_history=status_history)


@app.route('/staff/notifications')
@login_required
def view_notifications():
    notifications = Notification.query.filter_by(
        user_id=session.get('user_id')
    ).order_by(Notification.created_at.desc()).all()

    # Mark all as read when viewed
    for n in notifications:
        n.is_read = True
    db.session.commit()

    return render_template('staff/notifications.html', notifications=notifications)


@app.route('/staff/notifications/count')
@login_required
def notification_count():
    count = Notification.query.filter_by(
        user_id=session.get('user_id'),
        is_read=False
    ).count()
    return {'count': count}


@app.route('/staff/notifications/clear', methods=['POST'])
@login_required
def clear_notifications():
    Notification.query.filter_by(
        user_id=session.get('user_id'),
        is_read=True
    ).delete()
    db.session.commit()
    return redirect(url_for('view_notifications'))


@app.route('/staff/shifts')
@login_required
@role_required('dispatcher', 'commander')
def shift_management():
    """View and manage shifts"""
    active_shifts = Shift.query.filter_by(status='active').all()
    today = datetime.datetime.now().date()
    today_shifts = Shift.query.filter(
        db.func.date(Shift.start_time) == today
    ).order_by(Shift.start_time.desc()).all()

    available_firefighters = Firefighter.query.filter_by(status='available').all()

    return render_template('staff/shift_management.html',
                           active_shifts=active_shifts,
                           today_shifts=today_shifts,
                           available_firefighters=available_firefighters,
                           datetime=datetime)


@app.route('/staff/shifts/start', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def start_shift():
    """Start a shift for a firefighter"""
    firefighter_id = request.form.get('firefighter_id')
    firefighter = Firefighter.query.get(firefighter_id)

    if not firefighter:
        flash('Firefighter not found', 'danger')
        return redirect(url_for('shift_management'))

    # End any active shifts for this firefighter
    active_shift = Shift.query.filter_by(
        firefighter_id=firefighter_id,
        status='active'
    ).first()

    if active_shift:
        active_shift.status = 'completed'
        active_shift.end_time = datetime.datetime.utcnow()

    # Create new shift
    new_shift = Shift(
        firefighter_id=firefighter_id,
        start_time=datetime.datetime.utcnow(),
        status='active'
    )
    db.session.add(new_shift)

    # Update firefighter
    firefighter.status = 'on_duty'
    firefighter.current_shift_id = new_shift.id
    firefighter.last_active = datetime.datetime.utcnow()

    db.session.commit()

    flash(f'Shift started for {firefighter.name}', 'success')
    return redirect(url_for('shift_management'))


@app.route('/staff/shifts/end/<int:shift_id>', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def end_shift(shift_id):
    """End a shift"""
    shift = Shift.query.get_or_404(shift_id)

    if shift.status != 'active':
        flash('Shift is already ended', 'warning')
        return redirect(url_for('shift_management'))

    shift.status = 'completed'
    shift.end_time = datetime.datetime.utcnow()

    # Update firefighter
    if shift.firefighter:
        shift.firefighter.status = 'available'
        shift.firefighter.current_shift_id = None

    db.session.commit()

    flash(f'Shift ended for {shift.firefighter.name}', 'success')
    return redirect(url_for('shift_management'))


@app.route('/staff/firefighter/<int:firefighter_id>/status', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def update_firefighter_status(firefighter_id):
    """Update firefighter status"""
    firefighter = Firefighter.query.get_or_404(firefighter_id)
    new_status = request.form.get('status')

    if new_status:
        firefighter.status = new_status
        db.session.commit()
        flash(f'{firefighter.name} status updated to {new_status}', 'success')

    return redirect(url_for('shift_management'))


@app.route('/staff/firefighter/<int:firefighter_id>/assign', methods=['GET', 'POST'])
@login_required
@role_required('commander', 'dispatcher')
def assign_firefighter(firefighter_id):
    """Assign a firefighter to a vehicle"""
    firefighter = Firefighter.query.get_or_404(firefighter_id)
    vehicles = Vehicle.query.all()

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        if vehicle_id:
            firefighter.vehicle_id = vehicle_id
            db.session.commit()
            flash(f'{firefighter.name} assigned to vehicle successfully!', 'success')
        else:
            # Unassign
            firefighter.vehicle_id = None
            db.session.commit()
            flash(f'{firefighter.name} unassigned from vehicle.', 'info')

        return redirect(url_for('staff_firefighters'))

    return render_template('staff/assign_firefighter.html',
                           firefighter=firefighter,
                           vehicles=vehicles)
@app.route('/dispatcher/dashboard')
@login_required
@role_required('dispatcher', 'commander')
def dispatcher_dashboard():
    active_incidents = Incident.query.filter(Incident.status != 'Closed').count()
    available_vehicles = Vehicle.query.count()
    total_firefighters = Firefighter.query.count()
    recent_incidents = Incident.query.order_by(Incident.reported_at.desc()).limit(5).all()

    return render_template('staff/dispatcher_dashboard.html',
                           active_incidents=active_incidents,
                           available_vehicles=available_vehicles,
                           total_firefighters=total_firefighters,
                           recent_incidents=recent_incidents)


@app.route('/firefighter/dashboard')
@login_required
@role_required('firefighter', 'commander')
def firefighter_dashboard():
    # Get incidents assigned to this firefighter's vehicle
    firefighter = Firefighter.query.filter_by(name=session.get('user_name')).first()
    my_incidents = []
    if firefighter and firefighter.vehicle_id:
        my_incidents = Incident.query.filter_by(assigned_vehicle_id=firefighter.vehicle_id).all()

    return render_template('staff/firefighter_dashboard.html',
                           incidents=my_incidents,
                           firefighter=firefighter)


@app.route('/commander/dashboard')
@login_required
@role_required('commander')
def commander_dashboard():
    # Get incident counts by type for charts
    fire_count = Incident.query.filter_by(incident_type='fire').count()
    rescue_count = Incident.query.filter_by(incident_type='rescue').count()
    accident_count = Incident.query.filter_by(incident_type='accident').count()
    hazmat_count = Incident.query.filter_by(incident_type='hazmat').count()
    other_count = Incident.query.filter_by(incident_type='other').count()

    # Get monthly incident data for the last 6 months
    import calendar
    from sqlalchemy import extract

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

    # Calculate units in field
    units_in_field = Incident.query.filter(Incident.status.in_(['Dispatched', 'On Scene'])).count()

    # Get last incident
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
        'units_in_field': units_in_field,  # ADD THIS
        'last_incident_time': last_incident_time  # ADD THIS
    }

    return render_template('staff/commander_dashboard.html', stats=stats)

# ========== STAFF OPERATIONAL ROUTES ==========
@app.route('/staff/incidents')
@login_required
def staff_incidents():
    """View incidents with search and filtering"""
    # Get filter parameters from request
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    # Start with base query
    query = Incident.query

    # Apply search
    if search_query:
        query = query.filter(
            db.or_(
                Incident.title.ilike(f'%{search_query}%'),
                Incident.location.ilike(f'%{search_query}%'),
                Incident.description.ilike(f'%{search_query}%')
            )
        )

    # Apply status filter
    if status_filter:
        query = query.filter(Incident.status == status_filter)

    # Apply type filter
    if type_filter:
        query = query.filter(Incident.incident_type == type_filter)

    # Apply date filters
    if date_from:
        date_from_obj = datetime.datetime.strptime(date_from, '%Y-%m-%d')
        query = query.filter(Incident.reported_at >= date_from_obj)

    if date_to:
        date_to_obj = datetime.datetime.strptime(date_to, '%Y-%m-%d') + datetime.timedelta(days=1)
        query = query.filter(Incident.reported_at <= date_to_obj)

    # Get filtered incidents
    all_incidents = query.order_by(Incident.reported_at.desc()).all()

    # Get unique statuses and types for filter dropdowns
    all_statuses = db.session.query(Incident.status).distinct().all()
    all_types = db.session.query(Incident.incident_type).distinct().all()

    return render_template('staff/incidents.html',
                           incidents=all_incidents,
                           all_statuses=[s[0] for s in all_statuses],
                           all_types=[t[0] for t in all_types],
                           search_query=search_query,
                           status_filter=status_filter,
                           type_filter=type_filter,
                           date_from=date_from,
                           date_to=date_to)


@app.route('/staff/incidents/export')
@login_required
@role_required('commander')
def export_incidents():
    """Export incidents to CSV"""
    import csv
    from io import StringIO
    from flask import Response

    # Create CSV in memory
    si = StringIO()
    cw = csv.writer(si)

    # Write headers
    cw.writerow(['ID', 'Title', 'Location', 'Type', 'Status',
                 'Reported At', 'Reported By', 'Assigned Vehicle'])

    # Get all incidents
    incidents = Incident.query.order_by(Incident.reported_at.desc()).all()

    # Write data rows
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

    # Get the CSV string
    output = si.getvalue()
    si.close()

    # Return as downloadable file
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=incidents_export.csv"}
    )

@app.route('/staff/report_incident', methods=['GET', 'POST'])
@login_required
@role_required('dispatcher', 'commander')
def staff_report_incident():
    form = IncidentForm()
    vehicles = Vehicle.query.all()
    form.vehicle_id.choices = [(v.id, f"{v.type} - {v.location}") for v in vehicles]

    if not form.vehicle_id.choices:
        form.vehicle_id.choices = [(0, 'No vehicles available - Import data first!')]

    if form.validate_on_submit():
        if form.vehicle_id.data == 0:
            flash('Please import vehicles first!', 'danger')
            return redirect(url_for('staff_report_incident'))

        # Parse coordinates if provided
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
        return redirect(url_for('staff_incidents'))

    return render_template('staff/report_incident.html', form=form, vehicles=vehicles)


@app.route('/staff/incident/<int:incident_id>/quick-status', methods=['POST'])
@login_required
def quick_status_update(incident_id):
    """Quick AJAX status update"""
    incident = Incident.query.get_or_404(incident_id)
    new_status = request.json.get('status')

    if not new_status:
        return {'error': 'No status provided'}, 400

    # Create status update record
    update = StatusUpdate(
        incident_id=incident.id,
        user_id=session.get('user_id'),
        old_status=incident.status,
        new_status=new_status,
        comment='Quick update from list view'
    )
    db.session.add(update)

    # Update incident
    old_status = incident.status
    incident.status = new_status
    incident.updated_by = session.get('user_id')

    # Set timestamps
    now = datetime.datetime.utcnow()
    if new_status == 'Dispatched' and not incident.dispatched_at:
        incident.dispatched_at = now
    elif new_status == 'On Scene' and not incident.on_scene_at:
        incident.on_scene_at = now
    elif new_status == 'Closed' and not incident.closed_at:
        incident.closed_at = now

    db.session.commit()

    # Create notification
    create_notification(
        user_id=incident.reported_by,
        title=f'Incident #{incident.id} Status Updated',
        message=f'Status changed from {old_status} to {new_status}',
        incident_id=incident.id
    )

    return {'success': True, 'new_status': new_status}


# ========== COMMUNICATION ROUTES ==========
@app.route('/staff/incident/<int:incident_id>/chat', methods=['GET', 'POST'])
@login_required
def incident_chat(incident_id):
    """Incident-specific chat channel"""
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

        # Create notification for all users assigned to this incident
        if form.is_emergency.data:
            notify_users_about_incident(incident.id, form.message.data)
            flash('🚨 EMERGENCY BROADCAST SENT! 🚨', 'danger')
        else:
            flash('Message sent', 'success')

        return redirect(url_for('incident_chat', incident_id=incident.id))

    # Get messages for this incident
    messages = Message.query.filter_by(incident_id=incident.id).order_by(Message.created_at).all()

    return render_template('staff/incident_chat.html',
                           incident=incident,
                           form=form,
                           messages=messages,
                           templates=templates)


@app.route('/staff/incident/<int:incident_id>/chat/quick', methods=['POST'])
@login_required
def quick_message(incident_id):
    """Send a quick message using template"""
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


@app.route('/staff/incident/<int:incident_id>/radio', methods=['GET', 'POST'])
@login_required
def radio_log(incident_id):
    """Simulated radio log for incident"""
    incident = Incident.query.get_or_404(incident_id)
    form = RadioLogForm()

    if form.validate_on_submit():
        # Format as radio transmission
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
        return redirect(url_for('radio_log', incident_id=incident.id))

    # Get radio messages only
    radio_messages = Message.query.filter_by(
        incident_id=incident.id,
        message_type='radio'
    ).order_by(Message.created_at.desc()).all()

    return render_template('staff/radio_log.html',
                           incident=incident,
                           form=form,
                           radio_messages=radio_messages)


@app.route('/staff/templates')
@login_required
@role_required('dispatcher', 'commander')
def manage_templates():
    """Manage message templates"""
    templates = MessageTemplate.query.order_by(MessageTemplate.category, MessageTemplate.order).all()
    return render_template('staff/templates.html', templates=templates)


@app.route('/staff/templates/add', methods=['GET', 'POST'])
@login_required
@role_required('dispatcher', 'commander')
def add_template():
    """Add new message template"""
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
        return redirect(url_for('manage_templates'))

    return render_template('staff/template_form.html', form=form, title="Add Template")


@app.route('/staff/templates/<int:template_id>/delete', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def delete_template(template_id):
    """Delete a message template"""
    template = MessageTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()
    flash(f'Template "{template.name}" deleted.', 'warning')
    return redirect(url_for('manage_templates'))


def notify_users_about_incident(incident_id, message):
    """Notify all users involved in incident"""
    incident = Incident.query.get(incident_id)

    # Notify dispatcher who reported
    if incident.reported_by:
        create_notification(
            user_id=incident.reported_by,
            title=f'🚨 EMERGENCY - Incident #{incident.id}',
            message=message,
            incident_id=incident.id
        )

    # Notify firefighters on assigned vehicle
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

@app.route('/staff/firefighters')
@login_required
@role_required('dispatcher', 'commander')
def staff_firefighters():
    """View firefighters and vehicles with search"""
    # Get filter parameters
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    vehicle_filter = request.args.get('vehicle', '')

    # Firefighters query with filters
    ff_query = Firefighter.query

    if search_query:
        ff_query = ff_query.filter(
            db.or_(
                Firefighter.name.ilike(f'%{search_query}%'),
                Firefighter.rank.ilike(f'%{search_query}%')
            )
        )

    if status_filter:
        ff_query = ff_query.filter(Firefighter.status == status_filter)

    if vehicle_filter:
        if vehicle_filter == 'unassigned':
            ff_query = ff_query.filter(Firefighter.vehicle_id.is_(None))
        else:
            ff_query = ff_query.filter(Firefighter.vehicle_id == vehicle_filter)

    all_firefighters = ff_query.all()

    # Vehicles query with search
    v_query = Vehicle.query

    if search_query:
        v_query = v_query.filter(
            db.or_(
                Vehicle.type.ilike(f'%{search_query}%'),
                Vehicle.location.ilike(f'%{search_query}%')
            )
        )

    all_vehicles = v_query.all()

    # Get unique statuses for filter
    all_statuses = ['available', 'on_duty', 'off_duty', 'training', 'sick', 'vacation']

    return render_template('staff/firefighters.html',
                           firefighters=all_firefighters,
                           vehicles=all_vehicles,
                           all_statuses=all_statuses,
                           search_query=search_query,
                           status_filter=status_filter,
                           vehicle_filter=vehicle_filter)


@app.route('/staff/import-data')
@login_required
@role_required('dispatcher', 'commander')
def staff_import_data():
    try:
        from data import firefighters, vehicles

        Firefighter.query.delete()
        Vehicle.query.delete()

        for v in vehicles:
            vehicle = Vehicle(
                id=v['id'],
                type=v['type'],
                location=v['location'],
                latitude=v.get('latitude'),
                longitude=v.get('longitude'),
                status=v.get('status', 'station')
            )
            db.session.add(vehicle)

        db.session.commit()

        for f in firefighters:
            firefighter = Firefighter(
                id=f['id'],
                name=f['name'],
                rank=f['rank'],
                status=f['status'],
                vehicle_id=f['vehicle_id']
            )
            db.session.add(firefighter)

        db.session.commit()

        flash(f'Successfully imported {len(vehicles)} vehicles and {len(firefighters)} firefighters!', 'success')

    except Exception as e:
        flash(f'Error importing data: {str(e)}', 'danger')
        print(f"Error: {e}")

    return redirect(url_for('staff_firefighters'))


#@app.route('/staff/import-equipment')
#@login_required
#@role_required('dispatcher', 'commander')
#def import_equipment():
    """Import default equipment"""
    try:
        from utils import create_default_equipment
        create_default_equipment()
        flash('Default equipment added successfully!', 'success')
    except Exception as e:
        flash(f'Error importing equipment: {str(e)}', 'danger')
        print(f"Error: {e}")

    return redirect(url_for('equipment_list'))

@app.route('/staff/incident/<int:incident_id>/pdf')
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def incident_pdf(incident_id):
    """Generate PDF report for an incident"""
    incident = Incident.query.get_or_404(incident_id)

    try:
        # Generate PDF
        pdf_buffer = generate_incident_pdf(incident)

        # Send file
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"incident_{incident_id}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('incident_detail', incident_id=incident_id))


@app.route('/staff/incident/<int:incident_id>/pdf/view')
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def view_incident_pdf(incident_id):
    """View PDF in browser instead of downloading"""
    incident = Incident.query.get_or_404(incident_id)

    try:
        pdf_buffer = generate_incident_pdf(incident)
        return send_file(
            pdf_buffer,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('incident_detail', incident_id=incident_id))

@app.route('/staff/logout')
def staff_logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('staff_login'))


@app.route('/create-first-commander')
def create_first_commander():
    existing = UserModel.query.filter_by(role='commander').first()
    if existing:
        return "Commander already exists!"

    commander = UserModel(
        username='commander',
        email='c@fire.bg',
        password=generate_password_hash('123456'),
        role='commander'
    )
    db.session.add(commander)
    db.session.commit()
    return "Commander created! Email: c@fire.bg, Password: 123456"

# ========== DATABASE INIT ==========
with app.app_context():
    db.create_all()
    print("Database tables created/updated!")

    from utils import create_default_templates
    create_default_templates()

if __name__ == '__main__':
    app.run(debug=True)