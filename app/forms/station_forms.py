from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length

class FireStationForm(FlaskForm):
    name = StringField('Station Name', validators=[DataRequired(), Length(max=100)])
    address = StringField('Address', validators=[DataRequired(), Length(max=200)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    email = StringField('Email Address', validators=[Optional(), Email(), Length(max=100)])
    
    max_vehicles = IntegerField('Max Vehicles Capacity', default=5, validators=[Optional()])
    max_personnel = IntegerField('Max Personnel Capacity', default=20, validators=[Optional()])
    
    latitude = FloatField('Latitude', validators=[Optional()])
    longitude = FloatField('Longitude', validators=[Optional()])
    
    is_active = BooleanField('Station is Active', default=True)
    
    submit = SubmitField('Save Station')
