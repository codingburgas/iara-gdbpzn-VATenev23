from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField
from wtforms.validators import DataRequired

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