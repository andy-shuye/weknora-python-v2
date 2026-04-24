from flask import Blueprint, jsonify


system_bp = Blueprint('system', __name__, url_prefix='/api/system')


@system_bp.get('/')
def system_index():
    return jsonify(
        {
            'success': True,
            'message': 'Backend API is running. Frontend should be started separately on Vite dev server.',
        }
    )


@system_bp.get('/health')
def health():
    return jsonify({'success': True, 'message': 'ok'})
