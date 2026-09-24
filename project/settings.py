import os
from dotenv import load_dotenv
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

_DEBUG_RAW = os.getenv('DEBUG', 'False').strip().lower()
DEBUG = _DEBUG_RAW in ('1', 'true', 'yes', 'on')

SECRET_KEY = (os.getenv('SECRET_KEY') or os.getenv('JWT_SECRET_KEY') or '').strip()
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-change-before-production'
    else:
        raise ImproperlyConfigured('SECRET_KEY es obligatorio cuando DEBUG=False')

_ALLOWED_HOSTS_RAW = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in _ALLOWED_HOSTS_RAW.split(',') if h.strip()]
_host = (os.getenv('HOST') or '').strip()
if _host and _host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_host)
PORT = os.getenv("PORT")

CSRF_COOKIE_NAME = "csrftoken"
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'rest_framework',
    'drf_yasg',
    'utils',
    'security',
    'sipo',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'utils.middleware.ErrorHandlerMiddleware'
]

ROOT_URLCONF = 'project.urls'

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_web_host = (os.getenv("WEB_HOST") or "").strip()
if _web_host and _web_host not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(_web_host)
CORS_ALLOW_CREDENTIALS = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'


def _postgres_options(schema_key: str) -> dict:
    schema = (os.getenv(schema_key) or '').strip().strip('"')
    if not schema:
        return {}
    return {'OPTIONS': {'options': f'-c search_path={schema}'}}


DATABASES = {
    'default': {
        'ENGINE': os.getenv("DB_ENGINE"),
        'NAME': os.getenv("DB_DATABASE_APP"),
        'USER': os.getenv("DB_USERNAME_APP"),
        'PASSWORD': os.getenv("DB_PASSWORD_APP"),
        'HOST': os.getenv("DB_HOST"),
        'PORT': os.getenv("DB_PORT"),
        **_postgres_options('DB_SCHEMA_APP'),
    },
    'security': {
        'ENGINE': os.getenv("DB_ENGINE"),
        'NAME': os.getenv("DB_DATABASE_SECURITY"),
        'USER': os.getenv("DB_USERNAME_SECURITY"),
        'PASSWORD': os.getenv("DB_PASSWORD_SECURITY"),
        'HOST': os.getenv("DB_HOST"),
        'PORT': os.getenv("DB_PORT"),
        **_postgres_options('DB_SCHEMA_SECURITY'),
    },
    'sip_db': {
        'ENGINE': os.getenv("DB_MYSQL_ENGINE", "django.db.backends.mysql"),
        'NAME': os.getenv("DB_MYSQL_DATABASE"),
        'USER': os.getenv("DB_MYSQL_USER"),
        'PASSWORD': os.getenv("DB_MYSQL_PASSWORD"),
        'HOST': os.getenv("DB_MYSQL_HOST"),
        'PORT': os.getenv("DB_MYSQL_PORT"),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'connect_timeout': 5,
            'read_timeout': 15,
            'write_timeout': 15,
        },
    },
    'dw_chile': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_DW_NAME'),
        'USER': os.getenv('DB_DW_USER'),
        'PASSWORD': os.getenv('DB_DW_PASSWORD'),
        'HOST': os.getenv('DB_DW_HOST'),
        'PORT': os.getenv('DB_DW_PORT', '5432'),
        'OPTIONS': {
            'options': f"-c search_path={os.getenv('DB_SCHEMA_DW_RRHH', 'flesan_rrhh')},public",
        },
    },
}

DATABASE_ROUTERS = ['project.router.SipoObraRouter']

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Abstract API — validación correo candidato (paridad SIP Nuevo / legado)
ABSTRACT_EMAIL_VALIDATION_API_KEY = os.getenv('ABSTRACT_EMAIL_VALIDATION_API_KEY', '')
ABSTRACT_EMAIL_VALIDATION_BASE_URL = os.getenv(
    'ABSTRACT_EMAIL_VALIDATION_BASE_URL',
    'https://emailvalidation.abstractapi.com/v1/',
)
ABSTRACT_EMAIL_VALIDATION_TIMEOUT = int(os.getenv('ABSTRACT_EMAIL_VALIDATION_TIMEOUT', '10'))

# iBuilder Gateway (paridad class_sip_obra.php Browser)
CHECK_IBUILDER_SAP_ENABLED = os.getenv('CHECK_IBUILDER_SAP_ENABLED', 'False').strip().lower() in (
    '1', 'true', 'yes', 'on',
)
IBUILDER_GATEWAY_URL = os.getenv(
    'IBUILDER_GATEWAY_URL',
    os.getenv('IBUILDER_API_URL', 'https://gateway.builder.cl'),
)
IBUILDER_API_URL = os.getenv('IBUILDER_API_URL', IBUILDER_GATEWAY_URL)
IBUILDER_SYNC_ENABLED = os.getenv('IBUILDER_SYNC_ENABLED', 'False').strip().lower() in (
    '1', 'true', 'yes', 'on',
)
IBUILDER_API_TOKEN = os.getenv('IBUILDER_API_TOKEN', '')
IBUILDER_API_EMAIL = os.getenv('IBUILDER_API_EMAIL', '')
IBUILDER_API_PASSWORD = os.getenv('IBUILDER_API_PASSWORD', '')
IBUILDER_API_TIMEOUT = int(os.getenv('IBUILDER_API_TIMEOUT', '15'))

# SAP SuccessFactors (paridad legado Basic Auth; desactivar SAP_SF_SYNC_ENABLED en dev)
SAP_SF_SYNC_ENABLED = os.getenv('SAP_SF_SYNC_ENABLED', 'False').strip().lower() in (
    '1', 'true', 'yes', 'on',
)
SAP_SF_UPSERT_URL = os.getenv(
    'SAP_SF_UPSERT_URL',
    'https://api19.sapsf.com/odata/v2/upsert?$format=json',
)
SAP_SF_BASIC_USER = os.getenv('SAP_SF_BASIC_USER', '')
SAP_SF_BASIC_PASSWORD = os.getenv('SAP_SF_BASIC_PASSWORD', '')
SAP_SF_OAUTH_URL = os.getenv('SAP_SF_OAUTH_URL', 'https://api19.sapsf.com/oauth/token')
SAP_SF_CLIENT_ID = os.getenv('SAP_SF_CLIENT_ID', '')
SAP_SF_CLIENT_SECRET = os.getenv('SAP_SF_CLIENT_SECRET', '')
SAP_SF_REQUEST_TIMEOUT = int(os.getenv('SAP_SF_REQUEST_TIMEOUT', '60'))

# Kiptor — simulador sueldo base obra
KIPTOR_ENABLED = os.getenv('KIPTOR_ENABLED', 'False').strip().lower() in (
    '1', 'true', 'yes', 'on',
)
KIPTOR_USER = os.getenv('KIPTOR_USER', 'flesan-kiptor')
KIPTOR_PASSWORD = os.getenv('KIPTOR_PASSWORD', '')
KIPTOR_AUTH_URL = os.getenv('KIPTOR_AUTH_URL', 'https://node.kiptor.com/autenticar')
KIPTOR_SIMULADOR_URL = os.getenv(
    'KIPTOR_SIMULADOR_URL',
    'https://node.kiptor.com/simuladorSueldo',
)
KIPTOR_FINIQUITO_URL = os.getenv(
    'KIPTOR_FINIQUITO_URL',
    'https://node.kiptor.com/simuladores/finiquitos',
)
KIPTOR_REQUEST_TIMEOUT = int(os.getenv('KIPTOR_REQUEST_TIMEOUT', '30'))

# Trabajando.com (portal empleo — paridad legado)
TRABAJANDO_COUNTRY = os.getenv('TRABAJANDO_COUNTRY', 'CL')
TRABAJANDO_CLIENT = os.getenv('TRABAJANDO_CLIENT', 'FLESAN-CL')
TRABAJANDO_TOKEN = os.getenv('TRABAJANDO_TOKEN', '')
TRABAJANDO_DOMAIN_ID = os.getenv('TRABAJANDO_DOMAIN_ID', '2957')
TRABAJANDO_FROM_DATE = os.getenv('TRABAJANDO_FROM_DATE', '20190101')
TRABAJANDO_ROWS_PER_PAGE = int(os.getenv('TRABAJANDO_ROWS_PER_PAGE', '50'))
TRABAJANDO_REQUEST_TIMEOUT = int(os.getenv('TRABAJANDO_REQUEST_TIMEOUT', '60'))
TRABAJANDO_BASE_URL = os.getenv(
    'TRABAJANDO_BASE_URL',
    'https://wsintegracion.trabajando.com',
)

def _env_flag(name: str, default: str = 'false') -> bool:
    return os.getenv(name, default).strip().lower() in (
        '1', 'true', 'yes', 'on', 'si', 'sí',
    )


# SMTP notificaciones (paridad PHPMailer legado / SIP_NUEVO)
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = _env_flag('EMAIL_USE_TLS', 'true')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'equipo_desarrollo@flesan.cl')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    EMAIL_HOST_USER or 'equipo_desarrollo@flesan.cl',
)
SIP_EMAIL_FROM = os.getenv('SIP_EMAIL_FROM', DEFAULT_FROM_EMAIL)
SIP_EMAIL_FROM_NAME = os.getenv('SIP_EMAIL_FROM_NAME', 'Sip Obra')
SIP_EMAIL_ENABLED = _env_flag('SIP_EMAIL_ENABLED', 'true')
# Modo prueba: si=true → todos los mails solo a SIP_EMAIL_TEST_OVERRIDE
SIP_EMAIL_FORCE_OVERRIDE = _env_flag('SIP_EMAIL_FORCE_OVERRIDE', 'si')
SIP_EMAIL_TEST_OVERRIDE = os.getenv(
    'SIP_EMAIL_TEST_OVERRIDE',
    'martin.norambuena@flesan.cl',
)
SIP_EMAIL_IMG_BASE = os.getenv(
    'SIP_EMAIL_IMG_BASE',
    'https://www.flesanmvi.com/controlflujo/system/view/sip/img',
)
SIPO_PORTAL_BASE_URL = os.getenv(
    'SIPO_PORTAL_BASE_URL',
    'http://localhost:5173/panel/sipo',
)
SIP_EMAIL_RRHH = os.getenv('SIP_EMAIL_RRHH', 'rrhh@flesan.cl')
SIP_EMAIL_ERROR_BUILDER = os.getenv(
    'SIP_EMAIL_ERROR_BUILDER',
    ','.join([
        'jorge.barrozo@flesan.cl',
        'administrativos-2025-grupo-flesan@flesan.cl',
        'supervisoresrh2022@flesan.cl',
        'alejandro.jara@flesan.cl',
    ]),
)
SIP_EMAIL_RECHAZO_DOCS_BCC = os.getenv(
    'SIP_EMAIL_RECHAZO_DOCS_BCC',
    ','.join([
        'jorge.barrozo@flesan.cl',
        'sofia.figueroa@flesan.cl',
        'maria.cayuqueo@flesan.cl',
        'manuel.pacha@flesan.cl',
        'nelson.aravena@flesan.cl',
        'marco.martinez@flesan.cl',
        'carolina.zavala@flesan.cl',
        'carolina.carreno@flesan.cl',
    ]),
)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'security.authentication.CustomJWTAuthentication',
    ),
    'EXCEPTION_HANDLER': 'utils.middleware.ErrorApiHandlerMiddleware',
}

JWT_ALGORITHM = "HS256"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": JWT_ALGORITHM,
    "SIGNING_KEY": os.getenv("JWT_SECRET_KEY"),
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id_aplicacion_usuario",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "security.models.user",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

CACHES = {
    'default': {
        'BACKEND': 'utils.json_cache.JSONFileCache',
        'LOCATION': os.path.join(BASE_DIR, "cache.json")
    }
}

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

X_FRAME_OPTIONS = 'ALLOW-FROM http://127.0.0.1:8000/'
