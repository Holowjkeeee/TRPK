# Generated for iteration 4.
from django.db import migrations, models
import django.db.models.deletion


def backfill_team_memberships(apps, schema_editor):
    Participation = apps.get_model('competitions', 'Participation')
    TeamMembership = apps.get_model('competitions', 'TeamMembership')

    last_team_by_athlete = {}
    participations = Participation.objects.exclude(team_id__isnull=True).order_by('athlete_id', 'created_at', 'id')
    for participation in participations.iterator():
        TeamMembership.objects.get_or_create(
            athlete_id=participation.athlete_id,
            team_id=participation.team_id,
            defaults={'is_current': False},
        )
        last_team_by_athlete[participation.athlete_id] = participation.team_id

    for athlete_id, team_id in last_team_by_athlete.items():
        TeamMembership.objects.filter(athlete_id=athlete_id).update(is_current=False)
        TeamMembership.objects.filter(athlete_id=athlete_id, team_id=team_id).update(is_current=True)


class Migration(migrations.Migration):
    dependencies = [('competitions', '0003_finalprotocol')]

    operations = [
        migrations.CreateModel(
            name='TeamMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_current', models.BooleanField(default=True)),
                ('first_seen_at', models.DateTimeField(auto_now_add=True)),
                ('last_seen_at', models.DateTimeField(auto_now=True)),
                ('athlete', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_memberships', to='competitions.athlete')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='athlete_memberships', to='competitions.team')),
            ],
            options={'ordering': ['team__name', 'athlete__last_name', 'athlete__first_name']},
        ),
        migrations.AddConstraint(
            model_name='teammembership',
            constraint=models.UniqueConstraint(fields=('athlete', 'team'), name='uq_athlete_team_membership'),
        ),
        migrations.RunPython(backfill_team_memberships, migrations.RunPython.noop),
    ]
