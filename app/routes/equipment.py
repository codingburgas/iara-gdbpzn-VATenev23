from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models.equipment import Equipment, EquipmentAssignment
from app.models.vehicle import Vehicle
from app.models.incident import Incident
from app.models.firefighter import Firefighter
from app.forms.equipment_forms import EquipmentForm, EquipmentCheckoutForm, EquipmentReturnForm
from app.utils import login_required, role_required, create_notification
import datetime

equipment_bp = Blueprint('equipment', __name__)


@equipment_bp.route('/staff/equipment')
@login_required
@role_required('dispatcher', 'commander')
def list_equipment():
    all_equipment = Equipment.query.all()
    vehicles = Vehicle.query.all()
    return render_template('staff/equipment/list.html',
                           equipment=all_equipment,
                           vehicles=vehicles)


@equipment_bp.route('/staff/equipment/add', methods=['GET', 'POST'])
@login_required
@role_required('commander')
def add_equipment():
    form = EquipmentForm()

    vehicles = Vehicle.query.all()
    form.vehicle_id.choices = [(0, 'None - Not assigned')] + [(v.id, f"{v.type} - {v.location}") for v in vehicles]

    if form.validate_on_submit():
        equipment = Equipment(
            name=form.name.data,
            type=form.type.data,
            model=form.model.data,
            serial_number=form.serial_number.data,
            status=form.status.data,
            condition=form.condition.data,
            vehicle_id=form.vehicle_id.data if form.vehicle_id.data != 0 else None,
            notes=form.notes.data,
            last_inspected=datetime.datetime.utcnow()
        )

        equipment.next_inspection = datetime.datetime.utcnow() + datetime.timedelta(days=180)

        db.session.add(equipment)
        db.session.commit()

        flash(f'Equipment {equipment.name} added successfully!', 'success')
        return redirect(url_for('equipment.list_equipment'))

    return render_template('staff/equipment/form.html', form=form, title="Add Equipment")


@equipment_bp.route('/staff/equipment/<int:equipment_id>')
@login_required
@role_required('dispatcher', 'commander', 'firefighter')
def detail(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    assignments = EquipmentAssignment.query.filter_by(equipment_id=equipment_id).order_by(
        EquipmentAssignment.assigned_at.desc()).all()

    return render_template('staff/equipment/detail.html',
                           equipment=equipment,
                           assignments=assignments)


@equipment_bp.route('/staff/equipment/<int:equipment_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('commander')
def edit_equipment(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    form = EquipmentForm(obj=equipment)

    vehicles = Vehicle.query.all()
    form.vehicle_id.choices = [(0, 'None - Not assigned')] + [(v.id, f"{v.type} - {v.location}") for v in vehicles]

    if form.validate_on_submit():
        equipment.name = form.name.data
        equipment.type = form.type.data
        equipment.model = form.model.data
        equipment.serial_number = form.serial_number.data
        equipment.status = form.status.data
        equipment.condition = form.condition.data
        equipment.vehicle_id = form.vehicle_id.data if form.vehicle_id.data != 0 else None
        equipment.notes = form.notes.data

        db.session.commit()
        flash('Equipment updated successfully!', 'success')
        return redirect(url_for('equipment.detail', equipment_id=equipment.id))

    return render_template('staff/equipment/form.html', form=form, equipment=equipment, title="Edit Equipment")


@equipment_bp.route('/staff/equipment/<int:equipment_id>/checkout', methods=['GET', 'POST'])
@login_required
@role_required('dispatcher', 'commander')
def checkout(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    form = EquipmentCheckoutForm()

    form.equipment_id.choices = [(equipment.id, equipment.name)]
    form.incident_id.choices = [(0, 'None')] + [(i.id, f"#{i.id} - {i.title}") for i in
                                                Incident.query.filter(Incident.status != 'Closed').all()]
    form.firefighter_id.choices = [(0, 'None')] + [(f.id, f"{f.name} ({f.rank})") for f in Firefighter.query.all()]

    if form.validate_on_submit():
        assignment = EquipmentAssignment(
            equipment_id=equipment.id,
            incident_id=form.incident_id.data if form.incident_id.data != 0 else None,
            firefighter_id=form.firefighter_id.data if form.firefighter_id.data != 0 else None,
            notes=form.notes.data,
            status='assigned'
        )

        equipment.status = 'in_use'

        db.session.add(assignment)
        db.session.commit()

        if form.incident_id.data != 0:
            incident = Incident.query.get(form.incident_id.data)
            create_notification(
                user_id=incident.reported_by,
                title=f'Equipment Checked Out',
                message=f'{equipment.name} checked out for incident #{incident.id}',
                incident_id=incident.id
            )

        flash(f'{equipment.name} checked out successfully!', 'success')
        return redirect(url_for('equipment.detail', equipment_id=equipment.id))

    return render_template('staff/equipment/checkout.html', form=form, equipment=equipment)


@equipment_bp.route('/staff/equipment/<int:assignment_id>/return', methods=['GET', 'POST'])
@login_required
@role_required('dispatcher', 'commander')
def return_equipment(assignment_id):
    assignment = EquipmentAssignment.query.get_or_404(assignment_id)
    equipment = assignment.equipment
    form = EquipmentReturnForm()

    if form.validate_on_submit():
        assignment.returned_at = datetime.datetime.utcnow()
        assignment.status = 'returned'
        assignment.notes = (assignment.notes or '') + f"\nReturn notes: {form.notes.data}"

        equipment.status = 'available'
        equipment.condition = form.condition.data
        equipment.last_inspected = datetime.datetime.utcnow()

        db.session.commit()

        flash(f'{equipment.name} returned successfully!', 'success')
        return redirect(url_for('equipment.detail', equipment_id=equipment.id))

    return render_template('staff/equipment/return.html', form=form, equipment=equipment, assignment=assignment)


@equipment_bp.route('/staff/import-equipment')
@login_required
@role_required('dispatcher', 'commander')
def import_equipment():
    from app.utils import create_default_equipment
    create_default_equipment()
    flash('Default equipment added successfully!', 'success')
    return redirect(url_for('equipment.list_equipment'))