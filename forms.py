from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, BooleanField, IntegerField, DateTimeField
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

    # NEW: Firefighter specific fields (only shown if role is firefighter)
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

class MessageForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired()])
    is_emergency = BooleanField('Emergency Broadcast', default=False)
    submit = SubmitField('Send')


class RadioLogForm(FlaskForm):
    message = TextAreaField('Radio Transmission', validators=[DataRequired()])
    unit = StringField('Unit/Callsign', validators=[DataRequired()])
    submit = SubmitField('Log Transmission')


class TemplateForm(FlaskForm):
    name = StringField('Template Name', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    category = SelectField('Category',
                          choices=[('general', 'General'),
                                   ('status', 'Status Update'),
                                   ('request', 'Request'),
                                   ('emergency', 'Emergency')],
                          validators=[DataRequired()])
    submit = SubmitField('Save Template')

class VolunteerApplicationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=6, max=20)])
    age = IntegerField('Age', validators=[DataRequired()])
    address = StringField('Address', validators=[Optional(), Length(max=200)])
    motivation = TextAreaField('Why do you want to volunteer?', validators=[Optional()])
    experience = TextAreaField('Previous experience (if any)', validators=[Optional()])
    submit = SubmitField('Submit Application')


class ApplicationReviewForm(FlaskForm):
    status = SelectField('Status',
                        choices=[('pending', 'Pending'),
                                ('approved', '✅ Approved'),
                                ('rejected', '❌ Rejected'),
                                ('trained', '🎓 Trained')],
                        validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Update Status')


class TrainingForm(FlaskForm):
    title = StringField('Training Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    date = DateTimeField('Date and Time', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    duration_hours = IntegerField('Duration (hours)', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    max_participants = IntegerField('Max Participants', validators=[DataRequired()])
    instructor = StringField('Instructor Name', validators=[Optional()])
    submit = SubmitField('Schedule Training')