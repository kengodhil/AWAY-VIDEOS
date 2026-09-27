import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"

# Comma-separated hosts; on Render also allow the service hostname automatically
_hosts = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]
_render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if _render_host and _render_host not in _hosts:
    _hosts.append(_render_host)
if DEBUG:
    for host in ("testserver", ".localhost"):
        if host not in _hosts:
            _hosts.append(host)
ALLOWED_HOSTS = _hosts

# CSRF trusted origins (required for HTTPS on Render)
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
    "catalog",
]

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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "catalog.User"

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
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "video_list"
LOGOUT_REDIRECT_URL = "home"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Behind Render / other reverse proxies
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Selcom checkout (https://developers.selcommobile.com/)
SELCOM_BASE_URL = os.getenv("SELCOM_BASE_URL", "https://apigw.selcommobile.com")
SELCOM_API_KEY = os.getenv("SELCOM_API_KEY", "")
SELCOM_API_SECRET = os.getenv("SELCOM_API_SECRET", "")
SELCOM_VENDOR = os.getenv("SELCOM_VENDOR", "")
SELCOM_WEBHOOK_URL = os.getenv("SELCOM_WEBHOOK_URL", "")
SELCOM_MOCK = os.getenv("SELCOM_MOCK", "true").lower() == "true"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
