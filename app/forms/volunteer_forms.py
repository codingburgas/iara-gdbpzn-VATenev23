from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField, IntegerField, DateTimeField
from wtforms.validators import DataRequired, Email, Length, Optional

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