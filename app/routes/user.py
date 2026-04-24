from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models.department import Department
from app.models.user import User
from app.utils.constants import ROLE_DEPT_ADMIN, ROLE_SUPER_ADMIN, VALID_ROLES
from app.utils.context import get_current_user
from app.utils.permissions import is_super_admin
from app.utils.rbac import role_required
from app.utils.security import hash_password


user_bp = Blueprint('user', __name__, url_prefix='/api/users')


@user_bp.get('')
@jwt_required()
@role_required(ROLE_DEPT_ADMIN)
def list_users():
    current_user = get_current_user()
    if not current_user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401

    query = User.query
    if not is_super_admin(current_user):
        query = query.filter(User.department_id == current_user.department_id)

    users = query.order_by(User.id.asc()).all()
    return jsonify({'success': True, 'data': [u.to_dict() for u in users]})


@user_bp.post('')
@jwt_required()
@role_required(ROLE_SUPER_ADMIN)
def create_user():
    payload = request.get_json(silent=True) or {}

    required = ['login_name', 'full_name', 'email', 'password']
    for field in required:
        if not payload.get(field):
            return jsonify({'success': False, 'message': f'{field} is required'}), 400

    login_name = payload['login_name'].strip()
    email = payload['email'].strip().lower()

    if User.query.filter((User.login_name == login_name) | (User.email == email)).first():
        return jsonify({'success': False, 'message': 'login_name or email already exists'}), 409

    role_level = payload.get('role_level', 'user')
    if role_level not in VALID_ROLES:
        return jsonify({'success': False, 'message': 'invalid role_level'}), 400

    department_id = payload.get('department_id')
    department_name = payload.get('department_name')
    if department_id:
        department = Department.query.get(department_id)
        if not department:
            return jsonify({'success': False, 'message': 'department not found'}), 404
        department_name = department.name

    user = User(
        login_name=login_name,
        domain_account=payload.get('domain_account'),
        full_name=payload['full_name'],
        email=email,
        department_id=department_id,
        department_name=department_name,
        role_level=role_level,
        password_hash=hash_password(payload['password']),
        is_enabled=bool(payload.get('is_enabled', True)),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True, 'data': user.to_dict()}), 201


@user_bp.put('/<int:user_id>')
@jwt_required()
@role_required(ROLE_SUPER_ADMIN)
def update_user(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'user not found'}), 404

    payload = request.get_json(silent=True) or {}

    for field in ['full_name', 'domain_account', 'department_name']:
        if field in payload:
            setattr(user, field, payload[field])

    if 'email' in payload:
        email = payload['email'].strip().lower()
        exists = User.query.filter(User.email == email, User.id != user.id).first()
        if exists:
            return jsonify({'success': False, 'message': 'email already exists'}), 409
        user.email = email

    if 'role_level' in payload:
        if payload['role_level'] not in VALID_ROLES:
            return jsonify({'success': False, 'message': 'invalid role_level'}), 400
        user.role_level = payload['role_level']

    if 'department_id' in payload:
        department_id = payload['department_id']
        if department_id is None:
            user.department_id = None
            user.department_name = payload.get('department_name')
        else:
            department = Department.query.get(department_id)
            if not department:
                return jsonify({'success': False, 'message': 'department not found'}), 404
            user.department_id = department.id
            user.department_name = department.name

    if 'is_enabled' in payload:
        user.is_enabled = bool(payload['is_enabled'])

    if payload.get('password'):
        user.password_hash = hash_password(payload['password'])

    db.session.commit()
    return jsonify({'success': True, 'data': user.to_dict()})
