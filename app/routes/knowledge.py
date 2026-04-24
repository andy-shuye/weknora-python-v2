from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models.space import KnowledgeBaseRegistry, Space
from app.services.weknora_client import WeKnoraApiError, WeKnoraClient
from app.utils.context import get_current_user
from app.utils.permissions import can_manage_space, can_share_kb, is_super_admin


knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/api/knowledge')


def _can_manage_registry(user, registry: KnowledgeBaseRegistry) -> bool:
    if not user or not registry:
        return False
    if is_super_admin(user):
        return True
    return registry.owner_user_id == user.id


def _query_visible_registries(user):
    query = KnowledgeBaseRegistry.query
    if not is_super_admin(user):
        query = query.filter_by(owner_user_id=user.id)
    return query.order_by(KnowledgeBaseRegistry.id.desc())


def _get_registry_with_permission(registry_id: int):
    user = get_current_user()
    registry = KnowledgeBaseRegistry.query.get(registry_id)
    if not user:
        return None, None, (jsonify({'success': False, 'message': 'invalid user'}), 401)
    if not registry:
        return user, None, (jsonify({'success': False, 'message': 'knowledge base not found'}), 404)
    if not _can_manage_registry(user, registry):
        return user, registry, (jsonify({'success': False, 'message': 'permission denied'}), 403)
    return user, registry, None


def _normalize_share_permission(raw_permission: str) -> str:
    permission = (raw_permission or '').strip().lower()
    permission_map = {
        'read': 'viewer',
        'viewer': 'viewer',
        'view': 'viewer',
        'write': 'editor',
        'edit': 'editor',
        'editor': 'editor',
        'manage': 'admin',
        'admin': 'admin',
        'owner': 'admin',
    }
    return permission_map.get(permission, 'viewer')


@knowledge_bp.get('/health')
def knowledge_health():
    return jsonify({'success': True, 'message': 'knowledge module ready'})


@knowledge_bp.get('/bases')
@jwt_required()
def list_bases():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401

    registries = _query_visible_registries(user).all()

    try:
        remote_bases = WeKnoraClient().list_knowledge_bases()
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to list WeKnora knowledge bases: {exc}'}), 502

    remote_map = {str(item.get('id')): item for item in remote_bases}

    merged = []
    for item in registries:
        registry_dict = item.to_dict()
        registry_dict['weknora'] = remote_map.get(item.weknora_kb_id)
        merged.append(registry_dict)

    return jsonify({'success': True, 'data': merged})


@knowledge_bp.post('/bases')
@jwt_required()
def create_base():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401

    payload = request.get_json(silent=True) or {}
    name = (payload.get('name') or '').strip()
    description = (payload.get('description') or '').strip()
    kb_type = (payload.get('type') or 'document').strip() or 'document'

    if not name:
        return jsonify({'success': False, 'message': 'name is required'}), 400

    try:
        remote = WeKnoraClient().create_knowledge_base(name=name, description=description, kb_type=kb_type)
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Create WeKnora knowledge base failed: {exc}'}), 502

    remote_id = str(remote.get('id') or '').strip()
    if not remote_id:
        return jsonify({'success': False, 'message': 'WeKnora did not return a knowledge base id'}), 502

    exists = KnowledgeBaseRegistry.query.filter_by(weknora_kb_id=remote_id).first()
    if exists:
        return jsonify({'success': False, 'message': 'knowledge base already registered locally'}), 409

    item = KnowledgeBaseRegistry(
        weknora_kb_id=remote_id,
        name=(remote.get('name') or name),
        owner_user_id=user.id,
        owner_department_id=user.department_id,
        visibility='private',
        created_by=user.id,
    )
    db.session.add(item)
    db.session.commit()

    result = item.to_dict()
    result['weknora'] = remote
    return jsonify({'success': True, 'data': result}), 201


@knowledge_bp.get('/bases/<int:registry_id>')
@jwt_required()
def get_base(registry_id: int):
    user = get_current_user()
    registry = KnowledgeBaseRegistry.query.get(registry_id)
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401
    if not registry:
        return jsonify({'success': False, 'message': 'knowledge base not found'}), 404
    if not _can_manage_registry(user, registry):
        return jsonify({'success': False, 'message': 'permission denied'}), 403

    try:
        remote = WeKnoraClient().get_knowledge_base(registry.weknora_kb_id)
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to query WeKnora knowledge base detail: {exc}'}), 502

    result = registry.to_dict()
    result['weknora'] = remote
    return jsonify({'success': True, 'data': result})


@knowledge_bp.put('/bases/<int:registry_id>')
@jwt_required()
def update_base(registry_id: int):
    user = get_current_user()
    registry = KnowledgeBaseRegistry.query.get(registry_id)
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401
    if not registry:
        return jsonify({'success': False, 'message': 'knowledge base not found'}), 404
    if not _can_manage_registry(user, registry):
        return jsonify({'success': False, 'message': 'permission denied'}), 403

    payload = request.get_json(silent=True) or {}
    name = payload.get('name')
    description = payload.get('description')

    if name is not None and not str(name).strip():
        return jsonify({'success': False, 'message': 'name cannot be empty'}), 400

    try:
        remote = WeKnoraClient().update_knowledge_base(
            kb_id=registry.weknora_kb_id,
            name=str(name).strip() if name is not None else None,
            description=str(description).strip() if description is not None else None,
        )
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to update WeKnora knowledge base: {exc}'}), 502

    if name is not None:
        registry.name = str(name).strip()
    db.session.commit()

    result = registry.to_dict()
    result['weknora'] = remote
    return jsonify({'success': True, 'data': result})


@knowledge_bp.delete('/bases/<int:registry_id>')
@jwt_required()
def delete_base(registry_id: int):
    user = get_current_user()
    registry = KnowledgeBaseRegistry.query.get(registry_id)
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401
    if not registry:
        return jsonify({'success': False, 'message': 'knowledge base not found'}), 404
    if not _can_manage_registry(user, registry):
        return jsonify({'success': False, 'message': 'permission denied'}), 403

    try:
        WeKnoraClient().delete_knowledge_base(registry.weknora_kb_id)
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to delete WeKnora knowledge base: {exc}'}), 502

    db.session.delete(registry)
    db.session.commit()
    return jsonify({'success': True, 'message': 'knowledge base deleted'})


@knowledge_bp.get('/bases/<int:registry_id>/documents')
@jwt_required()
def list_documents(registry_id: int):
    _, registry, error = _get_registry_with_permission(registry_id)
    if error:
        return error

    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    tag_id = (request.args.get('tag_id') or '').strip()

    try:
        docs = WeKnoraClient().list_knowledge_documents(registry.weknora_kb_id, page=page, page_size=page_size)
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to list documents from WeKnora: {exc}'}), 502

    if tag_id:
        items = docs.get('items') or []
        docs['items'] = [item for item in items if str(item.get('tag_id') or '') == tag_id]
        docs['total'] = len(docs['items'])

    return jsonify({'success': True, 'data': docs})


@knowledge_bp.post('/bases/<int:registry_id>/documents/upload')
@jwt_required()
def upload_document(registry_id: int):
    _, registry, error = _get_registry_with_permission(registry_id)
    if error:
        return error

    file_obj = request.files.get('file')
    if not file_obj:
        return jsonify({'success': False, 'message': 'file is required'}), 400

    enable_multimodel = request.form.get('enable_multimodel', 'true').lower() == 'true'
    tag_id = (request.form.get('tag_id') or '').strip()

    try:
        created = WeKnoraClient().upload_knowledge_file(
            kb_id=registry.weknora_kb_id,
            file_storage=file_obj,
            enable_multimodel=enable_multimodel,
        )
        if tag_id and created.get('id'):
            WeKnoraClient().batch_update_knowledge_tags({str(created.get('id')): tag_id})
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Upload document to WeKnora failed: {exc}'}), 502

    return jsonify({'success': True, 'data': created}), 201


@knowledge_bp.get('/bases/<int:registry_id>/tags')
@jwt_required()
def list_tags(registry_id: int):
    _, registry, error = _get_registry_with_permission(registry_id)
    if error:
        return error

    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 50))
    keyword = (request.args.get('keyword') or '').strip()

    try:
        tags = WeKnoraClient().list_knowledge_tags(
            kb_id=registry.weknora_kb_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
        )
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to list tags from WeKnora: {exc}'}), 502

    return jsonify({'success': True, 'data': tags})


@knowledge_bp.post('/bases/<int:registry_id>/tags')
@jwt_required()
def create_tag(registry_id: int):
    _, registry, error = _get_registry_with_permission(registry_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    name = (payload.get('name') or '').strip()
    color = (payload.get('color') or '').strip()
    sort_order = int(payload.get('sort_order') or 0)
    if not name:
        return jsonify({'success': False, 'message': 'name is required'}), 400

    try:
        tag = WeKnoraClient().create_knowledge_tag(
            kb_id=registry.weknora_kb_id,
            name=name,
            color=color,
            sort_order=sort_order,
        )
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to create tag: {exc}'}), 502

    return jsonify({'success': True, 'data': tag}), 201


@knowledge_bp.put('/bases/<int:registry_id>/tags/<string:tag_id>')
@jwt_required()
def update_tag(registry_id: int, tag_id: str):
    _, registry, error = _get_registry_with_permission(registry_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    name = payload.get('name')
    color = payload.get('color')
    sort_order = payload.get('sort_order')

    try:
        tag = WeKnoraClient().update_knowledge_tag(
            kb_id=registry.weknora_kb_id,
            tag_id=tag_id,
            name=name,
            color=color,
            sort_order=sort_order,
        )
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to update tag: {exc}'}), 502

    return jsonify({'success': True, 'data': tag})


@knowledge_bp.delete('/bases/<int:registry_id>/tags/<string:tag_id>')
@jwt_required()
def delete_tag(registry_id: int, tag_id: str):
    _, registry, error = _get_registry_with_permission(registry_id)
    if error:
        return error

    force = (request.args.get('force') or '').strip().lower() == 'true'
    try:
        WeKnoraClient().delete_knowledge_tag(
            kb_id=registry.weknora_kb_id,
            tag_id=tag_id,
            force=force,
        )
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to delete tag: {exc}'}), 502

    return jsonify({'success': True, 'message': 'tag deleted'})


@knowledge_bp.put('/bases/<int:registry_id>/documents/tags')
@jwt_required()
def batch_update_document_tags(registry_id: int):
    _, _, error = _get_registry_with_permission(registry_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    updates = payload.get('updates') or {}
    if not isinstance(updates, dict) or not updates:
        return jsonify({'success': False, 'message': 'updates is required'}), 400

    try:
        result = WeKnoraClient().batch_update_knowledge_tags(updates)
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to update document tags: {exc}'}), 502

    return jsonify({'success': True, 'data': result})


@knowledge_bp.post('/<int:registry_id>/share-to-space')
@jwt_required()
def share_to_space(registry_id: int):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401
    if not can_share_kb(user):
        return jsonify({'success': False, 'message': 'only dept_admin or super_admin can share knowledge base'}), 403

    payload = request.get_json(silent=True) or {}
    space_id = payload.get('space_id')
    permission = _normalize_share_permission(payload.get('permission') or 'viewer')

    if not space_id:
        return jsonify({'success': False, 'message': 'space_id is required'}), 400

    kb = KnowledgeBaseRegistry.query.get(registry_id)
    if not kb:
        return jsonify({'success': False, 'message': 'knowledge base registry not found'}), 404

    if not is_super_admin(user) and kb.owner_user_id != user.id:
        return jsonify({'success': False, 'message': 'cannot share a knowledge base not owned by you'}), 403

    space = Space.query.get(space_id)
    if not space:
        return jsonify({'success': False, 'message': 'space not found'}), 404
    if not can_manage_space(user, space):
        return jsonify({'success': False, 'message': 'permission denied for target space'}), 403
    if not space.weknora_org_id:
        return jsonify({'success': False, 'message': 'target space has no mapped WeKnora organization'}), 400

    try:
        share_info = WeKnoraClient().share_knowledge_base(
            kb_id=kb.weknora_kb_id,
            organization_id=space.weknora_org_id,
            permission=permission,
        )
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Share knowledge base failed: {exc}'}), 502

    kb.visibility = 'space'
    kb.space_id = space.id
    db.session.commit()

    return jsonify({'success': True, 'data': {'registry': kb.to_dict(), 'share': share_info}})


@knowledge_bp.delete('/<int:registry_id>/share-from-space')
@jwt_required()
def revoke_share_from_space(registry_id: int):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'invalid user'}), 401

    kb = KnowledgeBaseRegistry.query.get(registry_id)
    if not kb:
        return jsonify({'success': False, 'message': 'knowledge base registry not found'}), 404

    if not is_super_admin(user) and kb.owner_user_id != user.id:
        return jsonify({'success': False, 'message': 'cannot revoke a knowledge base not owned by you'}), 403

    if not kb.space_id:
        return jsonify({'success': False, 'message': 'knowledge base is not shared to a space'}), 400

    space = Space.query.get(kb.space_id)
    if not space:
        return jsonify({'success': False, 'message': 'space not found'}), 404

    if not can_manage_space(user, space):
        return jsonify({'success': False, 'message': 'permission denied for target space'}), 403

    if space.weknora_org_id:
        try:
            shares = WeKnoraClient().list_knowledge_base_shares(kb.weknora_kb_id)
            target_share = None
            for share in shares:
                if str(share.get('organization_id')) == str(space.weknora_org_id):
                    target_share = share
                    break
            if target_share and target_share.get('id'):
                WeKnoraClient().delete_knowledge_base_share(kb.weknora_kb_id, str(target_share['id']))
        except WeKnoraApiError as exc:
            return jsonify({'success': False, 'message': f'Revoke share failed: {exc}'}), 502

    kb.visibility = 'private'
    kb.space_id = None
    db.session.commit()

    return jsonify({'success': True, 'data': kb.to_dict()})
