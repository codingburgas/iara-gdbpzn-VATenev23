from functools import wraps
from flask import flash, redirect, url_for, session, send_file
import requests
import datetime
import io
from models import db, Notification, Equipment, EquipmentAssignment, Vehicle

# ReportLab imports - FIXED with all needed constants
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

# ========== DECORATORS ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please login to access the staff portal.', 'warning')
            return redirect(url_for('staff_login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                flash('Please login to access the staff portal.', 'warning')
                return redirect(url_for('staff_login'))
            if session.get('user_role') not in roles:
                flash('Unauthorized access. This incident has been logged.', 'danger')
                return redirect(url_for('staff_dashboard'))
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

    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)

    # Container for elements
    elements = []

    # Styles
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

    # Title
    elements.append(Paragraph(f"Incident Report #{incident.id}", title_style))
    elements.append(Spacer(1, 0.25 * inch))

    # Department header
    elements.append(Paragraph("Burgas Fire Department", styles['Heading2']))
    elements.append(Paragraph("Emergency Operations Center", styles['Normal']))
    elements.append(Spacer(1, 0.25 * inch))

    # Incident Details Table
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

    # Description
    elements.append(Paragraph("Description", header_style))
    elements.append(Paragraph(incident.description, styles['Normal']))
    elements.append(Spacer(1, 0.25 * inch))

    # Assigned Unit
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

    # Timeline
    if incident.status_updates:
        elements.append(Paragraph("Timeline", header_style))
        timeline_data = [['Time', 'Status', 'User']]
        for update in incident.status_updates[:10]:  # Last 10 updates
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

    # Footer
    elements.append(Spacer(1, 0.5 * inch))
    footer_text = f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | Burgas Fire Department - Official Report"
    elements.append(Paragraph(footer_text, styles['Italic']))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def create_default_equipment():
    """Create default equipment for testing"""
    # Check if equipment already exists
    if Equipment.query.count() > 0:
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

    db.session.commit()
    print(f"Added {len(default_equipment)} equipment items")