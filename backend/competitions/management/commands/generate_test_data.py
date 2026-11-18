from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from competitions.services.demo_data import generate_test_competitions

User = get_user_model()


class Command(BaseCommand):
    help = "Создаёт набор тестовых соревнований для демонстрации и разработки"

    def add_arguments(self, parser):
        parser.add_argument("--keep", action="store_true", help="Не удалять ранее созданные [ТЕСТ] соревнования")

    def handle(self, *args, **options):
        user = User.objects.filter(username="admin").first() or User.objects.filter(is_superuser=True).first()
        competitions = generate_test_competitions(user=user, replace=not options["keep"])
        self.stdout.write(self.style.SUCCESS("Созданы тестовые соревнования:"))
        for competition in competitions:
            self.stdout.write(f"  ID {competition.id}: {competition.name}")
