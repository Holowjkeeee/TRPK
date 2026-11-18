from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from competitions.models import UserProfile
from competitions.services.demo_data import generate_test_competitions

User = get_user_model()


class Command(BaseCommand):
    help = "Создаёт демонстрационного администратора и готовые тестовые соревнования"

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(username="admin")
        user.set_password("admin123")
        user.is_staff = True
        user.is_superuser = True
        user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.Role.ORGANIZER
        profile.save()

        competitions = generate_test_competitions(user=user, replace=True)
        self.stdout.write(self.style.SUCCESS("Готово: admin / admin123"))
        for competition in competitions:
            self.stdout.write(self.style.SUCCESS(f"Соревнование ID {competition.id}: {competition.name}"))
