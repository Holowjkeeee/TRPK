from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from competitions.models import UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Создаёт демонстрационного администратора, если его ещё нет"

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username="admin")
        if created:
            user.set_password("admin123")
        user.is_staff = True
        user.is_superuser = True
        user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.Role.ORGANIZER
        profile.save()
        self.stdout.write(self.style.SUCCESS("Демо-доступ: admin / admin123"))
