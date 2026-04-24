from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models.department import Department
from app.models.user import User
from app.utils.constants import ROLE_USER, VALID_ROLES
from app.utils.security import hash_password, verify_password


class AuthError(Exception):
    pass


class AuthConfigError(AuthError):
    pass


class AuthUnavailableError(AuthError):
    pass


class InvalidAuthProviderError(AuthError):
    pass


@dataclass
class AuthResult:
    user: User
    provider_used: str
    fallback_used: bool = False


@dataclass
class LdapIdentity:
    login_name: str
    domain_account: str
    full_name: str
    email: str
    department: str
    dn: str
    sid: str


def _extract_account_alias(account: str) -> str:
    value = (account or "").strip()
    if not value:
        return ""
    if "\\" in value:
        return value.split("\\", 1)[1]
    if "@" in value:
        return value.split("@", 1)[0]
    return value


def _split_account_candidates(account: str) -> list[str]:
    account = (account or "").strip()
    if not account:
        return []

    values = {account, _extract_account_alias(account)}
    if "\\" in account:
        values.add(account.split("\\", 1)[1])
    if "@" in account:
        values.add(account.split("@", 1)[0])
    return [v for v in values if v]


def _find_local_user_for_ldap(account: str, email: str = "") -> Optional[User]:
    candidates = _split_account_candidates(account)
    clauses = []
    if candidates:
        clauses.append(User.domain_account.in_(candidates))
        clauses.append(User.login_name.in_(candidates))
    if email:
        clauses.append(User.email == email.lower())
    if not clauses:
        return None

    return User.query.filter(or_(*clauses)).order_by(User.id.asc()).first()


def _normalize_provider_name(provider_name: Optional[str]) -> str:
    value = (provider_name or "").strip().lower()
    return value or "local"


class LocalAuthProvider:
    name = "local"

    def authenticate(self, account: str, password: str) -> Optional[User]:
        user = User.query.filter_by(login_name=account).first()
        if not user:
            return None
        if not user.is_enabled:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user


class LdapAuthProvider:
    name = "ldap"

    @staticmethod
    def _attr(entry, key: str) -> str:
        if key not in entry:
            return ""
        value = entry[key].value
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _build_bind_account(account: str, account_domain: str) -> str:
        raw = (account or "").strip()
        if not raw:
            return raw
        if "\\" in raw or "@" in raw:
            return raw
        if account_domain:
            return f"{raw}@{account_domain}"
        return raw

    def _get_required_config(self):
        cfg = current_app.config
        if not cfg.get("LDAP_ENABLED", False):
            raise AuthConfigError("LDAP authentication is not enabled.")

        server_uri = (cfg.get("LDAP_SERVER_URI") or "").strip()
        search_base_dn = (cfg.get("LDAP_SEARCH_BASE_DN") or "").strip()
        user_filter_template = (cfg.get("LDAP_USER_FILTER_TEMPLATE") or "").strip()
        bind_dn = (cfg.get("LDAP_BIND_DN") or "").strip()
        bind_password = cfg.get("LDAP_BIND_PASSWORD") or ""
        user_attributes = cfg.get("LDAP_USER_ATTRIBUTES") or []

        if not server_uri:
            raise AuthConfigError("LDAP_SERVER_URI is required when LDAP is enabled.")
        if not user_filter_template:
            raise AuthConfigError("LDAP_USER_FILTER_TEMPLATE is required when LDAP is enabled.")
        if search_base_dn and "{account}" not in user_filter_template:
            raise AuthConfigError("LDAP_USER_FILTER_TEMPLATE must include {account}.")
        if not isinstance(user_attributes, list):
            user_attributes = []

        return {
            "server_uri": server_uri,
            "use_ssl": bool(cfg.get("LDAP_USE_SSL", False)),
            "timeout": int(cfg.get("LDAP_CONNECT_TIMEOUT", 8)),
            "search_base_dn": search_base_dn,
            "bind_dn": bind_dn,
            "bind_password": bind_password,
            "user_filter_template": user_filter_template,
            "account_domain": (cfg.get("LDAP_ACCOUNT_DOMAIN") or "").strip(),
            "auto_create_user": bool(cfg.get("LDAP_AUTO_CREATE_USER", True)),
            "sync_full_name": bool(cfg.get("LDAP_SYNC_FULL_NAME", True)),
            "sync_email": bool(cfg.get("LDAP_SYNC_EMAIL", True)),
            "sync_department": bool(cfg.get("LDAP_SYNC_DEPARTMENT", True)),
            "auto_create_department": bool(cfg.get("LDAP_AUTO_CREATE_DEPARTMENT", False)),
            "default_role_level": str(cfg.get("LDAP_DEFAULT_ROLE_LEVEL") or ROLE_USER),
            "user_attributes": [str(i) for i in user_attributes if str(i).strip()],
        }

    @staticmethod
    def _generate_unique_email(base_email: str, login_name: str, current_user_id: Optional[int] = None) -> str:
        candidate = (base_email or "").strip().lower()
        if not candidate:
            candidate = f"{login_name}@ldap.local"

        if "@" not in candidate:
            candidate = f"{candidate}@ldap.local"

        local_part, domain_part = candidate.split("@", 1)
        index = 0
        while True:
            email = f"{local_part}@{domain_part}" if index == 0 else f"{local_part}+{index}@{domain_part}"
            exists = User.query.filter(User.email == email)
            if current_user_id is not None:
                exists = exists.filter(User.id != current_user_id)
            if not exists.first():
                return email
            index += 1

    @staticmethod
    def _resolve_department(name: str, auto_create_department: bool) -> Optional[Department]:
        dept_name = (name or "").strip()
        if not dept_name:
            return None

        department = Department.query.filter_by(name=dept_name).first()
        if department:
            return department
        if not auto_create_department:
            return None

        department = Department(name=dept_name, is_enabled=True)
        db.session.add(department)
        db.session.flush()
        return department

    def _sync_local_user(self, identity: LdapIdentity, cfg: dict) -> Optional[User]:
        lookup_account = identity.domain_account or identity.login_name
        user = _find_local_user_for_ldap(lookup_account, identity.email)

        if not user and not cfg["auto_create_user"]:
            return None

        if not user:
            role_level = cfg["default_role_level"] if cfg["default_role_level"] in VALID_ROLES else ROLE_USER
            department = self._resolve_department(identity.department, cfg["auto_create_department"])
            email = self._generate_unique_email(identity.email, identity.login_name)

            user = User(
                login_name=identity.login_name,
                domain_account=identity.domain_account or identity.login_name,
                full_name=identity.full_name or identity.login_name,
                email=email,
                department_id=department.id if department else None,
                department_name=department.name if department else (identity.department or None),
                role_level=role_level,
                password_hash=hash_password(uuid4().hex),
                is_enabled=True,
            )
            db.session.add(user)
            db.session.commit()
            return user

        changed = False

        if not user.domain_account and identity.domain_account:
            user.domain_account = identity.domain_account
            changed = True

        if cfg["sync_full_name"] and identity.full_name and user.full_name != identity.full_name:
            user.full_name = identity.full_name
            changed = True

        if cfg["sync_email"]:
            expected_email = self._generate_unique_email(identity.email, user.login_name, current_user_id=user.id)
            if expected_email and user.email != expected_email:
                user.email = expected_email
                changed = True

        if cfg["sync_department"]:
            department = self._resolve_department(identity.department, cfg["auto_create_department"])
            target_department_id = department.id if department else None
            target_department_name = department.name if department else (identity.department or None)

            if user.department_id != target_department_id:
                user.department_id = target_department_id
                changed = True
            if user.department_name != target_department_name:
                user.department_name = target_department_name
                changed = True

        if changed:
            db.session.commit()

        return user

    def _query_identity_with_service_conn(self, service_conn, search_base_dn: str, user_filter: str, attributes: list[str]) -> Optional[LdapIdentity]:
        ok = service_conn.search(
            search_base=search_base_dn,
            search_filter=user_filter,
            attributes=attributes,
            size_limit=1,
        )
        if not ok or not service_conn.entries:
            return None

        entry = service_conn.entries[0]
        login_name = self._attr(entry, "sAMAccountName") or self._attr(entry, "uid")
        full_name = self._attr(entry, "displayName") or self._attr(entry, "cn") or login_name
        email = self._attr(entry, "mail")
        department = self._attr(entry, "department")
        sid = self._attr(entry, "objectSid")
        dn = str(entry.entry_dn)

        return LdapIdentity(
            login_name=login_name,
            domain_account=login_name,
            full_name=full_name,
            email=email,
            department=department,
            dn=dn,
            sid=sid,
        )

    def _authenticate_and_get_identity(self, account: str, password: str) -> Optional[LdapIdentity]:
        try:
            from ldap3 import ALL, Connection, Server
            from ldap3.core.exceptions import LDAPException, LDAPInvalidCredentialsResult
            from ldap3.utils.conv import escape_filter_chars
        except Exception as exc:
            raise AuthUnavailableError(
                "LDAP runtime dependency missing. Install `ldap3` to enable LDAP authentication."
            ) from exc

        cfg = self._get_required_config()
        account_alias = _extract_account_alias(account)

        server = Server(
            cfg["server_uri"],
            use_ssl=cfg["use_ssl"],
            connect_timeout=cfg["timeout"],
            get_info=ALL,
        )

        service_conn = None
        try:
            user_identity = None

            if cfg["bind_dn"] and cfg["search_base_dn"]:
                service_conn = Connection(
                    server,
                    user=cfg["bind_dn"],
                    password=cfg["bind_password"],
                    auto_bind=True,
                    receive_timeout=cfg["timeout"],
                )

                escaped = escape_filter_chars(account_alias)
                user_filter = cfg["user_filter_template"].format(account=escaped)
                user_identity = self._query_identity_with_service_conn(
                    service_conn=service_conn,
                    search_base_dn=cfg["search_base_dn"],
                    user_filter=user_filter,
                    attributes=cfg["user_attributes"],
                )
                if not user_identity:
                    return None

                bind_user = user_identity.dn
            else:
                bind_user = self._build_bind_account(account, cfg["account_domain"])

            user_conn = Connection(
                server,
                user=bind_user,
                password=password,
                auto_bind=True,
                receive_timeout=cfg["timeout"],
            )
            user_conn.unbind()

            if user_identity:
                return user_identity

            # direct bind mode fallback: keep minimal identity if no directory search is configured
            return LdapIdentity(
                login_name=account_alias or account,
                domain_account=account_alias or account,
                full_name=account_alias or account,
                email="",
                department="",
                dn="",
                sid="",
            )

        except LDAPInvalidCredentialsResult:
            return None
        except LDAPException as exc:
            message = str(exc).lower()
            if any(i in message for i in ["invalidcredentials", "invalid credentials", "data 52e"]):
                return None
            raise AuthUnavailableError(f"LDAP service unavailable: {exc}") from exc
        except Exception as exc:
            raise AuthUnavailableError(f"LDAP service unavailable: {exc}") from exc
        finally:
            if service_conn is not None and service_conn.bound:
                service_conn.unbind()

    def authenticate(self, account: str, password: str) -> Optional[User]:
        identity = self._authenticate_and_get_identity(account, password)
        if not identity:
            return None

        cfg = self._get_required_config()
        try:
            user = self._sync_local_user(identity, cfg)
        except Exception as exc:
            db.session.rollback()
            raise AuthUnavailableError(f"Failed to sync local user profile: {exc}") from exc

        if not user:
            return None
        if not user.is_enabled:
            return None
        return user


def get_auth_provider(provider_name: str):
    normalized = _normalize_provider_name(provider_name)
    if normalized == "local":
        return LocalAuthProvider()
    if normalized in {"ldap", "ad"}:
        return LdapAuthProvider()
    raise InvalidAuthProviderError(f"Unsupported auth provider: {provider_name}")


def authenticate_user(account: str, password: str, requested_provider: Optional[str] = None) -> AuthResult:
    configured = _normalize_provider_name(current_app.config.get("AUTH_PROVIDER", "local"))
    allow_fallback = bool(current_app.config.get("AUTH_ALLOW_LOCAL_FALLBACK", True))
    selected = _normalize_provider_name(requested_provider) if requested_provider else configured

    if selected == "auto":
        if current_app.config.get("LDAP_ENABLED", False):
            try:
                ldap_user = LdapAuthProvider().authenticate(account, password)
                if ldap_user:
                    return AuthResult(user=ldap_user, provider_used="ldap", fallback_used=False)
            except (AuthConfigError, AuthUnavailableError):
                pass

        local_user = LocalAuthProvider().authenticate(account, password)
        if not local_user:
            raise AuthError("Invalid credentials or disabled account")
        return AuthResult(user=local_user, provider_used="local", fallback_used=True)

    if selected in {"ldap", "ad"}:
        ldap_error: Optional[Exception] = None
        try:
            ldap_user = LdapAuthProvider().authenticate(account, password)
        except (AuthConfigError, AuthUnavailableError) as exc:
            ldap_error = exc
            if not allow_fallback:
                raise
            ldap_user = None
        if ldap_user:
            return AuthResult(user=ldap_user, provider_used="ldap", fallback_used=False)
        if allow_fallback:
            local_user = LocalAuthProvider().authenticate(account, password)
            if local_user:
                return AuthResult(user=local_user, provider_used="local", fallback_used=True)
        if ldap_error:
            raise AuthError(f"LDAP login failed: {ldap_error}")
        raise AuthError("Invalid credentials or disabled account")

    if selected == "local":
        local_user = LocalAuthProvider().authenticate(account, password)
        if not local_user:
            raise AuthError("Invalid credentials or disabled account")
        return AuthResult(user=local_user, provider_used="local", fallback_used=False)

    raise InvalidAuthProviderError(f"Unsupported auth provider: {selected}")
