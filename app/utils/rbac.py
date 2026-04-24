from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request

from app.utils.constants import ROLE_LEVELS


def role_required(*roles: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            current_role = claims.get('role_level')
            if current_role not in ROLE_LEVELS:
                return jsonify({'success': False, 'message': 'Invalid role in token'}), 403
            allowed = any(
                ROLE_LEVELS.get(current_role, 0) >= ROLE_LEVELS.get(role, 999)
                for role in roles
            )
            if not allowed:
                return jsonify({'success': False, 'message': 'Permission denied'}), 403
            return func(*args, **kwargs)

        return wrapper

    return decorator
