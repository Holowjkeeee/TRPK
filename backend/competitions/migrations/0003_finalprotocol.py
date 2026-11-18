# Generated for iteration 3.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0002_match"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FinalProtocol",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("generated_at", models.DateTimeField(auto_now=True)),
                ("snapshot", models.JSONField(blank=True, default=dict)),
                ("document", models.FileField(blank=True, upload_to="protocols/%Y/%m/%d/")),
                ("competition", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="final_protocol", to="competitions.competition")),
                ("generated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_final_protocols", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-generated_at"]},
        ),
    ]
