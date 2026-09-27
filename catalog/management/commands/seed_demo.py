from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Create a demo admin account if it does not exist."

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(username="admin").exists():
            self.stdout.write("Admin already exists.")
            return
        User.objects.create_superuser(
            username="admin",
            email="admin@adureel.local",
            password="admin123",
            first_name="Adu Admin",
            phone="255700000000",
        )
        self.stdout.write(self.style.SUCCESS("Created admin / admin123"))
