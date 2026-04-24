from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_

from app.extensions import db
from app.models.department import Department
from app.models.space import KnowledgeBaseRegistry, Space, SpaceDepartmentMember, SpaceUserMember
from app.models.user import User
from app.services.weknora_client import WeKnoraApiError, WeKnoraClient
from app.utils.context import get_current_user
from app.utils.constants import ROLE_DEPT_ADMIN
from app.utils.permissions import can_manage_space, is_super_admin
from app.utils.rbac import role_required


space_bp = Blueprint('space', __name__, url_prefix='/api/spaces')


def _space_with_access(user):
    if is_super_admin(user):
        return Space.query

    membership_user_space_ids = db.session.query(SpaceUserMember.space_id).filter(
        SpaceUserMember.user_id == user.id
    )
    membership_dept_space_ids = db.session.query(SpaceDepartmentMember.space_id).filter(
        SpaceDepartmentMember.department_id == user.department_id
    )

    return Space.query.filter(
        or_(
            Space.owner_user_id == user.id,
            Space.id.in_(membership_user_space_ids),
            Space.id.in_(membership_dept_space_ids),
        )
    )


@space_bp.get('')
@jwt_required()
def list_spaces():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401

    spaces = _space_with_access(user).order_by(Space.id.asc()).all()
    space_ids = [s.id for s in spaces]

    user_member_counts = {}
    dept_member_counts = {}
    kb_counts = {}

    if space_ids:
        user_rows = (
            db.session.query(SpaceUserMember.space_id, db.func.count(SpaceUserMember.id))
            .filter(SpaceUserMember.space_id.in_(space_ids))
            .group_by(SpaceUserMember.space_id)
            .all()
        )
        dept_rows = (
            db.session.query(SpaceDepartmentMember.space_id, db.func.count(SpaceDepartmentMember.id))
            .filter(SpaceDepartmentMember.space_id.in_(space_ids))
            .group_by(SpaceDepartmentMember.space_id)
            .all()
        )
        kb_rows = (
            db.session.query(KnowledgeBaseRegistry.space_id, db.func.count(KnowledgeBaseRegistry.id))
            .filter(KnowledgeBaseRegistry.space_id.in_(space_ids))
            .group_by(KnowledgeBaseRegistry.space_id)
            .all()
        )

        user_member_counts = {space_id: count for space_id, count in user_rows}
        dept_member_counts = {space_id: count for space_id, count in dept_rows}
        kb_counts = {space_id: count for space_id, count in kb_rows}

    results = []
    for s in spaces:
        data = s.to_dict()
        data['owner_name'] = s.owner_user.full_name if s.owner_user else ''
        data['member_count'] = int(user_member_counts.get(s.id, 0)) + int(dept_member_counts.get(s.id, 0))
        data['kb_count'] = int(kb_counts.get(s.id, 0))
        data['my_permission'] = 'manage' if can_manage_space(user, s) else 'read'
        results.append(data)

    return jsonify({'success': True, 'data': results})


@space_bp.get('/<int:space_id>/knowledge-bases')
@jwt_required()
def list_space_knowledge_bases(space_id: int):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401

    space = _space_with_access(user).filter(Space.id == space_id).first()
    if not space:
        return jsonify({'success': False, 'message': 'space not found or inaccessible'}), 404

    items = (
        KnowledgeBaseRegistry.query.filter_by(space_id=space.id)
        .order_by(KnowledgeBaseRegistry.id.desc())
        .all()
    )
    return jsonify({'success': True, 'data': [i.to_dict() for i in items]})


@space_bp.post('')
@jwt_required()
@role_required(ROLE_DEPT_ADMIN)
def create_space():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401

    payload = request.get_json(silent=True) or {}
    name = (payload.get('name') or '').strip()
    description = (payload.get('description') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'name is required'}), 400

    space = Space(
        name=name,
        description=description,
        owner_user_id=user.id,
        owner_department_id=user.department_id,
        is_enabled=True,
    )

    db.session.add(space)
    db.session.flush()

    try:
        weknora_org = WeKnoraClient().create_organization(name=name, description=description)
        space.weknora_org_id = str(weknora_org.get('id') or '')
    except WeKnoraApiError as exc:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Create WeKnora organization failed: {exc}'}), 502

    db.session.commit()
    return jsonify({'success': True, 'data': space.to_dict()}), 201


@space_bp.put('/<int:space_id>')
@jwt_required()
@role_required(ROLE_DEPT_ADMIN)
def update_space(space_id: int):
    user = get_current_user()
    space = Space.query.get(space_id)
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401
    if not space:
        return jsonify({'success': False, 'message': 'space not found'}), 404
    if not can_manage_space(user, space):
        return jsonify({'success': False, 'message': 'permission denied'}), 403

    payload = request.get_json(silent=True) or {}
    if 'name' in payload:
        name = (payload.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'message': 'name cannot be empty'}), 400
        space.name = name
    if 'description' in payload:
        space.description = (payload.get('description') or '').strip()
    if 'is_enabled' in payload:
        space.is_enabled = bool(payload.get('is_enabled'))

    if space.weknora_org_id:
        try:
            WeKnoraClient().update_organization(
                organization_id=space.weknora_org_id,
                name=space.name,
                description=space.description,
            )
        except WeKnoraApiError as exc:
            return jsonify({'success': False, 'message': f'Update WeKnora organization failed: {exc}'}), 502

    db.session.commit()
    return jsonify({'success': True, 'data': space.to_dict()})


@space_bp.get('/<int:space_id>/members')
@jwt_required()
def list_space_members(space_id: int):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401

    space = _space_with_access(user).filter(Space.id == space_id).first()
    if not space:
        return jsonify({'success': False, 'message': 'space not found or inaccessible'}), 404

    user_members = SpaceUserMember.query.filter_by(space_id=space_id).all()
    dept_members = SpaceDepartmentMember.query.filter_by(space_id=space_id).all()

    return jsonify(
        {
            'success': True,
            'data': {
                'space': space.to_dict(),
                'user_members': [m.to_dict() for m in user_members],
                'department_members': [m.to_dict() for m in dept_members],
            },
        }
    )


@space_bp.post('/<int:space_id>/members/users')
@jwt_required()
@role_required(ROLE_DEPT_ADMIN)
def add_space_users(space_id: int):
    user = get_current_user()
    space = Space.query.get(space_id)
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401
    if not space:
        return jsonify({'success': False, 'message': 'space not found'}), 404
    if not can_manage_space(user, space):
        return jsonify({'success': False, 'message': 'permission denied'}), 403

    payload = request.get_json(silent=True) or {}
    user_ids = payload.get('user_ids') or []
    if not isinstance(user_ids, list) or not user_ids:
        return jsonify({'success': False, 'message': 'user_ids is required'}), 400

    created = []
    for target_user_id in user_ids:
        target_user = User.query.get(target_user_id)
        if not target_user:
            continue
        exists = SpaceUserMember.query.filter_by(space_id=space.id, user_id=target_user.id).first()
        if exists:
            continue
        member = SpaceUserMember(space_id=space.id, user_id=target_user.id)
        db.session.add(member)
        created.append(member)

    db.session.commit()
    return jsonify({'success': True, 'data': [m.to_dict() for m in created]})


@space_bp.delete('/<int:space_id>/members/users/<int:user_id>')
@jwt_required()
@role_required(ROLE_DEPT_ADMIN)
def remove_space_user(space_id: int, user_id: int):
    user = get_current_user()
    space = Space.query.get(space_id)
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401
    if not space:
        return jsonify({'success': False, 'message': 'space not found'}), 404
    if not can_manage_space(user, space):
        return jsonify({'success': False, 'message': 'permission denied'}), 403

    member = SpaceUserMember.query.filter_by(space_id=space.id, user_id=user_id).first()
    if not member:
        return jsonify({'success': False, 'message': 'member not found'}), 404
    db.session.delete(member)
    db.session.commit()
    return jsonify({'success': True, 'message': 'member removed'})


@space_bp.post('/<int:space_id>/members/departments')
@jwt_required()
@role_required(ROLE_DEPT_ADMIN)
def add_space_departments(space_id: int):
    user = get_current_user()
    space = Space.query.get(space_id)
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401
    if not space:
        return jsonify({'success': False, 'message': 'space not found'}), 404
    if not can_manage_space(user, space):
        return jsonify({'success': False, 'message': 'permission denied'}), 403

    payload = request.get_json(silent=True) or {}
    department_ids = payload.get('department_ids') or []
    if not isinstance(department_ids, list) or not department_ids:
        return jsonify({'success': False, 'message': 'department_ids is required'}), 400

    created = []
    for department_id in department_ids:
        department = Department.query.get(department_id)
        if not department:
            continue
        exists = SpaceDepartmentMember.query.filter_by(space_id=space.id, department_id=department.id).first()
        if exists:
            continue
        member = SpaceDepartmentMember(space_id=space.id, department_id=department.id)
        db.session.add(member)
        created.append(member)

    db.session.commit()
    return jsonify({'success': True, 'data': [m.to_dict() for m in created]})


@space_bp.delete('/<int:space_id>/members/departments/<int:department_id>')
@jwt_required()
@role_required(ROLE_DEPT_ADMIN)
def remove_space_department(space_id: int, department_id: int):
    user = get_current_user()
    space = Space.query.get(space_id)
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401
    if not space:
        return jsonify({'success': False, 'message': 'space not found'}), 404
    if not can_manage_space(user, space):
        return jsonify({'success': False, 'message': 'permission denied'}), 403

    member = SpaceDepartmentMember.query.filter_by(space_id=space.id, department_id=department_id).first()
    if not member:
        return jsonify({'success': False, 'message': 'department member not found'}), 404
    db.session.delete(member)
    db.session.commit()
    return jsonify({'success': True, 'message': 'department member removed'})
