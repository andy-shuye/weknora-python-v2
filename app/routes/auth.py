from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app.models.user import User
from app.services.auth_provider import (
    AuthConfigError,
    AuthError,
    AuthUnavailableError,
    InvalidAuthProviderError,
    authenticate_user,
)


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    account = (payload.get("account") or "").strip()
    password = payload.get("password") or ""
    auth_provider = (payload.get("auth_provider") or payload.get("auth_type") or "").strip().lower()

    if not account or not password:
        return jsonify({"success": False, "message": "account and password are required"}), 400

    try:
        result = authenticate_user(account=account, password=password, requested_provider=auth_provider or None)
        user = result.user
    except InvalidAuthProviderError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except AuthConfigError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except AuthUnavailableError as exc:
        return jsonify({"success": False, "message": str(exc)}), 503
    except AuthError as exc:
        return jsonify({"success": False, "message": str(exc)}), 401

    additional_claims = {
        "role_level": user.role_level,
        "department_id": user.department_id,
        "department_name": user.department_name,
        "login_name": user.login_name,
        "auth_provider": result.provider_used,
    }
    token = create_access_token(identity=str(user.id), additional_claims=additional_claims)

    return jsonify(
        {
            "success": True,
            "data": {
                "token": token,
                "user": user.to_dict(),
                "auth_provider": result.provider_used,
                "fallback_used": result.fallback_used,
            },
        }
    )


@auth_bp.get("/login-options")
def login_options():
    auth_provider = (current_app.config.get("AUTH_PROVIDER") or "local").lower()
    ldap_enabled = bool(current_app.config.get("LDAP_ENABLED", False))
    allow_local_fallback = bool(current_app.config.get("AUTH_ALLOW_LOCAL_FALLBACK", True))

    available = ["local"]
    if ldap_enabled:
        available.append("ldap")
    if ldap_enabled and allow_local_fallback:
        available.append("auto")

    return jsonify(
        {
            "success": True,
            "data": {
                "default_provider": auth_provider,
                "available_providers": available,
                "ldap_enabled": ldap_enabled,
                "allow_local_fallback": allow_local_fallback,
            },
        }
    )


@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    try:
        user = User.query.get(int(user_id))
    except (TypeError, ValueError):
        user = None
    if not user or not user.is_enabled:
        return jsonify({"success": False, "message": "User not found or disabled"}), 404
    return jsonify({"success": True, "data": user.to_dict()})


@auth_bp.post("/logout")
@jwt_required()
def logout():
    return jsonify({"success": True, "message": "Logout success"})
