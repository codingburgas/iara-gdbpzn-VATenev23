from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.forms.volunteer_forms import VolunteerApplicationForm
from app.models.volunteer import VolunteerApplication
from app.models.incident import Incident
from app.models.vehicle import Vehicle
from app.utils import vehicle_live_position, process_vehicle_arrivals
from app import db
import datetime
import json

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def home():
    return render_template('public/index.html')


@public_bp.route('/news')
def news():
    return render_template('public/news.html')


@public_bp.route('/safety-tips')
def safety_tips():
    return render_template('public/safety_tips.html')


@public_bp.route('/contact')
def contact():
    return render_template('public/contact.html')


@public_bp.route('/volunteer')
def volunteer():
    return render_template('public/volunteer.html')


@public_bp.route('/non-emergency', methods=['GET', 'POST'])
def non_emergency():
    if request.method == 'POST':
        flash('Thank you for your report. We will review it within 24 hours.', 'success')
        return redirect(url_for('public.non_emergency'))
    return render_template('public/non_emergency.html')


@public_bp.route('/live')
def live_operations():
    """Public-facing live map: shows the community where the service is currently
    responding. No login required, no personally-identifiable detail exposed."""
    return render_template('public/live.html')


@public_bp.route('/api/public/operations')
def public_operations():
    """Anonymized live feed for the public map.

    Privacy filter at the boundary: crew names, vehicle IDs/types, SOS detail
    and internal status notes are stripped. Locations are kept (so the public
    can see road closures and active scenes) but addresses are coarsened to
    the most informative two address components."""
    # Run the same arrival logic the staff endpoints do, so on-scene flips
    # happen even if no staff is watching.
    process_vehicle_arrivals()

    def coarsen(loc):
        if not loc:
            return ''
        parts = [p.strip() for p in loc.split(',') if p.strip()]
        # Take up to the first two parts (street / area) — drop city/country tail.
        return ', '.join(parts[:2])

    active = (Incident.query.filter(Incident.status != 'Closed')
              .order_by(Incident.reported_at.desc()).all())

    incidents = []
    for inc in active:
        incidents.append({
            'id': inc.id,                          # OK — anonymous reference number
            'type': inc.incident_type,             # OK — fire / rescue / etc
            'status': inc.status,                  # OK — Reported / Dispatched / On Scene
            'location': coarsen(inc.location),     # coarsened
            'lat': inc.latitude,
            'lng': inc.longitude,
            'reported_at': inc.reported_at.isoformat() if inc.reported_at else None,
            'units_assigned': 1 if inc.assigned_vehicle else 0,
        })

    units = []
    for v in Vehicle.query.filter(Vehicle.status.in_(['en_route', 'on_scene'])).all():
        live = vehicle_live_position(v)
        unit = {
            'lat': live['lat'] if live else v.latitude,
            'lng': live['lng'] if live else v.longitude,
            'status': v.status,
            # NB: no crew, no vehicle id, no vehicle type.
        }
        if live:
            unit['route'] = json.loads(v.route_polyline)
            unit['progress'] = live['progress']
            unit['total_seconds'] = v.route_total_seconds
        units.append(unit)

    # Public-friendly stats
    deployed = sum(1 for v in Vehicle.query.all()
                   if v.status in ('en_route', 'on_scene'))

    return jsonify({
        'incidents': incidents,
        'units': units,
        'stats': {
            'active_incidents': len(incidents),
            'units_deployed': deployed,
        },
        'server_time': datetime.datetime.utcnow().isoformat(),
    })


@public_bp.route('/volunteer/apply', methods=['GET', 'POST'])
def volunteer_apply():
    form = VolunteerApplicationForm()

    if form.validate_on_submit():
        application = VolunteerApplication(
            full_name=form.full_name.data,
            email=form.email.data,
            phone=form.phone.data,
            age=form.age.data,
            address=form.address.data,
            motivation=form.motivation.data,
            experience=form.experience.data,
            status='pending'
        )
        db.session.add(application)
        db.session.commit()

        flash('Thank you for your interest! We will review your application and contact you soon.', 'success')
        return redirect(url_for('public.home'))

    return render_template('public/volunteer_apply.html', form=form)