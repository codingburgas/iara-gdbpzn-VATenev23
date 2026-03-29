from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models.fire_station import FireStation
from app.forms.station_forms import FireStationForm
from app.utils import login_required, role_required

stations_bp = Blueprint('stations', __name__)

@stations_bp.route('/staff/stations')
@login_required
@role_required('commander', 'dispatcher')
def list_stations():
    stations = FireStation.query.all()
    return render_template('staff/stations/list.html', stations=stations)

@stations_bp.route('/staff/station/add', methods=['GET', 'POST'])
@login_required
@role_required('commander')
def add_station():
    form = FireStationForm()
    if form.validate_on_submit():
        station = FireStation(
            name=form.name.data,
            address=form.address.data,
            phone=form.phone.data,
            email=form.email.data,
            max_vehicles=form.max_vehicles.data,
            max_personnel=form.max_personnel.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            is_active=form.is_active.data
        )
        db.session.add(station)
        db.session.commit()
        flash(f'Fire Station {station.name} added successfully!', 'success')
        return redirect(url_for('stations.list_stations'))
    
    return render_template('staff/stations/form.html', form=form, title="Add Fire Station")

@stations_bp.route('/staff/station/<int:station_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('commander')
def edit_station(station_id):
    station = FireStation.query.get_or_404(station_id)
    form = FireStationForm(obj=station)
    if form.validate_on_submit():
        form.populate_obj(station)
        db.session.commit()
        flash(f'Fire Station {station.name} updated successfully!', 'success')
        return redirect(url_for('stations.list_stations'))
    
    return render_template('staff/stations/form.html', form=form, title="Edit Fire Station", station=station)

@stations_bp.route('/staff/station/<int:station_id>/delete', methods=['POST'])
@login_required
@role_required('commander')
def delete_station(station_id):
    station = FireStation.query.get_or_404(station_id)
    
    if station.vehicles or station.personnel:
        flash(f'Cannot delete {station.name} because it has assigned vehicles or personnel.', 'danger')
        return redirect(url_for('stations.list_stations'))
        
    db.session.delete(station)
    db.session.commit()
    flash(f'Fire Station {station.name} deleted.', 'success')
    return redirect(url_for('stations.list_stations'))

@stations_bp.route('/staff/station/<int:station_id>')
@login_required
@role_required('commander', 'dispatcher')
def detail(station_id):
    station = FireStation.query.get_or_404(station_id)
    return render_template('staff/stations/detail.html', station=station)
