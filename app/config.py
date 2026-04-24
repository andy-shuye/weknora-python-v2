import json
import os
from datetime import timedelta
from urllib.parse import quote_plus


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_json(name: str, default):
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=_env_int('JWT_EXPIRES_HOURS', 8))

    DB_HOST = os.getenv('DB_HOST', '192.168.4.227')
    DB_PORT = _env_int('DB_PORT', 3306)
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
    DB_NAME = os.getenv('DB_NAME', 'weknora_python')

    _db_user_escaped = quote_plus(DB_USER)
    _db_password_escaped = quote_plus(DB_PASSWORD)
    _default_mysql_uri = (
        f"mysql+pymysql://{_db_user_escaped}:{_db_password_escaped}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    _database_url_override = (os.getenv('DATABASE_URL') or '').strip()

    if _database_url_override:
        _lower_url = _database_url_override.lower()
        if not (_lower_url.startswith('mysql://') or _lower_url.startswith('mysql+pymysql://')):
            raise RuntimeError(
                'Only MySQL is supported for this project. '
                'Please use DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME or a MySQL DATABASE_URL.'
            )
        SQLALCHEMY_DATABASE_URI = _database_url_override
    else:
        SQLALCHEMY_DATABASE_URI = _default_mysql_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WEKNORA_BASE_URL = os.getenv('WEKNORA_BASE_URL', 'http://192.168.40.188/api/v1')
    WEKNORA_API_KEY = os.getenv('WEKNORA_API_KEY', 'sk-_0yRXTTjUODNNhTnyelGBEE0ultmikgQpyRU5K8HU8ryzzy9')

    # Knowledge-base defaults used when creating KB via weknora-python.
    WEKNORA_KB_DEFAULT_TYPE = os.getenv('WEKNORA_KB_DEFAULT_TYPE', 'document')
    WEKNORA_KB_DEFAULT_EMBEDDING_MODEL_ID = os.getenv('WEKNORA_KB_DEFAULT_EMBEDDING_MODEL_ID', '')
    WEKNORA_KB_DEFAULT_SUMMARY_MODEL_ID = os.getenv('WEKNORA_KB_DEFAULT_SUMMARY_MODEL_ID', '')
    WEKNORA_KB_DEFAULT_VLM_MODEL_ID = os.getenv('WEKNORA_KB_DEFAULT_VLM_MODEL_ID', '')

    WEKNORA_KB_ENABLE_MULTIMODAL = _env_bool('WEKNORA_KB_ENABLE_MULTIMODAL', True)
    WEKNORA_KB_ENABLE_PARENT_CHILD = _env_bool('WEKNORA_KB_ENABLE_PARENT_CHILD', False)
    WEKNORA_KB_CHUNK_SIZE = _env_int('WEKNORA_KB_CHUNK_SIZE', 1000)
    WEKNORA_KB_CHUNK_OVERLAP = _env_int('WEKNORA_KB_CHUNK_OVERLAP', 200)
    WEKNORA_KB_PARENT_CHUNK_SIZE = _env_int('WEKNORA_KB_PARENT_CHUNK_SIZE', 4096)
    WEKNORA_KB_CHILD_CHUNK_SIZE = _env_int('WEKNORA_KB_CHILD_CHUNK_SIZE', 384)

    WEKNORA_KB_SEPARATORS = _env_json(
        'WEKNORA_KB_SEPARATORS',
        ['\n\n', '\n', '。', '！', '？', ';', '；'],
    )
    WEKNORA_KB_PARSER_ENGINE_RULES = _env_json('WEKNORA_KB_PARSER_ENGINE_RULES', [])

    WEKNORA_KB_STORAGE_PROVIDER = os.getenv('WEKNORA_KB_STORAGE_PROVIDER', 'local')

    WEKNORA_KB_ASR_ENABLED = _env_bool('WEKNORA_KB_ASR_ENABLED', False)
    WEKNORA_KB_ASR_MODEL_ID = os.getenv('WEKNORA_KB_ASR_MODEL_ID', '')
    WEKNORA_KB_ASR_LANGUAGE = os.getenv('WEKNORA_KB_ASR_LANGUAGE', '')

    WEKNORA_KB_QUESTION_GENERATION_ENABLED = _env_bool('WEKNORA_KB_QUESTION_GENERATION_ENABLED', False)
    WEKNORA_KB_QUESTION_COUNT = _env_int('WEKNORA_KB_QUESTION_COUNT', 3)

    # Reserved: chat/agent level defaults (not directly used in KB create API)
    WEKNORA_CHAT_DEFAULT_MODEL_ID = os.getenv('WEKNORA_CHAT_DEFAULT_MODEL_ID', '')
    WEKNORA_CHAT_DEFAULT_RERANK_MODEL_ID = os.getenv('WEKNORA_CHAT_DEFAULT_RERANK_MODEL_ID', '')
    WEKNORA_AGENT_QUICK_ANSWER_ID = os.getenv('WEKNORA_AGENT_QUICK_ANSWER_ID', 'builtin-quick-answer')
    WEKNORA_AGENT_SMART_REASONING_ID = os.getenv('WEKNORA_AGENT_SMART_REASONING_ID', 'builtin-smart-reasoning')

    AUTH_PROVIDER = os.getenv('AUTH_PROVIDER', 'local').lower()
    AUTH_ALLOW_LOCAL_FALLBACK = _env_bool('AUTH_ALLOW_LOCAL_FALLBACK', True)

    LDAP_ENABLED = _env_bool('LDAP_ENABLED', False)
    LDAP_SERVER_URI = os.getenv('LDAP_SERVER_URI', '')
    LDAP_USE_SSL = _env_bool('LDAP_USE_SSL', False)
    LDAP_CONNECT_TIMEOUT = _env_int('LDAP_CONNECT_TIMEOUT', 8)
    LDAP_SEARCH_BASE_DN = os.getenv('LDAP_SEARCH_BASE_DN', '')
    LDAP_BIND_DN = os.getenv('LDAP_BIND_DN', '')
    LDAP_BIND_PASSWORD = os.getenv('LDAP_BIND_PASSWORD', '')
    LDAP_USER_FILTER_TEMPLATE = os.getenv('LDAP_USER_FILTER_TEMPLATE', '(sAMAccountName={account})')
    LDAP_ACCOUNT_DOMAIN = os.getenv('LDAP_ACCOUNT_DOMAIN', '')
    LDAP_USER_ATTRIBUTES = _env_json(
        'LDAP_USER_ATTRIBUTES',
        ['objectSid', 'sAMAccountName', 'displayName', 'cn', 'mail', 'department'],
    )
    LDAP_AUTO_CREATE_USER = _env_bool('LDAP_AUTO_CREATE_USER', True)
    LDAP_SYNC_FULL_NAME = _env_bool('LDAP_SYNC_FULL_NAME', True)
    LDAP_SYNC_EMAIL = _env_bool('LDAP_SYNC_EMAIL', True)
    LDAP_SYNC_DEPARTMENT = _env_bool('LDAP_SYNC_DEPARTMENT', True)
    LDAP_AUTO_CREATE_DEPARTMENT = _env_bool('LDAP_AUTO_CREATE_DEPARTMENT', False)
    LDAP_DEFAULT_ROLE_LEVEL = os.getenv('LDAP_DEFAULT_ROLE_LEVEL', 'user').strip().lower()


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
