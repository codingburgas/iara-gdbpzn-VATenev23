from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, SelectField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Optional

class MessageForm(FlaskForm):
    # Message text is optional so a photo can be sent on its own; the route
    # enforces that at least one of (text, photo) is provided.
    message = TextAreaField('Message', validators=[Optional()])
    photo = FileField('Photo', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only (jpg, png, gif, webp).')
    ])
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