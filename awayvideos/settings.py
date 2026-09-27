import os
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

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

# ─── Cloudinary CDN (videos/images survive Render redeploys) ─────────────────
_cloudinary_url = (os.getenv("CLOUDINARY_URL") or "").strip().strip("'\"")
USE_CLOUDINARY = bool(_cloudinary_url)

if USE_CLOUDINARY:
    INSTALLED_APPS = [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "cloudinary_storage",
        "cloudinary",
        "catalog.apps.CatalogConfig",
    ]

    # Parse cloudinary://API_KEY:API_SECRET@CLOUD_NAME
    _cu = urlparse(_cloudinary_url)
    _cloud_name = (_cu.hostname or "").strip()
    _api_key = unquote(_cu.username or "")
    _api_secret = unquote(_cu.password or "")

    # Optional overrides (private CDN / custom CNAME)
    _private_cdn = os.getenv("CLOUDINARY_PRIVATE_CDN", "false").lower() == "true"
    _secure_distribution = (os.getenv("CLOUDINARY_SECURE_DISTRIBUTION") or "").strip()

    import cloudinary

    cloudinary.config(
        cloud_name=_cloud_name,
        api_key=_api_key,
        api_secret=_api_secret,
        secure=True,  # HTTPS CDN URLs (res.cloudinary.com)
        private_cdn=_private_cdn,
        secure_distribution=_secure_distribution or None,
    )

    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": _cloud_name,
        "API_KEY": _api_key,
        "API_SECRET": _api_secret,
        # CDN delivery
        "SECURE": True,  # https://res.cloudinary.com/...
        "MEDIA_TAG": "away-videos-media",
        "PREFIX": "away-videos",
        "INVALID_VIDEO_ERROR_MESSAGE": "Please upload a valid video file (mp4, webm, mov).",
        "STATIC_VIDEOS_EXTENSIONS": [
            "mp4",
            "webm",
            "mov",
            "m4v",
            "avi",
            "mkv",
            "ogv",
            "3gp",
        ],
        "STATIC_IMAGES_EXTENSIONS": [
            "jpg",
            "jpeg",
            "png",
            "gif",
            "webp",
            "bmp",
            "tif",
            "tiff",
        ],
    }
    if _private_cdn:
        CLOUDINARY_STORAGE["SECURE"] = True

    # Public CDN base URL (used by templates / .url on FileFields)
    if _secure_distribution:
        MEDIA_URL = f"https://{_secure_distribution}/"
    elif _private_cdn and _cloud_name:
        MEDIA_URL = f"https://{_cloud_name}-res.cloudinary.com/"
    else:
        MEDIA_URL = f"https://res.cloudinary.com/{_cloud_name}/"

    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
else:
    MEDIA_URL = "/media/"
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }

MEDIA_ROOT = BASE_DIR / "media"

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
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": (tmp_postgres.path or "/neondb").lstrip("/") or "neondb",
            "USER": tmp_postgres.username,
            "PASSWORD": tmp_postgres.password,
            "HOST": tmp_postgres.hostname,
            "PORT": tmp_postgres.port or 5432,
            "OPTIONS": dict(parse_qsl(tmp_postgres.query)),
            "CONN_MAX_AGE": 600,
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
