"""
Create the initial Tab Master account non-interactively.

FIX #10: when a database is recreated from scratch, `migrate` gives you empty
tables and no account to log in with. Login then stops returning 500 and starts
saying "Invalid username or password", which looks like a brand new bug but is
just an empty auth_user table. Render's free tier has no shell, so there is no
way to run `createsuperuser` interactively — hence this command.

Usage (safe to run on every deploy; it never overwrites an existing account):

    python manage.py ensure_superuser

Reads DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL and
DJANGO_SUPERUSER_PASSWORD from the environment. Does nothing if any are missing.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from decouple import config


class Command(BaseCommand):
    help = "Create the initial superuser from environment variables, if absent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Reset the password of an existing account to the env var value.",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        username = config("DJANGO_SUPERUSER_USERNAME", default="")
        email = config("DJANGO_SUPERUSER_EMAIL", default="")
        password = config("DJANGO_SUPERUSER_PASSWORD", default="")

        if not (username and password):
            self.stdout.write(
                "DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_PASSWORD not set — "
                "skipping superuser creation."
            )
            return

        existing = User.objects.filter(username=username).first()

        if existing:
            if options["reset_password"]:
                existing.set_password(password)
                existing.is_staff = True
                existing.is_superuser = True
                existing.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Password reset for existing user '{username}'.")
                )
            else:
                self.stdout.write(f"Superuser '{username}' already exists — nothing to do.")
            return

        User.objects.create_superuser(
            username=username,
            email=email or None,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))
