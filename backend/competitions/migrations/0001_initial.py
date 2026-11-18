# Initial schema for TRPK Django/Vue v2.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Athlete",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_name", models.CharField(max_length=100)),
                ("first_name", models.CharField(max_length=100)),
                ("middle_name", models.CharField(blank=True, max_length=100)),
                ("birth_date", models.DateField(blank=True, null=True)),
                ("birth_year", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("gender", models.CharField(choices=[("male", "Мужской"), ("female", "Женский"), ("unknown", "Не указан")], default="unknown", max_length=20)),
            ],
            options={"ordering": ["last_name", "first_name", "middle_name"]},
        ),
        migrations.CreateModel(
            name="Team",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("city", models.CharField(blank=True, max_length=150)),
                ("coach_name", models.CharField(blank=True, max_length=255)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Competition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("date", models.DateField()),
                ("venue", models.CharField(max_length=255)),
                ("registration_deadline", models.DateTimeField(blank=True, null=True)),
                ("mat_count", models.PositiveSmallIntegerField(default=2)),
                ("status", models.CharField(choices=[("draft", "Подготовка"), ("registration", "Приём заявок"), ("weigh_in", "Взвешивание"), ("running", "Проводится"), ("finished", "Завершено")], default="draft", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_competitions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-date", "-id"]},
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("organizer", "Организатор"), ("chief_judge", "Главный судья"), ("chief_secretary", "Главный секретарь"), ("timekeeper", "Секундометрист / оператор")], default="organizer", max_length=30)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("age_group", models.CharField(max_length=120)),
                ("birth_year_from", models.PositiveSmallIntegerField()),
                ("birth_year_to", models.PositiveSmallIntegerField()),
                ("weight_limit", models.DecimalField(decimal_places=2, max_digits=6)),
                ("gender", models.CharField(choices=[("male", "Мужской"), ("female", "Женский"), ("unknown", "Не указан")], default="male", max_length=20)),
                ("system_type", models.CharField(blank=True, choices=[("round_robin", "Круговая"), ("nordic", "Нордическая"), ("elimination", "Прямое выбывание")], max_length=30)),
                ("status", models.CharField(choices=[("draft", "Черновик"), ("ready", "Готова"), ("running", "Проводится"), ("finished", "Завершена")], default="draft", max_length=30)),
                ("competition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="categories", to="competitions.competition")),
            ],
            options={"ordering": ["birth_year_from", "weight_limit", "name"]},
        ),
        migrations.CreateModel(
            name="Application",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_file", models.FileField(upload_to="applications/%Y/%m/%d/")),
                ("original_name", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("imported", "Импортирована"), ("needs_review", "Требует уточнения"), ("failed", "Ошибка импорта")], default="imported", max_length=30)),
                ("imported_rows", models.PositiveIntegerField(default=0)),
                ("duplicate_rows", models.PositiveIntegerField(default=0)),
                ("error_rows", models.PositiveIntegerField(default=0)),
                ("errors", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("competition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="applications", to="competitions.competition")),
                ("imported_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="imported_applications", to=settings.AUTH_USER_MODEL)),
                ("team", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="applications", to="competitions.team")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Participation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("declared_category_label", models.CharField(blank=True, max_length=100)),
                ("weigh_in_status", models.CharField(choices=[("pending", "Не проверено"), ("matched", "Соответствует заявленной категории"), ("transfer_required", "Требуется перенос"), ("transferred", "Перенесён в другую категорию"), ("rejected", "Не допущен по результату взвешивания")], default="pending", max_length=30)),
                ("weigh_in_comment", models.CharField(blank=True, max_length=255)),
                ("medical_clearance", models.BooleanField(default=False)),
                ("insurance_checked", models.BooleanField(default=False)),
                ("documents_checked", models.BooleanField(default=False)),
                ("admission_status", models.CharField(choices=[("pending", "Ожидает проверки"), ("admitted", "Допущен"), ("rejected", "Не допущен")], default="pending", max_length=30)),
                ("admission_reason", models.CharField(blank=True, max_length=255)),
                ("review_status", models.CharField(choices=[("ok", "Данные приняты"), ("needs_review", "Требует уточнения")], default="ok", max_length=30)),
                ("draw_number", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("application", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="participations", to="competitions.application")),
                ("athlete", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="participations", to="competitions.athlete")),
                ("competition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="participations", to="competitions.competition")),
                ("confirmed_category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="confirmed_participations", to="competitions.category")),
                ("declared_category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="declared_participations", to="competitions.category")),
                ("team", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="participations", to="competitions.team")),
            ],
            options={"ordering": ["athlete__last_name", "athlete__first_name"]},
        ),
        migrations.AddIndex(model_name="athlete", index=models.Index(fields=["last_name", "first_name", "birth_year"], name="competitions_last_na_87537e_idx")),
        migrations.AddConstraint(model_name="category", constraint=models.UniqueConstraint(fields=("competition", "birth_year_from", "birth_year_to", "weight_limit", "gender"), name="uq_category_per_competition")),
        migrations.AddConstraint(model_name="participation", constraint=models.UniqueConstraint(fields=("competition", "athlete"), name="uq_athlete_competition")),
    ]
