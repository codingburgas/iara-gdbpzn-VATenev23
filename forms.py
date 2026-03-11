from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

# ========== AUTH FORMS ==========
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


# ========== INCIDENT FORMS ==========
class IncidentForm(FlaskForm):
    title = StringField('Incident Title', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    latitude = StringField('Latitude', validators=[Optional()])
    longitude = StringField('Longitude', validators=[Optional()])
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


class StatusUpdateForm(FlaskForm):
    new_status = SelectField('New Status',
                            choices=[('Reported', '🚨 Reported'),
                                    ('Dispatched', '🚒 Dispatched'),
                                    ('On Scene', '🔥 On Scene'),
                                    ('Contained', '📦 Contained'),
                                    ('Closed', '✅ Closed')],
                            validators=[DataRequired()])
    comment = TextAreaField('Comment (optional)', validators=[Optional()])
    submit = SubmitField('Update Status')


# ========== SHIFT FORMS ==========
class ShiftStartForm(FlaskForm):
    firefighter_id = SelectField('Firefighter', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Start Shift')


class ShiftEndForm(FlaskForm):
    submit = SubmitField('End Shift')


class FirefighterStatusForm(FlaskForm):
    status = SelectField('Status',
                        choices=[('available', '✅ Available'),
                                ('on_duty', '🚒 On Duty'),
                                ('off_duty', '💤 Off Duty'),
                                ('training', '📚 Training'),
                                ('sick', '🤒 Sick'),
                                ('vacation', '🏖️ Vacation')],
                        validators=[DataRequired()])
    submit = SubmitField('Update Status')

class EquipmentForm(FlaskForm):
    name = StringField('Equipment Name', validators=[DataRequired()])
    type = SelectField('Type',
                       choices=[('tool', '🔧 Tool'),
                                ('hose', '📏 Hose'),
                                ('extinguisher', '🧯 Extinguisher'),
                                ('gear', '🦺 Protective Gear'),
                                ('medical', '🚑 Medical Equipment'),
                                ('other', '📦 Other')],
                       validators=[DataRequired()])
    model = StringField('Model', validators=[Optional()])
    serial_number = StringField('Serial Number', validators=[Optional()])
    status = SelectField('Status',
                        choices=[('available', '✅ Available'),
                                ('in_use', '🔄 In Use'),
                                ('maintenance', '🔧 Maintenance'),
                                ('damaged', '⚠️ Damaged')],
                        validators=[DataRequired()])
    condition = SelectField('Condition',
                           choices=[('good', '✅ Good'),
                                   ('fair', '🟡 Fair'),
                                   ('poor', '🟠 Poor'),
                                   ('needs_repair', '🔴 Needs Repair')],
                           validators=[DataRequired()])
    vehicle_id = SelectField('Assigned Vehicle', coerce=int, validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Add Equipment')

class EquipmentCheckoutForm(FlaskForm):
    equipment_id = SelectField('Equipment', coerce=int, validators=[DataRequired()])
    incident_id = SelectField('Incident', coerce=int, validators=[Optional()])
    firefighter_id = SelectField('Firefighter', coerce=int, validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Check Out Equipment')

class EquipmentReturnForm(FlaskForm):
    condition = SelectField('Condition After Use',
                           choices=[('good', '✅ Good'),
                                   ('fair', '🟡 Fair'),
                                   ('needs_repair', '🔴 Needs Repair'),
                                   ('damaged', '⚠️ Damaged')],
                           validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Return Equipment')