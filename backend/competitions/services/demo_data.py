from datetime import date, timedelta

from django.db import transaction

from competitions.models import Athlete, Category, Competition, Participation, Team, TeamMembership
from competitions.services.brackets import assign_mats, generate_bracket, simulate_category

TEST_PREFIX = "[ТЕСТ]"

FIRST_NAMES = [
    ("Иванов", "Иван", "Алексеевич", "male"), ("Петров", "Пётр", "Сергеевич", "male"),
    ("Сидоров", "Алексей", "Игоревич", "male"), ("Смирнов", "Максим", "Олегович", "male"),
    ("Кузнецов", "Даниил", "Андреевич", "male"), ("Попов", "Артём", "Романович", "male"),
    ("Васильев", "Егор", "Дмитриевич", "male"), ("Соколов", "Кирилл", "Владимирович", "male"),
    ("Михайлов", "Роман", "Евгеньевич", "male"), ("Новиков", "Илья", "Павлович", "male"),
    ("Фёдоров", "Никита", "Максимович", "male"), ("Морозов", "Матвей", "Денисович", "male"),
    ("Волков", "Андрей", "Михайлович", "male"), ("Алексеев", "Степан", "Антонович", "male"),
    ("Лебедев", "Михаил", "Иванович", "male"), ("Семёнов", "Дмитрий", "Александрович", "male"),
    ("Егоров", "Владислав", "Сергеевич", "male"), ("Павлов", "Глеб", "Андреевич", "male"),
    ("Козлов", "Тимофей", "Олегович", "male"), ("Степанов", "Ярослав", "Игоревич", "male"),
    ("Николаев", "Арсений", "Петрович", "male"), ("Орлов", "Савелий", "Романович", "male"),
    ("Андреев", "Марк", "Дмитриевич", "male"), ("Макаров", "Лев", "Владимирович", "male"),
    ("Захаров", "Константин", "Евгеньевич", "male"), ("Зайцев", "Денис", "Павлович", "male"),
    ("Белов", "Виктор", "Максимович", "male"), ("Комаров", "Олег", "Денисович", "male"),
    ("Гусев", "Сергей", "Михайлович", "male"), ("Титов", "Антон", "Иванович", "male"),
]

TEAM_DATA = [
    ("Богатырь", "Иркутск", "Георгий Андреевич"),
    ("Сокол", "Шелехов", "Александр Сергеевич"),
    ("Ермак", "Ангарск", "Михаил Олегович"),
    ("Олимп", "Иркутск", "Владимир Игоревич"),
    ("Байкал", "Иркутск", "Сергей Павлович"),
    ("Спарта", "Усолье-Сибирское", "Андрей Викторович"),
    ("Ангара", "Ангарск", "Дмитрий Романович"),
    ("Витязь", "Шелехов", "Евгений Алексеевич"),
]
TEAM_NAMES = [name for name, _city, _coach in TEAM_DATA]

# Это демонстрационный, а не нормативный набор. Он нужен, чтобы интерфейс
# выглядел как реальное соревнование с большим числом весов.
DEMO_WEIGHT_LIMITS = (32, 35, 38, 41, 44, 48, 52, 57, 62, 68, 75, 85, 92, 100, 110)


def _category(competition, weight, years=(2012, 2013)):
    category, _ = Category.objects.get_or_create(
        competition=competition,
        birth_year_from=years[0],
        birth_year_to=years[1],
        weight_limit=weight,
        gender="male",
        defaults={
            "name": f"Юноши {years[0]}-{years[1]}, до {weight} кг",
            "age_group": f"Юноши {years[0]}-{years[1]}",
        },
    )
    return category


def _category_set(competition, weights=DEMO_WEIGHT_LIMITS, years=(2012, 2013)):
    categories = {weight: _category(competition, weight, years=years) for weight in weights}
    assign_mats(competition)
    return categories


def _athlete(index, year=2012):
    last_name, first_name, middle_name, gender = FIRST_NAMES[index % len(FIRST_NAMES)]
    athlete, _ = Athlete.objects.get_or_create(
        last_name=last_name,
        first_name=first_name,
        birth_year=year,
        defaults={"middle_name": middle_name, "gender": gender},
    )
    return athlete


def _participation(competition, athlete, team, declared_category, weigh_status, confirmed_category=None, docs=True, review="ok", comment=""):
    membership, _ = TeamMembership.objects.get_or_create(athlete=athlete, team=team, defaults={"is_current": True})
    if not membership.is_current:
        membership.is_current = True
        membership.save(update_fields=["is_current", "last_seen_at"])
    TeamMembership.objects.filter(athlete=athlete, is_current=True).exclude(pk=membership.pk).update(is_current=False)

    participation = Participation.objects.create(
        competition=competition,
        athlete=athlete,
        team=team,
        declared_category=declared_category,
        declared_category_label=f"{str(declared_category.weight_limit).rstrip('0').rstrip('.')} кг",
        confirmed_category=confirmed_category,
        weigh_in_status=weigh_status,
        weigh_in_comment=comment,
        documents_checked=docs,
        medical_clearance=docs,
        insurance_checked=docs,
        review_status=review,
    )
    if docs and confirmed_category and weigh_status in {Participation.WeighInStatus.MATCHED, Participation.WeighInStatus.TRANSFERRED}:
        participation.admission_status = Participation.AdmissionStatus.ADMITTED
    elif weigh_status == Participation.WeighInStatus.REJECTED:
        participation.admission_status = Participation.AdmissionStatus.REJECTED
        participation.admission_reason = comment or "Не допущен по результату взвешивания"
    participation.save()
    return participation


@transaction.atomic
def generate_test_competitions(user=None, replace=True):
    if replace:
        Competition.objects.filter(name__startswith=TEST_PREFIX).delete()

    teams = []
    for name, city, coach_name in TEAM_DATA:
        team, _ = Team.objects.get_or_create(name=name, defaults={"city": city, "coach_name": coach_name})
        teams.append(team)

    today = date.today()

    prep = Competition.objects.create(
        name=f"{TEST_PREFIX} Подготовка и взвешивание",
        date=today + timedelta(days=7),
        venue="СК Богатырь",
        mat_count=2,
        status=Competition.Status.WEIGH_IN,
        created_by=user,
    )
    prep_map = _category_set(prep)
    prep_categories = [prep_map[w] for w in (38, 44, 52, 57, 62, 68)]
    statuses = [
        (Participation.WeighInStatus.PENDING, None, False, ""),
        (Participation.WeighInStatus.MATCHED, prep_categories[1], True, ""),
        (Participation.WeighInStatus.TRANSFER_REQUIRED, None, True, "Весовая категория требует уточнения"),
        (Participation.WeighInStatus.TRANSFERRED, prep_categories[3], True, "Перенос согласован"),
        (Participation.WeighInStatus.REJECTED, None, True, "Решение судейской коллегии"),
        (Participation.WeighInStatus.MATCHED, prep_categories[4], False, "Ожидается проверка документов"),
    ]
    for i, (status, confirmed, docs, comment) in enumerate(statuses):
        declared = prep_categories[min(i, len(prep_categories) - 1)]
        if status == Participation.WeighInStatus.TRANSFERRED:
            declared = prep_categories[2]
        _participation(prep, _athlete(i), teams[i % len(teams)], declared, status, confirmed, docs=docs, comment=comment)

    grids = Competition.objects.create(
        name=f"{TEST_PREFIX} Наборы для сеток 5 / 7 / 10",
        date=today + timedelta(days=14),
        venue="Дворец спорта Труд",
        mat_count=2,
        status=Competition.Status.RUNNING,
        created_by=user,
    )
    grid_map_young = _category_set(grids, years=(2012, 2013))
    grid_map_old = _category_set(grids, years=(2010, 2011))
    grid_specs = [
        (grid_map_young[52], 5, 2012),
        (grid_map_old[57], 7, 2010),
        (grid_map_old[62], 10, 2010),
    ]
    athlete_index = 6
    grid_categories = []
    for category, count, birth_year in grid_specs:
        grid_categories.append(category)
        for offset in range(count):
            athlete = _athlete(athlete_index, year=birth_year)
            athlete_index += 1
            _participation(grids, athlete, teams[offset % len(teams)], category, Participation.WeighInStatus.MATCHED, category, docs=True)

    # В тестовом соревновании сетки создаются сразу, чтобы второй этап можно было
    # проверять без ручной жеребьёвки каждого набора. Порядок детерминированный.
    for category in grid_categories:
        generate_bracket(category, shuffle=False)

    blank = Competition.objects.create(
        name=f"{TEST_PREFIX} Пустое для импорта Word",
        date=today + timedelta(days=21),
        venue="Учебный спортивный зал",
        mat_count=2,
        status=Competition.Status.REGISTRATION,
        created_by=user,
    )
    _category_set(blank)

    protocol_demo = Competition.objects.create(
        name=f"{TEST_PREFIX} Завершённое для итогового протокола",
        date=today - timedelta(days=1),
        venue="СК Богатырь",
        mat_count=2,
        status=Competition.Status.RUNNING,
        created_by=user,
    )
    protocol_map_young = _category_set(protocol_demo, years=(2012, 2013))
    protocol_map_old = _category_set(protocol_demo, years=(2010, 2011))
    protocol_specs = [
        (protocol_map_young[52], 5, 2012),
        (protocol_map_old[57], 7, 2010),
        (protocol_map_old[62], 10, 2010),
    ]
    athlete_index = 0
    protocol_categories = []
    for category, count, birth_year in protocol_specs:
        protocol_categories.append(category)
        for offset in range(count):
            athlete = _athlete(athlete_index, year=birth_year)
            athlete_index += 1
            _participation(
                protocol_demo, athlete, teams[offset % len(teams)], category,
                Participation.WeighInStatus.MATCHED, category, docs=True,
            )
    for category in protocol_categories:
        generate_bracket(category, shuffle=False)
        simulate_category(category)
    protocol_demo.status = Competition.Status.FINISHED
    protocol_demo.save(update_fields=["status"])

    return [prep, grids, blank, protocol_demo]
