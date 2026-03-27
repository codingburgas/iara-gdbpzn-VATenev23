from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, Optional


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

    # Firefighter specific fields (only shown if role is firefighter)
    full_name = StringField('Full Name', validators=[Optional()])
    rank = SelectField('Rank',
                       choices=[('Firefighter', 'Firefighter'),
                                ('Driver', 'Driver'),
                                ('Commander', 'Commander'),
                                ('Chief', 'Chief')],
                       validators=[Optional()])
    phone = StringField('Phone Number', validators=[Optional()])
    employee_id = StringField('Employee ID', validators=[Optional()])

    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")