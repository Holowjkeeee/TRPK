from django.db import transaction

from competitions.models import Athlete, Team, TeamMembership


def get_or_create_team(name, city='', coach_name=''):
    clean_name = ' '.join(str(name or '').split()).strip()
    if not clean_name:
        raise ValueError('Не указана команда/клуб')

    team = Team.objects.filter(name__iexact=clean_name).first()
    if team is None:
        team = Team.objects.create(name=clean_name, city=city.strip(), coach_name=coach_name.strip())
        return team

    changed = []
    if city and not team.city:
        team.city = city.strip()
        changed.append('city')
    if coach_name and not team.coach_name:
        team.coach_name = coach_name.strip()
        changed.append('coach_name')
    if changed:
        team.save(update_fields=changed)
    return team


def _base_athlete_query(last_name, first_name, birth_date=None, birth_year=None):
    query = Athlete.objects.filter(last_name__iexact=last_name.strip(), first_name__iexact=first_name.strip())
    if birth_date:
        exact_date = query.filter(birth_date=birth_date)
        if exact_date.exists():
            return exact_date
        # Старые импорты могли содержать только год рождения.
        return query.filter(birth_date__isnull=True, birth_year=birth_date.year)
    if birth_year:
        return query.filter(birth_year=birth_year)
    return query.none()


def _pick_unambiguous(query, middle_name=''):
    if middle_name:
        exact = query.filter(middle_name__iexact=middle_name.strip())
        if exact.count() == 1:
            return exact.first()
        without_middle = query.filter(middle_name='')
        if without_middle.count() == 1:
            return without_middle.first()
        return None
    return query.first() if query.count() == 1 else None


def find_existing_athlete(team, last_name, first_name, middle_name='', birth_date=None, birth_year=None):
    # Сначала ищем человека среди спортсменов той же команды.
    team_query = _base_athlete_query(last_name, first_name, birth_date, birth_year).filter(team_memberships__team=team).distinct()
    athlete = _pick_unambiguous(team_query, middle_name)
    if athlete:
        return athlete

    # Затем ищем глобально. Это позволяет сохранить одного Athlete при смене клуба.
    global_query = _base_athlete_query(last_name, first_name, birth_date, birth_year).distinct()
    return _pick_unambiguous(global_query, middle_name)


@transaction.atomic
def resolve_athlete_for_team(
    team,
    last_name,
    first_name,
    middle_name='',
    birth_date=None,
    birth_year=None,
    gender=Athlete.Gender.UNKNOWN,
):
    athlete = find_existing_athlete(
        team=team,
        last_name=last_name,
        first_name=first_name,
        middle_name=middle_name,
        birth_date=birth_date,
        birth_year=birth_year,
    )
    created = athlete is None
    if created:
        athlete = Athlete.objects.create(
            last_name=last_name.strip(),
            first_name=first_name.strip(),
            middle_name=middle_name.strip(),
            birth_date=birth_date,
            birth_year=birth_year,
            gender=gender,
        )
    else:
        changed = []
        if middle_name and not athlete.middle_name:
            athlete.middle_name = middle_name.strip()
            changed.append('middle_name')
        if birth_date and not athlete.birth_date:
            athlete.birth_date = birth_date
            changed.append('birth_date')
        if birth_year and not athlete.birth_year:
            athlete.birth_year = birth_year
            changed.append('birth_year')
        if athlete.gender == Athlete.Gender.UNKNOWN and gender != Athlete.Gender.UNKNOWN:
            athlete.gender = gender
            changed.append('gender')
        if changed:
            athlete.save(update_fields=changed)

    # Участие хранит команду турнира как снимок, а membership - долговременную историю.
    membership, membership_created = TeamMembership.objects.get_or_create(
        athlete=athlete,
        team=team,
        defaults={'is_current': True},
    )
    if not membership.is_current:
        membership.is_current = True
        membership.save(update_fields=['is_current', 'last_seen_at'])

    # Если спортсмен заявлен за новую команду, старая связь остаётся в истории,
    # но перестаёт считаться текущей.
    TeamMembership.objects.filter(athlete=athlete, is_current=True).exclude(pk=membership.pk).update(is_current=False)
    return athlete, created, membership_created
