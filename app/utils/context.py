from flask_jwt_extended import get_jwt_identity

from app.models.user import User


def get_current_user():
    identity = get_jwt_identity()
    if identity is None:
        return None
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    return User.query.get(user_id)
