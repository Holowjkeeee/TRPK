from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("competitions", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Match",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_index", models.PositiveIntegerField(default=0)),
                ("round_number", models.PositiveIntegerField(default=1)),
                ("stage", models.CharField(choices=[("round_robin", "Круговая встреча"), ("group", "Групповой этап"), ("qualification", "Квалификация"), ("main", "Основная сетка"), ("semifinal", "Полуфинал"), ("final", "Финал"), ("repechage", "Утешительная встреча"), ("bronze", "Встреча за бронзу")], max_length=30)),
                ("stage_label", models.CharField(blank=True, max_length=100)),
                ("group_label", models.CharField(blank=True, max_length=10)),
                ("branch_label", models.CharField(blank=True, max_length=10)),
                ("red_score", models.PositiveIntegerField(blank=True, null=True)),
                ("blue_score", models.PositiveIntegerField(blank=True, null=True)),
                ("red_classification_points", models.PositiveSmallIntegerField(default=0)),
                ("blue_classification_points", models.PositiveSmallIntegerField(default=0)),
                ("victory_method", models.CharField(blank=True, choices=[("points", "По баллам"), ("technical_superiority", "Техническое превосходство"), ("fall", "Туше"), ("no_show", "Неявка"), ("medical_forfeit", "Медицинское снятие"), ("disqualification", "Дисквалификация")], max_length=40)),
                ("status", models.CharField(choices=[("pending", "Ожидает участников"), ("ready", "Готов к проведению"), ("finished", "Завершён")], default="pending", max_length=20)),
                ("next_slot", models.CharField(blank=True, choices=[("red", "Красный"), ("blue", "Синий")], max_length=10)),
                ("loser_next_slot", models.CharField(blank=True, choices=[("red", "Красный"), ("blue", "Синий")], max_length=10)),
                ("mat_number", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("scheduled_order", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("blue", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="matches_blue", to="competitions.participation")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="matches", to="competitions.category")),
                ("competition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="matches", to="competitions.competition")),
                ("loser_next_match", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="loser_sources", to="competitions.match")),
                ("next_match", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="winner_sources", to="competitions.match")),
                ("red", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="matches_red", to="competitions.participation")),
                ("winner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="won_matches", to="competitions.participation")),
            ],
            options={"ordering": ["category_id", "order_index", "id"]},
        ),
        migrations.AddIndex(
            model_name="match",
            index=models.Index(fields=["competition", "category", "status"], name="match_comp_cat_status_idx"),
        ),
        migrations.AddIndex(
            model_name="match",
            index=models.Index(fields=["category", "stage", "round_number"], name="match_cat_stage_round_idx"),
        ),
    ]
