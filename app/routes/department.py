from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models.department import Department
from app.utils.constants import ROLE_SUPER_ADMIN
from app.utils.rbac import role_required


department_bp = Blueprint('department', __name__, url_prefix='/api/departments')


@department_bp.get('')
@jwt_required()
def list_departments():
    departments = Department.query.order_by(Department.id.asc()).all()
    return jsonify({'success': True, 'data': [d.to_dict() for d in departments]})


@department_bp.post('')
@jwt_required()
@role_required(ROLE_SUPER_ADMIN)
def create_department():
    payload = request.get_json(silent=True) or {}
    name = (payload.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'name is required'}), 400

    if Department.query.filter_by(name=name).first():
        return jsonify({'success': False, 'message': 'department name already exists'}), 409

    parent_id = payload.get('parent_id')
    if parent_id is not None and not Department.query.get(parent_id):
        return jsonify({'success': False, 'message': 'parent department not found'}), 404

    department = Department(
        name=name,
        parent_id=parent_id,
        is_enabled=bool(payload.get('is_enabled', True)),
    )
    db.session.add(department)
    db.session.commit()
    return jsonify({'success': True, 'data': department.to_dict()}), 201


@department_bp.put('/<int:department_id>')
@jwt_required()
@role_required(ROLE_SUPER_ADMIN)
def update_department(department_id: int):
    department = Department.query.get(department_id)
    if not department:
        return jsonify({'success': False, 'message': 'department not found'}), 404

    payload = request.get_json(silent=True) or {}

    if 'name' in payload:
        name = (payload.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'message': 'name cannot be empty'}), 400
        exists = Department.query.filter(Department.name == name, Department.id != department.id).first()
        if exists:
            return jsonify({'success': False, 'message': 'department name already exists'}), 409
        department.name = name

    if 'parent_id' in payload:
        parent_id = payload.get('parent_id')
        if parent_id == department.id:
            return jsonify({'success': False, 'message': 'parent_id cannot be itself'}), 400
        if parent_id is not None and not Department.query.get(parent_id):
            return jsonify({'success': False, 'message': 'parent department not found'}), 404
        department.parent_id = parent_id

    if 'is_enabled' in payload:
        department.is_enabled = bool(payload['is_enabled'])

    db.session.commit()
    return jsonify({'success': True, 'data': department.to_dict()})
