from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models.chat_session import ChatSessionRegistry
from app.services.weknora_client import WeKnoraApiError, WeKnoraClient
from app.utils.context import get_current_user


chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')


def _require_user():
    user = get_current_user()
    if not user:
        return None, (jsonify({'success': False, 'message': 'invalid user'}), 401)
    if not user.is_enabled:
        return None, (jsonify({'success': False, 'message': 'account is disabled'}), 403)
    return user, None


def _get_owned_session(user_id: int, session_id: str):
    return ChatSessionRegistry.query.filter_by(
        owner_user_id=user_id,
        weknora_session_id=session_id,
    ).first()


def _require_owned_session(user_id: int, session_id: str):
    item = _get_owned_session(user_id, session_id)
    if not item:
        return None, (jsonify({'success': False, 'message': 'session not found or inaccessible'}), 404)
    return item, None


@chat_bp.get('/health')
def chat_health():
    return jsonify({'success': True, 'message': 'chat module ready'})


@chat_bp.get('/options')
@jwt_required()
def chat_options():
    _, error = _require_user()
    if error:
        return error

    default_model_id = current_app.config.get('WEKNORA_CHAT_DEFAULT_MODEL_ID', '')
    models = []
    try:
        raw_models = WeKnoraClient().list_models()
        for item in raw_models:
            model_id = str(item.get('id') or '').strip()
            name = str(item.get('name') or model_id).strip()
            model_type = str(item.get('type') or '').strip().lower()
            if not model_id:
                continue
            # Keep chat-capable models only.
            if model_type not in {'knowledgeqa', 'chat'}:
                continue
            models.append({'id': model_id, 'name': name, 'type': model_type})
    except WeKnoraApiError:
        models = []

    if default_model_id and not any(m['id'] == default_model_id for m in models):
        models.insert(0, {'id': default_model_id, 'name': default_model_id, 'type': 'chat'})

    return jsonify(
        {
            'success': True,
            'data': {
                'default_model_id': default_model_id,
                'default_rerank_model_id': current_app.config.get('WEKNORA_CHAT_DEFAULT_RERANK_MODEL_ID', ''),
                'quick_answer_agent_id': current_app.config.get('WEKNORA_AGENT_QUICK_ANSWER_ID', 'builtin-quick-answer'),
                'smart_reasoning_agent_id': current_app.config.get('WEKNORA_AGENT_SMART_REASONING_ID', 'builtin-smart-reasoning'),
                'models': models,
                'modes': [
                    {'id': 'quick', 'label': '快速问答'},
                    {'id': 'reasoning', 'label': '智能推理'},
                ],
            },
        }
    )


@chat_bp.get('/sessions')
@jwt_required()
def list_sessions():
    user, error = _require_user()
    if error:
        return error

    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 100))
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 100

    query = ChatSessionRegistry.query.filter_by(owner_user_id=user.id).order_by(ChatSessionRegistry.updated_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return jsonify(
        {
            'success': True,
            'data': {
                'items': [i.to_dict() for i in items],
                'page': page,
                'page_size': page_size,
                'total': total,
            },
        }
    )


@chat_bp.post('/sessions')
@jwt_required()
def create_session():
    user, error = _require_user()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    title = (payload.get('title') or '').strip()
    description = (payload.get('description') or '').strip()

    try:
        data = WeKnoraClient().create_session(title=title, description=description)
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to create session: {exc}'}), 502

    weknora_session_id = str(data.get('id') or '').strip()
    if not weknora_session_id:
        return jsonify({'success': False, 'message': 'weknora did not return session id'}), 502

    existing = ChatSessionRegistry.query.filter_by(weknora_session_id=weknora_session_id).first()
    if existing and existing.owner_user_id != user.id:
        return jsonify({'success': False, 'message': 'session id conflict'}), 409
    if not existing:
        existing = ChatSessionRegistry(
            weknora_session_id=weknora_session_id,
            owner_user_id=user.id,
            title=(data.get('title') or title or '新会话'),
            description=(data.get('description') or description or ''),
        )
        db.session.add(existing)
    else:
        existing.title = (data.get('title') or title or existing.title or '新会话')
        existing.description = (data.get('description') or description or existing.description or '')
    db.session.commit()

    return jsonify({'success': True, 'data': existing.to_dict()}), 201


@chat_bp.put('/sessions/<string:session_id>')
@jwt_required()
def rename_session(session_id: str):
    user, error = _require_user()
    if error:
        return error
    item, item_error = _require_owned_session(user.id, session_id)
    if item_error:
        return item_error

    payload = request.get_json(silent=True) or {}
    title = payload.get('title')
    description = payload.get('description')

    if title is not None and not str(title).strip():
        return jsonify({'success': False, 'message': 'title cannot be empty'}), 400

    try:
        data = WeKnoraClient().update_session(
            session_id=session_id,
            title=str(title).strip() if title is not None else None,
            description=str(description).strip() if description is not None else None,
        )
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to update session: {exc}'}), 502

    if title is not None:
        item.title = str(title).strip()
    if description is not None:
        item.description = str(description).strip()
    if not item.title:
        item.title = str(data.get('title') or '')
    if not item.description:
        item.description = str(data.get('description') or '')
    db.session.commit()

    return jsonify({'success': True, 'data': item.to_dict()})


@chat_bp.delete('/sessions/<string:session_id>')
@jwt_required()
def delete_session(session_id: str):
    user, error = _require_user()
    if error:
        return error
    item, item_error = _require_owned_session(user.id, session_id)
    if item_error:
        return item_error

    try:
        WeKnoraClient().delete_session(session_id=session_id)
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to delete session: {exc}'}), 502

    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'session deleted'})


@chat_bp.delete('/sessions/batch-delete')
@jwt_required()
def delete_sessions_batch():
    user, error = _require_user()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    ids = payload.get('ids') or []
    if not isinstance(ids, list) or not ids:
        return jsonify({'success': False, 'message': 'ids is required'}), 400

    normalized_ids = [str(i).strip() for i in ids if str(i).strip()]
    owned_items = ChatSessionRegistry.query.filter(
        ChatSessionRegistry.owner_user_id == user.id,
        ChatSessionRegistry.weknora_session_id.in_(normalized_ids),
    ).all()
    owned_map = {i.weknora_session_id: i for i in owned_items}
    unauthorized = [sid for sid in normalized_ids if sid not in owned_map]
    if unauthorized:
        return jsonify({'success': False, 'message': 'contains inaccessible session ids'}), 403

    client = WeKnoraClient()
    for sid in normalized_ids:
        try:
            client.delete_session(session_id=sid)
        except WeKnoraApiError:
            # Keep local+remote best-effort consistency; if remote already gone, continue local cleanup.
            pass
        db.session.delete(owned_map[sid])
    db.session.commit()
    return jsonify({'success': True, 'message': 'sessions deleted'})


@chat_bp.delete('/sessions/<string:session_id>/messages')
@jwt_required()
def clear_session_messages(session_id: str):
    user, error = _require_user()
    if error:
        return error
    _, item_error = _require_owned_session(user.id, session_id)
    if item_error:
        return item_error
    try:
        WeKnoraClient().clear_session_messages(session_id=session_id)
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to clear messages: {exc}'}), 502
    return jsonify({'success': True, 'message': 'session messages cleared'})


@chat_bp.get('/sessions/<string:session_id>/messages')
@jwt_required()
def list_session_messages(session_id: str):
    user, error = _require_user()
    if error:
        return error
    _, item_error = _require_owned_session(user.id, session_id)
    if item_error:
        return item_error

    limit = int(request.args.get('limit', 100))
    before_time = (request.args.get('before_time') or '').strip()
    try:
        items = WeKnoraClient().list_session_messages(
            session_id=session_id,
            limit=limit,
            before_time=before_time,
        )
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to load messages: {exc}'}), 502
    return jsonify({'success': True, 'data': items})


@chat_bp.post('/sessions/<string:session_id>/stream')
@jwt_required()
def stream_chat(session_id: str):
    user, error = _require_user()
    if error:
        return error
    item, item_error = _require_owned_session(user.id, session_id)
    if item_error:
        return item_error

    payload = request.get_json(silent=True) or {}
    query = (payload.get('query') or '').strip()
    mode = (payload.get('mode') or 'quick').strip().lower()
    knowledge_base_ids = payload.get('knowledge_base_ids') or []
    mentioned_items = payload.get('mentioned_items') or []
    summary_model_id = (payload.get('summary_model_id') or '').strip()
    model_id = (payload.get('model_id') or current_app.config.get('WEKNORA_CHAT_DEFAULT_MODEL_ID') or '').strip()

    if not query:
        return jsonify({'success': False, 'message': 'query is required'}), 400

    quick_agent = current_app.config.get('WEKNORA_AGENT_QUICK_ANSWER_ID', 'builtin-quick-answer')
    smart_agent = current_app.config.get('WEKNORA_AGENT_SMART_REASONING_ID', 'builtin-smart-reasoning')
    selected_agent = smart_agent if mode == 'reasoning' else quick_agent

    upstream_payload = {
        'query': query,
        'knowledge_base_ids': knowledge_base_ids,
        'mentioned_items': mentioned_items,
        'channel': 'web',
        'disable_title': False,
        'enable_memory': True,
        'agent_id': selected_agent,
    }
    if summary_model_id:
        upstream_payload['summary_model_id'] = summary_model_id
    elif model_id:
        upstream_payload['summary_model_id'] = model_id

    client = WeKnoraClient()
    try:
        if mode == 'reasoning':
            upstream_resp = client.stream_agent_chat(session_id=session_id, payload=upstream_payload)
        else:
            upstream_resp = client.stream_knowledge_chat(session_id=session_id, payload=upstream_payload)
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to start stream chat: {exc}'}), 502

    item.updated_at = db.func.now()
    db.session.commit()

    @stream_with_context
    def generate():
        try:
            for line in upstream_resp.iter_lines(decode_unicode=True):
                if line is None:
                    continue
                if line == '':
                    yield '\n'
                    continue
                yield f'{line}\n'
        finally:
            upstream_resp.close()

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )


@chat_bp.get('/knowledge/<string:knowledge_id>/detail')
@jwt_required()
def knowledge_detail(knowledge_id: str):
    _, error = _require_user()
    if error:
        return error
    try:
        detail = WeKnoraClient().get_knowledge_detail(knowledge_id)
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to load knowledge detail: {exc}'}), 502
    return jsonify({'success': True, 'data': detail})


@chat_bp.get('/knowledge/<string:knowledge_id>/preview')
@jwt_required()
def knowledge_preview(knowledge_id: str):
    _, error = _require_user()
    if error:
        return error
    try:
        data = WeKnoraClient().preview_knowledge(knowledge_id)
    except WeKnoraApiError as exc:
        return jsonify({'success': False, 'message': f'Failed to preview knowledge: {exc}'}), 502

    content = data.get('content') or b''
    content_type = data.get('content_type') or 'application/octet-stream'

    text = ''
    if 'text' in content_type or 'json' in content_type or 'markdown' in content_type:
        try:
            text = content.decode('utf-8', errors='replace')
        except Exception:
            text = ''

    return jsonify(
        {
            'success': True,
            'data': {
                'content_type': content_type,
                'content_disposition': data.get('content_disposition') or '',
                'text': text,
                'size': len(content),
            },
        }
    )
