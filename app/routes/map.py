from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from app import db
from app.models.incident import Incident
from app.models.vehicle import Vehicle
from app.models.map_annotation import MapAnnotation
from app.forms.incident_forms import MapAnnotationForm
from app.utils import (login_required, role_required, create_notification,
                       vehicle_live_position, process_vehicle_arrivals)
import datetime
import json

map_bp = Blueprint('map', __name__)


@map_bp.route('/staff/map')
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def incident_map():
    incidents = Incident.query.filter(Incident.status != 'Closed').all()
    vehicles = Vehicle.query.all()

    return render_template('staff/map/incidents.html',
                           incidents=incidents,
                           vehicles=vehicles)


@map_bp.route('/api/vehicles/locations')
@login_required
def vehicle_locations():
    """Live vehicle positions for the map auto-refresh.

    For en-route vehicles the current position is computed from the stored road
    route and elapsed time, so units keep moving across reloads. When a unit
    reaches the incident it is persisted as 'on_scene'."""
    # Persist any vehicles that have reached their incident.
    process_vehicle_arrivals()

    vehicles = Vehicle.query.filter(
        Vehicle.latitude.isnot(None),
        Vehicle.longitude.isnot(None)
    ).all()

    result = []
    for v in vehicles:
        entry = {
            'id': v.id,
            'type': v.type,
            'lat': v.latitude,
            'lng': v.longitude,
            'status': v.status,
            'location': v.location,
            'incident_id': v.current_incident_id,
            'crew': [{'name': f.name, 'rank': f.rank} for f in v.firefighters],
            'route': None,
        }

        live = vehicle_live_position(v)
        if live:  # still en route (arrivals were already cleared above)
            entry.update({
                'lat': live['lat'],
                'lng': live['lng'],
                'status': 'en_route',
                'route': json.loads(v.route_polyline),
                'progress': live['progress'],
                'total_seconds': v.route_total_seconds,
                'real_seconds': v.route_real_seconds,
                'eta_seconds': live['eta_seconds'],
                'distance_m': v.route_distance_m,
                'dest': [v.route_dest_lat, v.route_dest_lng],
            })

        result.append(entry)

    return jsonify({'vehicles': result, 'server_time': datetime.datetime.utcnow().isoformat()})


@map_bp.route('/staff/map/incident/<int:incident_id>')
@login_required
def incident_detail_map(incident_id):
    """Map view for a specific incident"""
    incident = Incident.query.get_or_404(incident_id)
    annotations = MapAnnotation.query.filter_by(incident_id=incident_id).all()
    vehicles = Vehicle.query.filter_by(current_incident_id=incident_id).all()

    return render_template('staff/map/incident_detail_map.html',
                           incident=incident,
                           annotations=annotations,
                           vehicles=vehicles)


@map_bp.route('/staff/map/annotations/<int:incident_id>', methods=['GET', 'POST'])
@login_required
@role_required('dispatcher', 'commander')
def manage_annotations(incident_id):
    """Get or create map annotations"""
    incident = Incident.query.get_or_404(incident_id)

    if request.method == 'GET':
        annotations = MapAnnotation.query.filter_by(incident_id=incident_id).all()
        result = []
        for ann in annotations:
            result.append({
                'id': ann.id,
                'type': ann.annotation_type,
                'geometry': json.loads(ann.geometry),
                'color': ann.color,
                'description': ann.description,
                'created_at': ann.created_at.isoformat(),
                'user': ann.user.username
            })
        return jsonify(result)

    elif request.method == 'POST':
        data = request.get_json()

        annotation = MapAnnotation(
            incident_id=incident_id,
            user_id=session.get('user_id'),
            annotation_type=data.get('type'),
            geometry=json.dumps(data.get('geometry')),
            color=data.get('color', '#ff0000'),
            description=data.get('description')
        )
        db.session.add(annotation)
        db.session.commit()

        # Notify other users
        create_notification(
            user_id=session.get('user_id'),
            title=f'Map Updated',
            message=f'New {annotation.annotation_type} annotation added to incident #{incident_id}',
            incident_id=incident_id
        )

        return jsonify({
            'success': True,
            'id': annotation.id,
            'message': 'Annotation saved'
        })


@map_bp.route('/staff/map/annotations/<int:annotation_id>', methods=['DELETE'])
@login_required
@role_required('dispatcher', 'commander')
def delete_annotation(annotation_id):
    """Delete a map annotation"""
    annotation = MapAnnotation.query.get_or_404(annotation_id)
    incident_id = annotation.incident_id

    db.session.delete(annotation)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Annotation deleted'})


@map_bp.route('/staff/map/wind-direction', methods=['POST'])
@login_required
@role_required('dispatcher', 'commander')
def update_wind_direction():
    """Update wind direction for incident"""
    data = request.get_json()
    incident_id = data.get('incident_id')
    direction = data.get('direction')  # degrees
    speed = data.get('speed')  # km/h

    incident = Incident.query.get_or_404(incident_id)

    # Save wind data to incident or separate model
    incident.wind_direction = direction
    incident.wind_speed = speed
    db.session.commit()

    return jsonify({'success': True})