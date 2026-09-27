import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "awayvideos.settings")

application = get_wsgi_application()

# Render start command may omit seed_demo — create admin on boot
try:
    from catalog.apps import ensure_default_admin

    ensure_default_admin()
except Exception:
    pass
