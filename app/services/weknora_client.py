import requests
from flask import current_app


class WeKnoraApiError(Exception):
    pass


class WeKnoraClient:
    def __init__(self):
        base_url = (current_app.config.get('WEKNORA_BASE_URL') or '').rstrip('/')
        api_key = current_app.config.get('WEKNORA_API_KEY')
        if not base_url:
            raise WeKnoraApiError('WEKNORA_BASE_URL is not configured')
        if not api_key:
            raise WeKnoraApiError('WEKNORA_API_KEY is not configured')

        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'X-API-Key': api_key})

    def _request(self, method: str, path: str, json=None, params=None, data=None, files=None, timeout=60):
        url = f'{self.base_url}{path}'
        headers = {}
        if json is not None:
            headers['Content-Type'] = 'application/json'

        try:
            resp = self.session.request(
                method=method,
                url=url,
                json=json,
                params=params,
                data=data,
                files=files,
                headers=headers,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise WeKnoraApiError(f'Failed to call WeKnora: {exc}') from exc

        content_type = (resp.headers.get('Content-Type') or '').lower()
        is_json = 'application/json' in content_type
        payload = resp.json() if is_json else None

        if resp.status_code >= 400:
            message = None
            if isinstance(payload, dict):
                message = payload.get('message') or payload.get('error', {}).get('message')
            raise WeKnoraApiError(message or f'WeKnora API error: HTTP {resp.status_code}')

        return payload if payload is not None else {'success': True, 'data': None}

    def _request_stream(self, method: str, path: str, json=None, params=None):
        url = f'{self.base_url}{path}'
        headers = {}
        if json is not None:
            headers['Content-Type'] = 'application/json'

        try:
            resp = self.session.request(
                method=method,
                url=url,
                json=json,
                params=params,
                headers=headers,
                stream=True,
                timeout=(10, 3600),
            )
        except requests.RequestException as exc:
            raise WeKnoraApiError(f'Failed to call WeKnora stream API: {exc}') from exc

        if resp.status_code >= 400:
            message = None
            content_type = (resp.headers.get('Content-Type') or '').lower()
            if 'application/json' in content_type:
                try:
                    payload = resp.json()
                    if isinstance(payload, dict):
                        message = payload.get('message') or payload.get('error', {}).get('message')
                except Exception:
                    message = None
            resp.close()
            raise WeKnoraApiError(message or f'WeKnora stream API error: HTTP {resp.status_code}')

        return resp

    def list_knowledge_bases(self):
        result = self._request('GET', '/knowledge-bases')
        return result.get('data') or []

    def get_knowledge_base(self, kb_id: str):
        result = self._request('GET', f'/knowledge-bases/{kb_id}')
        return result.get('data') or {}

    def create_knowledge_base(self, name: str, description: str = '', kb_type: str = 'document'):
        cfg = current_app.config

        chunking_config = {
            'chunk_size': cfg.get('WEKNORA_KB_CHUNK_SIZE', 1000),
            'chunk_overlap': cfg.get('WEKNORA_KB_CHUNK_OVERLAP', 200),
            'separators': cfg.get('WEKNORA_KB_SEPARATORS', ['\n\n', '\n']),
            'enable_multimodal': cfg.get('WEKNORA_KB_ENABLE_MULTIMODAL', True),
            'parser_engine_rules': cfg.get('WEKNORA_KB_PARSER_ENGINE_RULES', []),
            'enable_parent_child': cfg.get('WEKNORA_KB_ENABLE_PARENT_CHILD', False),
            'parent_chunk_size': cfg.get('WEKNORA_KB_PARENT_CHUNK_SIZE', 4096),
            'child_chunk_size': cfg.get('WEKNORA_KB_CHILD_CHUNK_SIZE', 384),
        }

        vlm_model_id = cfg.get('WEKNORA_KB_DEFAULT_VLM_MODEL_ID', '')
        vlm_enabled = bool(vlm_model_id)

        payload = {
            'name': name,
            'description': description,
            'type': kb_type,
            'is_temporary': False,
            'chunking_config': chunking_config,
            'storage_provider_config': {'provider': cfg.get('WEKNORA_KB_STORAGE_PROVIDER', 'local')},
            'question_generation_config': {
                'enabled': cfg.get('WEKNORA_KB_QUESTION_GENERATION_ENABLED', False),
                'question_count': cfg.get('WEKNORA_KB_QUESTION_COUNT', 3),
            },
            'vlm_config': {
                'enabled': vlm_enabled,
                'model_id': vlm_model_id,
            },
            'asr_config': {
                'enabled': cfg.get('WEKNORA_KB_ASR_ENABLED', False),
                'model_id': cfg.get('WEKNORA_KB_ASR_MODEL_ID', ''),
                'language': cfg.get('WEKNORA_KB_ASR_LANGUAGE', ''),
            },
            'image_processing_config': {
                'model_id': vlm_model_id,
            },
        }

        embedding_model_id = (cfg.get('WEKNORA_KB_DEFAULT_EMBEDDING_MODEL_ID') or '').strip()
        summary_model_id = (cfg.get('WEKNORA_KB_DEFAULT_SUMMARY_MODEL_ID') or '').strip()

        if embedding_model_id:
            payload['embedding_model_id'] = embedding_model_id
        if summary_model_id:
            payload['summary_model_id'] = summary_model_id

        result = self._request('POST', '/knowledge-bases', json=payload)
        return result.get('data') or {}

    def update_knowledge_base(self, kb_id: str, name: str = None, description: str = None):
        payload = {}
        if name is not None:
            payload['name'] = name
        if description is not None:
            payload['description'] = description
        result = self._request('PUT', f'/knowledge-bases/{kb_id}', json=payload)
        return result.get('data') or {}

    def delete_knowledge_base(self, kb_id: str):
        self._request('DELETE', f'/knowledge-bases/{kb_id}')
        return True

    def list_knowledge_documents(self, kb_id: str, page: int = 1, page_size: int = 20):
        result = self._request('GET', f'/knowledge-bases/{kb_id}/knowledge', params={'page': page, 'page_size': page_size})
        return {
            'items': result.get('data') or [],
            'page': result.get('page', page),
            'page_size': result.get('page_size', page_size),
            'total': result.get('total', 0),
        }

    def list_knowledge_tags(self, kb_id: str, page: int = 1, page_size: int = 50, keyword: str = ''):
        params = {'page': page, 'page_size': page_size}
        if keyword:
            params['keyword'] = keyword
        result = self._request('GET', f'/knowledge-bases/{kb_id}/tags', params=params)
        raw = result.get('data')
        if isinstance(raw, dict):
            items = raw.get('data') or raw.get('tags') or []
            total = raw.get('total', len(items))
            current_page = raw.get('page', page)
            current_page_size = raw.get('page_size', page_size)
        else:
            items = raw or []
            total = result.get('total', len(items))
            current_page = result.get('page', page)
            current_page_size = result.get('page_size', page_size)
        return {
            'items': items,
            'page': current_page,
            'page_size': current_page_size,
            'total': total,
        }

    def create_knowledge_tag(self, kb_id: str, name: str, color: str = '', sort_order: int = 0):
        payload = {'name': name}
        if color:
            payload['color'] = color
        if sort_order:
            payload['sort_order'] = sort_order
        result = self._request('POST', f'/knowledge-bases/{kb_id}/tags', json=payload)
        return result.get('data') or {}

    def update_knowledge_tag(self, kb_id: str, tag_id: str, name: str = None, color: str = None, sort_order: int = None):
        payload = {}
        if name is not None:
            payload['name'] = name
        if color is not None:
            payload['color'] = color
        if sort_order is not None:
            payload['sort_order'] = sort_order
        result = self._request('PUT', f'/knowledge-bases/{kb_id}/tags/{tag_id}', json=payload)
        return result.get('data') or {}

    def delete_knowledge_tag(self, kb_id: str, tag_id: str, force: bool = False):
        params = {'force': 'true'} if force else None
        self._request('DELETE', f'/knowledge-bases/{kb_id}/tags/{tag_id}', params=params)
        return True

    def batch_update_knowledge_tags(self, updates: dict):
        result = self._request('PUT', '/knowledge/tags', json={'updates': updates})
        return result.get('data') or result

    def upload_knowledge_file(self, kb_id: str, file_storage, enable_multimodel: bool = True):
        files = {
            'file': (file_storage.filename, file_storage.stream, file_storage.mimetype or 'application/octet-stream')
        }
        data = {'enable_multimodel': str(enable_multimodel).lower()}
        result = self._request('POST', f'/knowledge-bases/{kb_id}/knowledge/file', data=data, files=files)
        return result.get('data') or {}

    def create_organization(self, name: str, description: str = ''):
        payload = {'name': name, 'description': description}
        result = self._request('POST', '/organizations', json=payload)
        return result.get('data') or {}

    def update_organization(self, organization_id: str, name: str = None, description: str = None):
        payload = {}
        if name is not None:
            payload['name'] = name
        if description is not None:
            payload['description'] = description
        if not payload:
            return {}
        result = self._request('PUT', f'/organizations/{organization_id}', json=payload)
        return result.get('data') or {}

    def share_knowledge_base(self, kb_id: str, organization_id: str, permission: str = 'read'):
        payload = {'organization_id': organization_id, 'permission': permission}
        result = self._request('POST', f'/knowledge-bases/{kb_id}/shares', json=payload)
        return result.get('data') or {}

    def list_knowledge_base_shares(self, kb_id: str):
        result = self._request('GET', f'/knowledge-bases/{kb_id}/shares')
        data = result.get('data')
        if isinstance(data, dict):
            return data.get('shares', [])
        return data or []

    def delete_knowledge_base_share(self, kb_id: str, share_id: str):
        self._request('DELETE', f'/knowledge-bases/{kb_id}/shares/{share_id}')
        return True

    # Chat/session/message APIs
    def list_sessions(self, page: int = 1, page_size: int = 100):
        result = self._request('GET', '/sessions', params={'page': page, 'page_size': page_size})
        return {
            'items': result.get('data') or [],
            'page': result.get('page', page),
            'page_size': result.get('page_size', page_size),
            'total': result.get('total', 0),
        }

    def create_session(self, title: str = '', description: str = ''):
        payload = {'title': title, 'description': description}
        result = self._request('POST', '/sessions', json=payload)
        return result.get('data') or {}

    def update_session(self, session_id: str, title: str = None, description: str = None):
        payload = {}
        if title is not None:
            payload['title'] = title
        if description is not None:
            payload['description'] = description
        result = self._request('PUT', f'/sessions/{session_id}', json=payload)
        return result.get('data') or {}

    def delete_session(self, session_id: str):
        self._request('DELETE', f'/sessions/{session_id}')
        return True

    def delete_sessions_batch(self, ids: list[str]):
        payload = {'ids': ids}
        self._request('DELETE', '/sessions/batch', json=payload)
        return True

    def clear_session_messages(self, session_id: str):
        self._request('DELETE', f'/sessions/{session_id}/messages')
        return True

    def list_session_messages(self, session_id: str, limit: int = 50, before_time: str = ''):
        params = {'limit': limit}
        if before_time:
            params['before_time'] = before_time
        result = self._request('GET', f'/messages/{session_id}/load', params=params)
        return result.get('data') or []

    def stream_knowledge_chat(self, session_id: str, payload: dict):
        return self._request_stream('POST', f'/knowledge-chat/{session_id}', json=payload)

    def stream_agent_chat(self, session_id: str, payload: dict):
        return self._request_stream('POST', f'/agent-chat/{session_id}', json=payload)

    def get_knowledge_detail(self, knowledge_id: str):
        result = self._request('GET', f'/knowledge/{knowledge_id}')
        return result.get('data') or {}

    def preview_knowledge(self, knowledge_id: str):
        url = f'{self.base_url}/knowledge/{knowledge_id}/preview'
        try:
            resp = self.session.request('GET', url=url, timeout=60)
        except requests.RequestException as exc:
            raise WeKnoraApiError(f'Failed to preview knowledge: {exc}') from exc
        if resp.status_code >= 400:
            message = None
            if 'application/json' in (resp.headers.get('Content-Type') or '').lower():
                try:
                    payload = resp.json()
                    if isinstance(payload, dict):
                        message = payload.get('message') or payload.get('error', {}).get('message')
                except Exception:
                    message = None
            raise WeKnoraApiError(message or f'Knowledge preview API error: HTTP {resp.status_code}')
        return {
            'content_type': resp.headers.get('Content-Type') or 'application/octet-stream',
            'content_disposition': resp.headers.get('Content-Disposition') or '',
            'content': resp.content,
        }

    def list_models(self):
        result = self._request('GET', '/models')
        data = result.get('data')
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get('models') or data.get('items') or []
        return []
