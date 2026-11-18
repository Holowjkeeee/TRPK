from django.db import migrations, models


def assign_existing_category_mats(apps, schema_editor):
    Competition = apps.get_model("competitions", "Competition")
    Category = apps.get_model("competitions", "Category")
    Match = apps.get_model("competitions", "Match")

    for competition in Competition.objects.all():
        mat_count = max(1, competition.mat_count or 1)
        categories = list(
            Category.objects.filter(competition=competition)
            .order_by("-birth_year_to", "-birth_year_from", "gender", "weight_limit", "id")
        )
        if not categories:
            continue

        age_groups = []
        seen = set()
        for category in categories:
            key = (category.birth_year_from, category.birth_year_to, category.gender, category.age_group)
            if key not in seen:
                seen.add(key)
                age_groups.append(key)

        group_count = len(age_groups)
        group_to_mat = {}
        for index, key in enumerate(age_groups):
            mat_number = min(mat_count, (index * mat_count) // group_count + 1)
            group_to_mat[key] = mat_number

        counters = {number: 0 for number in range(1, mat_count + 1)}
        for category in categories:
            key = (category.birth_year_from, category.birth_year_to, category.gender, category.age_group)
            category.mat_number = group_to_mat[key]
            category.save(update_fields=["mat_number"])

            for match in Match.objects.filter(category=category).order_by("round_number", "order_index", "id"):
                counters[category.mat_number] += 1
                match.mat_number = category.mat_number
                match.scheduled_order = counters[category.mat_number]
                match.save(update_fields=["mat_number", "scheduled_order"])


class Migration(migrations.Migration):
    dependencies = [("competitions", "0004_teammembership")]

    operations = [
        migrations.AddField(
            model_name="category",
            name="mat_number",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(assign_existing_category_mats, migrations.RunPython.noop),
    ]
