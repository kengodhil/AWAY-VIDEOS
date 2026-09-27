from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ensure default studio admin exists (admin / admin123)."

    def handle(self, *args, **options):
        User = get_user_model()
        username = "admin"
        password = "admin123"
        email = "admin@awayvideos.local"

        user = User.objects.filter(username=username).first()
        if user:
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Reset password for {username} / {password} — /studio/login/"
                )
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {username} / {password} — sign in at /studio/login/"
            )
        )
