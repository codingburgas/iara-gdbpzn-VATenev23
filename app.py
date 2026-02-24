from flask import Flask, render_template, redirect, url_for, flash, session
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import datetime  # This is correct

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

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    incident_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Reported')
    reported_by = db.Column(db.Integer, db.ForeignKey('user_model.id'))
    reported_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)  # Fixed!

    # Relationship
    reporter = db.relationship('UserModel', backref='incidents')

# ========== FORMS ==========
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    submit = SubmitField("Register")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class IncidentForm(FlaskForm):
    title = StringField('Incident Title', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    incident_type = SelectField('Incident Type',
                               choices=[('fire', 'Fire'),
                                       ('rescue', 'Rescue'),
                                       ('accident', 'Car Accident'),
                                       ('hazmat', 'Hazardous Materials'),
                                       ('other', 'Other')],
                               validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    submit = SubmitField('Report Incident')

# ========== ROUTES ==========
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = UserModel.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(form.password.data)
        new_user = UserModel(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = UserModel.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password, form.password.data):
            session['user_id'] = user.id
            session['user_name'] = user.username
            session['logged_in'] = True

            flash('Login successful! Welcome back, ' + user.username, 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password!', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully!', 'info')
    return redirect(url_for('home'))

@app.route('/incidents')
def incidents():
    all_incidents = Incident.query.order_by(Incident.reported_at.desc()).all()
    return render_template('incidents.html', incidents=all_incidents)

@app.route('/report_incident', methods=['GET', 'POST'])
def report_incident():
    form = IncidentForm()
    if form.validate_on_submit():
        if not session.get('logged_in'):
            flash('Please login to report an incident.', 'warning')
            return redirect(url_for('login'))

        new_incident = Incident(
            title=form.title.data,
            location=form.location.data,
            incident_type=form.incident_type.data,
            description=form.description.data,
            reported_by=session.get('user_id'),
            status='Reported'
        )

        db.session.add(new_incident)
        db.session.commit()

        flash('Incident reported successfully!', 'success')
        return redirect(url_for('incidents'))

    return render_template('report_incident.html', form=form)

# ========== DATABASE INIT ==========
with app.app_context():
    db.create_all()
    print("Database tables created/updated!")

if __name__ == '__main__':
    app.run(debug=True)