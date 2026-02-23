from flask import Flask, render_template, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash  # Add this line

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    submit = SubmitField("Register")

class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class IncidentForm(FlaskForm):
    title = StringField('Incident Title', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    incident_type = StringField('Type (Fire/Rescue/etc)', validators=[DataRequired()])
    description = StringField('Description')
    submit = SubmitField('Report Incident')
@app.route('/')
def home():  # put application's code here
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = UserModel.query.filter_by(email=form.email.data).first()
        if existing_user:
            return "Email already registered! Go back and try again."

        hashed_password = generate_password_hash(form.password.data)
        new_user = UserModel(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password # We'll hash this later!
        )
        # Add to database
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('home'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Find user by email
        user = UserModel.query.filter_by(email=form.email.data).first()

        # Check if user exists and password matches
        if user and check_password_hash(user.password, form.password.data):
            # In the future, we'll set up session here
            return redirect(url_for('home'))
        else:
            return "Invalid email or password. Go back and try again."

    return render_template('login.html', form=form)
@app.route('/incidents')
def incidents():
    return render_template('incidents.html')
@app.route('/report_incident', methods=['GET', 'POST'])
def report_incident():
    form = IncidentForm()
    if form.validate_on_submit():
        return redirect(url_for('incidents'))
    return render_template('report_incident.html', form=form)

with app.app_context():
    db.create_all()
    print("Database created!")
if __name__ == '__main__':
    app.run(debug=True)
