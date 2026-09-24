from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Make Thiru a Django superuser"

    def handle(self, *args, **kwargs):

        username = "Thiru"

        user = User.objects.get(username=username)

        user.is_staff = True
        user.is_superuser = True
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"{username} is now a superuser."
            )
        )