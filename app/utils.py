from functools import wraps
from flask import flash, redirect, url_for, session, send_file, current_app
import requests
import datetime
import io
import json
import math
from app import db
from app.models.notification import Notification
from app.models.equipment import Equipment, EquipmentAssignment
from app.models.vehicle import Vehicle
from app.models.communication import Message, MessageTemplate

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


# ========== DECORATORS ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please login to access the staff portal.', 'warning')
            return redirect(url_for('auth.staff_login'))
        return f(*args, **kwargs)

    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                flash('Please login to access the staff portal.', 'warning')
                return redirect(url_for('auth.staff_login'))
            if session.get('user_role') not in roles:
                flash('Unauthorized access. This incident has been logged.', 'danger')
                return redirect(url_for('dashboard.staff_dashboard'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ========== TEMPLATE FILTERS ==========
def duration_filter(start_time, end_time=None):
    """Calculate duration between two times"""
    if not end_time:
        end_time = datetime.datetime.utcnow()
    delta = end_time - start_time
    hours = int(delta.total_seconds() / 3600)
    minutes = int((delta.total_seconds() % 3600) / 60)
    return f"{hours}h {minutes}m"


# ========== HELPER FUNCTIONS ==========
def geocode_address(address):
    """Convert address to lat/lon using OpenStreetMap Nominatim"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': address,
            'format': 'json',
            'limit': 1
        }
        headers = {
            'User-Agent': 'BurgasFireDepartment/1.0'
        }
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except:
        pass
    return None, None


# ========== LIVE ROUTING (OSRM / OpenStreetMap, no API key) ==========

OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"
# Real driving time is compressed so dispatches are watchable during a demo,
# while the displayed ETA still reflects the true OSRM travel time.
ROUTE_SIM_SPEEDUP = 6.0
ROUTE_MIN_SECONDS = 25.0
ROUTE_MAX_SECONDS = 150.0


def haversine_m(lat1, lng1, lat2, lng2):
    """Great-circle distance in meters."""
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def get_route(start_lat, start_lng, end_lat, end_lng):
    """Driving route between two points via OSRM (OpenStreetMap). No API key.
    Returns {polyline: [[lat,lng],...], duration_seconds, distance_m}.
    Falls back to a straight line if the routing service is unreachable."""
    try:
        url = f"{OSRM_BASE}/{start_lng},{start_lat};{end_lng},{end_lat}"
        params = {'overview': 'full', 'geometries': 'geojson'}
        response = requests.get(url, params=params, timeout=6)
        data = response.json()
        if data.get('code') == 'Ok' and data.get('routes'):
            route = data['routes'][0]
            coords = route['geometry']['coordinates']  # OSRM returns [lng, lat]
            polyline = [[c[1], c[0]] for c in coords]
            return {
                'polyline': polyline,
                'duration_seconds': float(route['duration']),
                'distance_m': float(route['distance']),
            }
    except Exception as e:
        print(f"OSRM routing failed, using straight line: {e}")

    dist = haversine_m(start_lat, start_lng, end_lat, end_lng)
    return {
        'polyline': [[start_lat, start_lng], [end_lat, end_lng]],
        'duration_seconds': max(30.0, dist / 1000.0 / 40.0 * 3600.0),  # ~40 km/h estimate
        'distance_m': dist,
    }


def start_vehicle_route(vehicle, dest_lat, dest_lng):
    """Compute and store a live road route from the vehicle's current position
    to a destination and mark it en route. The caller commits the session."""
    if vehicle.latitude is None or vehicle.longitude is None:
        vehicle.latitude, vehicle.longitude = 42.5063, 27.4678  # central station default

    route = get_route(vehicle.latitude, vehicle.longitude, dest_lat, dest_lng)
    real = route['duration_seconds']
    sim = min(ROUTE_MAX_SECONDS, max(ROUTE_MIN_SECONDS, real / ROUTE_SIM_SPEEDUP))

    vehicle.route_polyline = json.dumps(route['polyline'])
    vehicle.route_real_seconds = real
    vehicle.route_total_seconds = sim
    vehicle.route_distance_m = route['distance_m']
    vehicle.route_started_at = datetime.datetime.utcnow()
    vehicle.route_dest_lat = dest_lat
    vehicle.route_dest_lng = dest_lng
    vehicle.status = 'en_route'
    return route


def _point_along(poly, frac):
    """Point at fractional arc-length along a [[lat,lng],...] polyline."""
    if not poly:
        return None, None
    if len(poly) == 1 or frac <= 0:
        return poly[0][0], poly[0][1]
    if frac >= 1:
        return poly[-1][0], poly[-1][1]

    seglen = []
    total = 0.0
    for i in range(len(poly) - 1):
        d = haversine_m(poly[i][0], poly[i][1], poly[i + 1][0], poly[i + 1][1])
        seglen.append(d)
        total += d
    if total == 0:
        return poly[0][0], poly[0][1]

    target = frac * total
    acc = 0.0
    for i, d in enumerate(seglen):
        if acc + d >= target:
            t = (target - acc) / d if d else 0
            lat = poly[i][0] + (poly[i + 1][0] - poly[i][0]) * t
            lng = poly[i][1] + (poly[i + 1][1] - poly[i][1]) * t
            return lat, lng
        acc += d
    return poly[-1][0], poly[-1][1]


def vehicle_live_position(vehicle):
    """Current interpolated position + progress for an en-route vehicle, based on
    elapsed wall-clock time. Returns None if the vehicle has no active route."""
    if not (vehicle.route_polyline and vehicle.route_started_at and vehicle.route_total_seconds):
        return None
    elapsed = (datetime.datetime.utcnow() - vehicle.route_started_at).total_seconds()
    progress = elapsed / vehicle.route_total_seconds if vehicle.route_total_seconds else 1.0
    progress = max(0.0, min(1.0, progress))
    poly = json.loads(vehicle.route_polyline)
    lat, lng = _point_along(poly, progress)
    eta_real = max(0.0, (vehicle.route_real_seconds or 0) * (1 - progress))
    return {
        'lat': lat,
        'lng': lng,
        'progress': progress,
        'eta_seconds': eta_real,
        'arrived': progress >= 1.0,
    }


def clear_vehicle_route(vehicle):
    """Wipe live-route fields (e.g. on arrival or when returning to station)."""
    vehicle.route_polyline = None
    vehicle.route_started_at = None
    vehicle.route_total_seconds = None
    vehicle.route_real_seconds = None
    vehicle.route_distance_m = None
    vehicle.route_dest_lat = None
    vehicle.route_dest_lng = None


def process_vehicle_arrivals():
    """Advance any en-route vehicle that has reached its destination: snap it to
    the incident, mark it on scene, flip the incident to 'On Scene' and log it.

    Shared by every live endpoint so arrivals are detected by whichever board the
    user happens to have open. Returns the number of arrivals processed."""
    from app.models.incident import StatusUpdate
    from app.models.user import UserModel

    vehicles = Vehicle.query.filter(Vehicle.route_polyline.isnot(None)).all()
    now = datetime.datetime.utcnow()
    arrived = 0

    for v in vehicles:
        live = vehicle_live_position(v)
        if not live or not live['arrived']:
            continue

        v.latitude = v.route_dest_lat
        v.longitude = v.route_dest_lng
        v.status = 'on_scene'

        inc = v.current_incident
        if inc:
            if not inc.on_scene_at:
                inc.on_scene_at = now
            if inc.status not in ('On Scene', 'Closed'):
                old_status = inc.status
                inc.status = 'On Scene'
                actor_id = inc.reported_by or inc.updated_by
                if actor_id is None:
                    fb = (UserModel.query.filter_by(role='commander').first()
                          or UserModel.query.first())
                    actor_id = fb.id if fb else None
                db.session.add(StatusUpdate(
                    incident_id=inc.id, user_id=actor_id,
                    old_status=old_status, new_status='On Scene',
                    comment=f'{v.type} arrived on scene', timestamp=now))
                notify_id = inc.reported_by or actor_id
                if notify_id is not None:
                    create_notification(
                        user_id=notify_id,
                        title=f'Incident #{inc.id} — Unit On Scene',
                        message=f'{v.type} has arrived on scene',
                        incident_id=inc.id)

        clear_vehicle_route(v)
        arrived += 1

    if arrived:
        db.session.commit()
    return arrived


def get_weather(lat, lon):
    """Fetch current weather for given coordinates using OpenWeatherMap"""
    api_key = current_app.config.get('WEATHER_API_KEY')
    
    # MOCK MODE: If no valid key, return fake data for testing
    if not api_key or api_key == '00000000000000000000000000000000':
        return {
            'temp': 22.5,
            'description': 'clear sky (TEST MODE)',
            'icon': '01d',
            'humidity': 45,
            'wind_speed': 3.2,
            'wind_deg': 180
        }

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key,
            'units': 'metric'
        }
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'temp': data['main']['temp'],
                'description': data['weather'][0]['description'],
                'icon': data['weather'][0]['icon'],
                'humidity': data['main']['humidity'],
                'wind_speed': data['wind']['speed'],
                'wind_deg': data['wind'].get('deg', 0)
            }
    except Exception as e:
        print(f"Weather API error: {e}")
    return None


def create_notification(user_id, title, message, incident_id=None):
    """Create a notification for a user"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        incident_id=incident_id
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def generate_incident_pdf(incident):
    """Generate PDF report for an incident"""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)

    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#dc3545'),
        alignment=TA_CENTER,
        spaceAfter=30
    )

    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12
    )

    elements.append(Paragraph(f"Incident Report #{incident.id}", title_style))
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph("Burgas Fire Department", styles['Heading2']))
    elements.append(Paragraph("Emergency Operations Center", styles['Normal']))
    elements.append(Spacer(1, 0.25 * inch))

    data = [
        ['Incident Details', ''],
        ['Title:', incident.title],
        ['Location:', incident.location],
        ['Type:', incident.incident_type.capitalize()],
        ['Status:', incident.status],
        ['Reported At:', incident.reported_at.strftime('%Y-%m-%d %H:%M')],
        ['Reported By:', incident.reporter.username if incident.reporter else 'Unknown'],
    ]

    if incident.latitude and incident.longitude:
        data.append(['Coordinates:', f"{incident.latitude}, {incident.longitude}"])

    table = Table(data, colWidths=[2 * inch, 4 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc3545')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph("Description", header_style))
    elements.append(Paragraph(incident.description, styles['Normal']))
    elements.append(Spacer(1, 0.25 * inch))

    if incident.assigned_vehicle:
        elements.append(Paragraph("Assigned Unit", header_style))
        vehicle_data = [
            ['Vehicle:', incident.assigned_vehicle.type],
            ['Location:', incident.assigned_vehicle.location],
        ]
        if incident.assigned_vehicle.firefighters:
            crew_names = ', '.join([f.name for f in incident.assigned_vehicle.firefighters])
            vehicle_data.append(['Crew:', crew_names])
        vehicle_table = Table(vehicle_data, colWidths=[1.5 * inch, 4.5 * inch])
        vehicle_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        elements.append(vehicle_table)
        elements.append(Spacer(1, 0.25 * inch))

    if incident.status_updates:
        elements.append(Paragraph("Timeline", header_style))
        timeline_data = [['Time', 'Status', 'User']]
        for update in incident.status_updates[:10]:
            timeline_data.append([
                update.timestamp.strftime('%H:%M %d/%m'),
                f"{update.old_status} → {update.new_status}",
                update.user.username if update.user else 'System'
            ])
        timeline_table = Table(timeline_data, colWidths=[1.5 * inch, 3 * inch, 2 * inch])
        timeline_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(timeline_table)

    elements.append(Spacer(1, 0.5 * inch))
    footer_text = f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | Burgas Fire Department - Official Report"
    elements.append(Paragraph(footer_text, styles['Italic']))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def create_default_templates():
    """Create default message templates"""
    if MessageTemplate.query.count() > 0:
        return

    templates = [
        ('En Route', 'En route to incident. Estimated arrival in {{ eta }} minutes.', 'status'),
        ('On Scene', 'Arrived on scene. Assessing situation.', 'status'),
        ('Need Backup', 'Need backup at this location. Additional units requested.', 'request'),
        ('Request Water Supply', 'Requesting additional water supply. Need water tender.', 'request'),
        ('Situation Under Control', 'Situation is under control. Continuing operations.', 'status'),
        ('All Clear', 'All clear. Returning to station.', 'status'),
        ('MAYDAY', 'MAYDAY MAYDAY MAYDAY! Firefighter down! Need immediate assistance!', 'emergency'),
        ('Hazmat Situation', 'Hazardous materials detected. Requesting hazmat team.', 'request'),
        ('Medical Emergency', 'Medical emergency at scene. Requesting ambulance.', 'request'),
        ('Command Update', 'Command update: Continuing operations. All units maintain position.', 'general'),
    ]

    for i, (name, message, category) in enumerate(templates):
        template = MessageTemplate(
            name=name,
            message=message,
            category=category,
            order=i
        )
        db.session.add(template)

    db.session.commit()
    print("Default templates added!")


def create_default_equipment():
    """Create default equipment for testing"""
    from app.models.equipment import Equipment
    from app.models.vehicle import Vehicle
    import datetime

    # Check if equipment already exists
    if Equipment.query.count() > 0:
        print("Equipment already exists, skipping import.")
        return

    # Get vehicles
    vehicles = Vehicle.query.all()
    vehicle_dict = {v.id: v for v in vehicles}

    default_equipment = [
        # Vehicle 101 equipment (Aerial Ladder)
        {
            'name': 'Aerial Ladder - 30m',
            'type': 'tool',
            'model': 'Magirus M30L',
            'serial_number': 'LAD-101-001',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': 101,
            'notes': 'Main ladder for aerial operations'
        },
        {
            'name': 'Chainsaw - Stihl MS 881',
            'type': 'tool',
            'model': 'Stihl MS 881',
            'serial_number': 'SAW-101-001',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': 101,
            'notes': 'For cutting obstacles'
        },
        {
            'name': 'Thermal Imaging Camera',
            'type': 'tool',
            'model': 'FLIR K65',
            'serial_number': 'CAM-101-001',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': 101,
            'notes': 'For finding hot spots'
        },
        # Vehicle 102 equipment (Water Tanker)
        {
            'name': 'Hose - 5 inch Supply Hose',
            'type': 'hose',
            'model': 'PONN Supreme',
            'serial_number': 'HOS-102-001',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': 102,
            'notes': '50m supply hose'
        },
        {
            'name': 'Hose - 2.5 inch Attack Hose',
            'type': 'hose',
            'model': 'Mercedes Textiles',
            'serial_number': 'HOS-102-002',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': 102,
            'notes': '30m attack line'
        },
        {
            'name': 'Portable Pump',
            'type': 'tool',
            'model': 'Honda WX15',
            'serial_number': 'PMP-102-001',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': 102,
            'notes': 'For drafting water'
        },
        # Vehicle 103 equipment (Command Vehicle)
        {
            'name': 'Portable Radio Set',
            'type': 'tool',
            'model': 'Motorola APX 8000',
            'serial_number': 'RAD-103-001',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': 103,
            'notes': 'Command comms'
        },
        {
            'name': 'Drone with Thermal Camera',
            'type': 'tool',
            'model': 'DJI Matrice 300',
            'serial_number': 'DRN-103-001',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': 103,
            'notes': 'Aerial surveillance'
        },
        # General equipment (not assigned to vehicle)
        {
            'name': 'Fire Extinguisher - ABC 10lb',
            'type': 'extinguisher',
            'model': 'Amerex 570',
            'serial_number': 'EXT-001-001',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': None,
            'notes': 'Multi-purpose extinguisher'
        },
        {
            'name': 'Fire Extinguisher - CO2 20lb',
            'type': 'extinguisher',
            'model': 'Amerex 320',
            'serial_number': 'EXT-001-002',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': None,
            'notes': 'For electrical fires'
        },
        {
            'name': 'Halligan Tool',
            'type': 'tool',
            'model': 'Pro-Bar',
            'serial_number': 'HAL-001-001',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': None,
            'notes': 'Forcible entry tool'
        },
        {
            'name': 'Medical Jump Bag',
            'type': 'medical',
            'model': 'Meret Basic Life Support',
            'serial_number': 'MED-001-001',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': None,
            'notes': 'Basic first aid supplies'
        },
        {
            'name': 'SCBA Set',
            'type': 'gear',
            'model': 'MSA G1',
            'serial_number': 'SCB-001-001',
            'status': 'available',
            'condition': 'good',
            'vehicle_id': None,
            'notes': 'Self-contained breathing apparatus'
        },
    ]

    added = 0
    for eq_data in default_equipment:
        # Check if serial number already exists
        if eq_data['serial_number'] and Equipment.query.filter_by(serial_number=eq_data['serial_number']).first():
            continue

        equipment = Equipment(
            name=eq_data['name'],
            type=eq_data['type'],
            model=eq_data['model'],
            serial_number=eq_data['serial_number'],
            status=eq_data['status'],
            condition=eq_data['condition'],
            vehicle_id=eq_data['vehicle_id'],
            notes=eq_data['notes'],
            last_inspected=datetime.datetime.utcnow()
        )
        # Set next inspection date (6 months from now)
        equipment.next_inspection = datetime.datetime.utcnow() + datetime.timedelta(days=180)
        db.session.add(equipment)
        added += 1

    db.session.commit()
    print(f"Added {added} equipment items")