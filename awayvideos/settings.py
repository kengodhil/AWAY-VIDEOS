import os
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"

_hosts = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]
_render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if _render_host and _render_host not in _hosts:
    _hosts.append(_render_host)
if DEBUG:
    for host in ("testserver", ".localhost"):
        if host not in _hosts:
            _hosts.append(host)
ALLOWED_HOSTS = _hosts

_csrf = [o.strip() for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
if _render_host:
    origin = f"https://{_render_host}"
    if origin not in _csrf:
        _csrf.append(origin)
CSRF_TRUSTED_ORIGINS = _csrf

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "catalog.apps.CatalogConfig",
]

BUNNY_STREAM_LIBRARY_ID = (os.getenv("BUNNY_STREAM_LIBRARY_ID") or "").strip()
BUNNY_STREAM_API_KEY = (os.getenv("BUNNY_STREAM_API_KEY") or "").strip()
BUNNY_STREAM_CDN_HOSTNAME = (os.getenv("BUNNY_STREAM_CDN_HOSTNAME") or "").strip()
USE_BUNNY = bool(
    BUNNY_STREAM_LIBRARY_ID and BUNNY_STREAM_API_KEY and BUNNY_STREAM_CDN_HOSTNAME
)

if USE_BUNNY:
    _cdn = BUNNY_STREAM_CDN_HOSTNAME.replace("https://", "").replace("http://", "").rstrip("/")
    MEDIA_URL = f"https://{_cdn}/"
else:
    MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "awayvideos.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "awayvideos.wsgi.application"

_database_url = (os.getenv("DATABASE_URL") or "").strip().strip("'\"")
if _database_url.startswith("postgres"):
    tmp_postgres = urlparse(_database_url)
    _opts = dict(parse_qsl(tmp_postgres.query))
    # Neon closes idle SSL sockets; avoid long-lived pooled connections
    if "sslmode" not in _opts:
        _opts["sslmode"] = "require"
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": (tmp_postgres.path or "/neondb").lstrip("/") or "neondb",
            "USER": tmp_postgres.username,
            "PASSWORD": tmp_postgres.password,
            "HOST": tmp_postgres.hostname,
            "PORT": tmp_postgres.port or 5432,
            "OPTIONS": _opts,
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Dar_es_Salaam"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/studio/login/"
LOGIN_REDIRECT_URL = "/studio/"
LOGOUT_REDIRECT_URL = "/"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SNIPPE_BASE_URL = os.getenv("SNIPPE_BASE_URL", "https://api.snippe.sh")
SNIPPE_API_KEY = os.getenv("SNIPPE_API_KEY", "")
SNIPPE_WEBHOOK_URL = os.getenv("SNIPPE_WEBHOOK_URL", "")
SNIPPE_MOCK = os.getenv("SNIPPE_MOCK", "true").lower() == "true"

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", str(60 * 60 * 12)))
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

WATCH_PRICE_TZS = 2000
DOWNLOAD_PRICE_TZS = 1000
