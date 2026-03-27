from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Optional

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