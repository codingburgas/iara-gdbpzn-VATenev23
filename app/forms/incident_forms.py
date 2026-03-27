from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Optional

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
class TaskForm(FlaskForm):
    title = StringField('Task Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    priority = SelectField('Priority',
                          choices=[('low', '🟢 Low'),
                                   ('normal', '🔵 Normal'),
                                   ('high', '🟠 High'),
                                   ('urgent', '🔴 Urgent')],
                          validators=[DataRequired()])
    deadline = StringField('Deadline (YYYY-MM-DD HH:MM)', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Create Task')


class TaskStatusForm(FlaskForm):
    status = SelectField('Status',
                        choices=[('pending', '⏳ Pending'),
                                 ('in_progress', '🔄 In Progress'),
                                 ('completed', '✅ Completed'),
                                 ('cancelled', '❌ Cancelled')],
                        validators=[DataRequired()])
    notes = TextAreaField('Completion Notes', validators=[Optional()])
    submit = SubmitField('Update Status')