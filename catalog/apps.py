from django.apps import AppConfig


def ensure_default_admin(**kwargs):
    """Create or reset studio admin so login works without Shell."""
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        username = "admin"
        password = "admin123"
        user = User.objects.filter(username=username).first()
        if user is None:
            User.objects.create_superuser(
                username=username,
                email="admin@awayvideos.local",
                password=password,
            )
            return
        # Always keep known password for default admin (reset on deploy)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
    except Exception:
        # DB may not be ready yet during some import paths
        pass


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(ensure_default_admin, sender=self)
