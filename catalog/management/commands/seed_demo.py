from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the default AWAY Videos studio admin account."

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(username="admin").exists():
            self.stdout.write("Admin already exists.")
            return
        User.objects.create_superuser(
            username="admin",
            email="admin@awayvideos.local",
            password="admin123",
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Created admin / admin123 — sign in at /studio/login/"
            )
        )
