from flask import Flask, render_template, redirect, url_for, flash, session, request
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import requests
import datetime

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)


# ========== MODELS ==========
class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), default='public')  # public, dispatcher, firefighter, commander


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    location = db.Column(db.String(200))
    firefighters = db.relationship('Firefighter', backref='assigned_vehicle', lazy=True)


class Firefighter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rank = db.Column(db.String(50))
    status = db.Column(db.String(20), default='available')
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)


# ========== FORMS ==========
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    role = SelectField('I am a...',
                       choices=[('public', 'Civilian / Public'),
                                ('firefighter', 'Firefighter'),
                                ('dispatcher', 'Dispatcher'),
                                ('commander', 'Commander')],
                       validators=[DataRequired()])
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    incident_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Reported')
    reported_by = db.Column(db.Integer, db.ForeignKey('user_model.id'))
    reported_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    assigned_vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    assigned_vehicle = db.relationship('Vehicle')
    reporter = db.relationship('UserModel', backref='incidents')
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)


class IncidentForm(FlaskForm):
    title = StringField('Incident Title', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    latitude = StringField('Latitude', validators=[Optional()])  # Add this
    longitude = StringField('Longitude', validators=[Optional()])  # Add this
    incident_type = SelectField('Incident Type',
                                choices=[('fire', 'Fire'),
                                         ('rescue', 'Rescue'),
                                         ('accident', 'Car Accident'),
                                         ('hazmat', 'Hazardous Materials'),
                                         ('other', 'Other')],
                                validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    vehicle_id = SelectField('Assign Vehicle', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Report Incident')

# ========== DECORATORS ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please login to access the staff portal.', 'warning')
            return redirect(url_for('staff_login'))
        return f(*args, **kwargs)

    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                flash('Please login to access the staff portal.', 'warning')
                return redirect(url_for('staff_login'))
            if session.get('user_role') not in roles:
                flash('Unauthorized access. This incident has been logged.', 'danger')
                return redirect(url_for('staff_dashboard'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator

def geocode_address(address):
    """Convert address to lat/lon using OpenStreetMap Nominatim"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': address,
            'format': 'json',
            'limit': 1
        }
        headers = {
            'User-Agent': 'BurgasFireDepartment/1.0'
        }
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except:
        pass
    return None, None

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
def staff_register():
    """Registration for staff (in real system, this would be admin-only)"""
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = UserModel.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('staff_register'))

        hashed_password = generate_password_hash(form.password.data)
        new_user = UserModel(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            role=form.role.data
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now login.', 'success')
        return redirect(url_for('staff_login'))
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

@app.route('/dispatcher/dashboard')
@login_required
@role_required('dispatcher', 'commander')
def dispatcher_dashboard():
    active_incidents = Incident.query.filter(Incident.status != 'Closed').count()
    available_vehicles = Vehicle.query.count()  # You'd add status later
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
    stats = {
        'total_incidents': Incident.query.count(),
        'active_incidents': Incident.query.filter(Incident.status != 'Closed').count(),
        'available_firefighters': Firefighter.query.filter_by(status='available').count(),
        'total_vehicles': Vehicle.query.count(),
        'total_users': UserModel.query.count()
    }

    return render_template('staff/commander_dashboard.html', stats=stats)


# ========== STAFF OPERATIONAL ROUTES ==========
@app.route('/staff/incidents')
@login_required
def staff_incidents():
    all_incidents = Incident.query.order_by(Incident.reported_at.desc()).all()
    return render_template('staff/incidents.html', incidents=all_incidents)


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


@app.route('/staff/firefighters')
@login_required
@role_required('dispatcher', 'commander')
def staff_firefighters():
    all_firefighters = Firefighter.query.all()
    all_vehicles = Vehicle.query.all()
    return render_template('staff/firefighters.html',
                           firefighters=all_firefighters,
                           vehicles=all_vehicles)


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
                location=v['location']
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


@app.route('/staff/logout')
def staff_logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('staff_login'))


# ========== DATABASE INIT ==========
with app.app_context():
    db.create_all()
    print("Database tables created/updated!")

if __name__ == '__main__':
    app.run(debug=True)