from functools import wraps
from flask import flash, redirect, url_for, session, send_file
import requests
import datetime
import io
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
        ('🚨 MAYDAY', 'MAYDAY MAYDAY MAYDAY! Firefighter down! Need immediate assistance!', 'emergency'),
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