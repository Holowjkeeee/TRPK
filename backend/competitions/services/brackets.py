import math
import random
from collections import defaultdict

from django.db import transaction

from competitions.models import Category, Match, Participation


SYSTEM_LABELS = {
    Category.SystemType.ROUND_ROBIN: "Круговая",
    Category.SystemType.NORDIC: "Нордическая",
    Category.SystemType.ELIMINATION: "Прямое выбывание",
}


def select_system(participant_count: int) -> str:
    if participant_count < 2:
        raise ValueError("Для формирования сетки требуется минимум 2 допущенных спортсмена")
    if participant_count <= 5:
        return Category.SystemType.ROUND_ROBIN
    if participant_count <= 7:
        return Category.SystemType.NORDIC
    return Category.SystemType.ELIMINATION


def _admitted(category: Category):
    return list(
        Participation.objects.select_related("athlete", "team")
        .filter(
            competition=category.competition,
            confirmed_category=category,
            admission_status=Participation.AdmissionStatus.ADMITTED,
        )
        .order_by("athlete__last_name", "athlete__first_name", "id")
    )


def _assign_draw_numbers(participants, shuffle=True):
    items = list(participants)
    if shuffle:
        random.shuffle(items)
    for index, participation in enumerate(items, start=1):
        if participation.draw_number != index:
            participation.draw_number = index
            participation.save(update_fields=["draw_number"])
    return items


def _circle_rounds(participants):
    """Возвращает раунды круговой системы без матчей с фиктивным участником."""
    players = list(participants)
    if len(players) % 2:
        players.append(None)
    n = len(players)
    if n < 2:
        return []
    rounds = []
    current = players[:]
    for _ in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a = current[i]
            b = current[n - 1 - i]
            if a is not None and b is not None:
                pairs.append((a, b))
        rounds.append(pairs)
        current = [current[0], current[-1], *current[1:-1]]
    return rounds


def _make_match(category, order_index, round_number, stage, label, red=None, blue=None, **extra):
    match = Match.objects.create(
        competition=category.competition,
        category=category,
        order_index=order_index,
        round_number=round_number,
        stage=stage,
        stage_label=label,
        red=red,
        blue=blue,
        **extra,
    )
    match.refresh_status()
    match.save(update_fields=["status"])
    return match


def _stage_label_for_main_round(bracket_size, round_index):
    participants_in_round = bracket_size // (2 ** (round_index - 1))
    if participants_in_round == 2:
        return "Финал"
    if participants_in_round == 4:
        return "Полуфинал"
    if participants_in_round == 8:
        return "1/4 финала"
    if participants_in_round == 16:
        return "1/8 финала"
    if participants_in_round == 32:
        return "1/16 финала"
    return f"Раунд на {participants_in_round}"


def _stage_type_for_main_round(bracket_size, round_index):
    participants_in_round = bracket_size // (2 ** (round_index - 1))
    if participants_in_round == 2:
        return Match.Stage.FINAL
    if participants_in_round == 4:
        return Match.Stage.SEMIFINAL
    return Match.Stage.MAIN


@transaction.atomic
def generate_bracket(category: Category, shuffle=True):
    existing = category.matches.all()
    if existing.filter(status=Match.Status.FINISHED).exists():
        raise ValueError("Нельзя перестроить сетку: в категории уже есть завершённые поединки")
    existing.delete()

    participants = _admitted(category)
    system_type = select_system(len(participants))
    category.system_type = system_type
    category.status = Category.Status.READY
    category.save(update_fields=["system_type", "status"])
    participants = _assign_draw_numbers(participants, shuffle=shuffle)

    if system_type == Category.SystemType.ROUND_ROBIN:
        _generate_round_robin(category, participants)
    elif system_type == Category.SystemType.NORDIC:
        _generate_nordic(category, participants)
    else:
        _generate_elimination(category, participants)

    assign_mats(category.competition)
    return category


def _generate_round_robin(category, participants):
    order = 1
    for round_number, pairs in enumerate(_circle_rounds(participants), start=1):
        for red, blue in pairs:
            _make_match(
                category, order, round_number, Match.Stage.ROUND_ROBIN,
                f"Круг {round_number}", red=red, blue=blue,
            )
            order += 1


def _generate_nordic(category, participants):
    split = (len(participants) + 1) // 2
    group_a = participants[:split]
    group_b = participants[split:]
    order = 1
    max_group_round = 0
    for group_label, group in (("A", group_a), ("B", group_b)):
        rounds = _circle_rounds(group)
        max_group_round = max(max_group_round, len(rounds))
        for round_number, pairs in enumerate(rounds, start=1):
            for red, blue in pairs:
                _make_match(
                    category, order, round_number, Match.Stage.GROUP,
                    f"Группа {group_label} · тур {round_number}", red=red, blue=blue,
                    group_label=group_label,
                )
                order += 1

    semifinal_round = max_group_round + 1
    semi1 = _make_match(category, order, semifinal_round, Match.Stage.SEMIFINAL, "Полуфинал 1")
    order += 1
    semi2 = _make_match(category, order, semifinal_round, Match.Stage.SEMIFINAL, "Полуфинал 2")
    order += 1
    final = _make_match(category, order, semifinal_round + 1, Match.Stage.FINAL, "Финал")
    bronze = _make_match(category, order + 1, semifinal_round + 1, Match.Stage.BRONZE, "Матч за 3 место", branch_label="N")

    semi1.next_match = final
    semi1.next_slot = Match.Slot.RED
    semi1.loser_next_match = bronze
    semi1.loser_next_slot = Match.Slot.RED
    semi1.save(update_fields=["next_match", "next_slot", "loser_next_match", "loser_next_slot"])

    semi2.next_match = final
    semi2.next_slot = Match.Slot.BLUE
    semi2.loser_next_match = bronze
    semi2.loser_next_slot = Match.Slot.BLUE
    semi2.save(update_fields=["next_match", "next_slot", "loser_next_match", "loser_next_slot"])


def _largest_power_of_two_leq(n):
    return 2 ** int(math.floor(math.log2(n)))


def _generate_elimination(category, participants):
    n = len(participants)
    bracket_size = _largest_power_of_two_leq(n)
    qualification_count = n - bracket_size
    qualification_players = participants[: qualification_count * 2]
    direct_players = participants[qualification_count * 2 :]

    order = 1
    qualifiers = []
    for index in range(qualification_count):
        red = qualification_players[index * 2]
        blue = qualification_players[index * 2 + 1]
        match = _make_match(
            category, order, 0, Match.Stage.QUALIFICATION,
            "Квалификация", red=red, blue=blue,
        )
        qualifiers.append(match)
        order += 1

    first_round_count = bracket_size // 2
    total_rounds = int(math.log2(bracket_size))
    rounds = []
    previous_round = None

    for round_index in range(1, total_rounds + 1):
        count = bracket_size // (2 ** round_index)
        label = _stage_label_for_main_round(bracket_size, round_index)
        stage = _stage_type_for_main_round(bracket_size, round_index)
        current = []
        for _ in range(count):
            match = _make_match(category, order, round_index, stage, label)
            current.append(match)
            order += 1
        rounds.append(current)

        if previous_round is not None:
            for source_index, source in enumerate(previous_round):
                target = current[source_index // 2]
                source.next_match = target
                source.next_slot = Match.Slot.RED if source_index % 2 == 0 else Match.Slot.BLUE
                source.save(update_fields=["next_match", "next_slot"])
        previous_round = current

    first_round = rounds[0]
    sources = []
    direct_iter = iter(direct_players)
    for qualifier in qualifiers:
        sources.append(("qualifier", qualifier))
        try:
            sources.append(("participant", next(direct_iter)))
        except StopIteration:
            pass
    sources.extend(("participant", p) for p in direct_iter)
    if len(sources) != bracket_size:
        raise ValueError("Внутренняя ошибка формирования основной сетки")

    for slot_index, source in enumerate(sources):
        target = first_round[slot_index // 2]
        slot = Match.Slot.RED if slot_index % 2 == 0 else Match.Slot.BLUE
        kind, value = source
        if kind == "participant":
            if slot == Match.Slot.RED:
                target.red = value
            else:
                target.blue = value
            target.refresh_status()
            target.save(update_fields=["red", "blue", "status"])
        else:
            value.next_match = target
            value.next_slot = slot
            value.save(update_fields=["next_match", "next_slot"])



def _classification_points(match, winner, victory_method, red_score, blue_score):
    loser = match.blue if match.red_id == winner.id else match.red
    winner_score = red_score if match.red_id == winner.id else blue_score
    loser_score = blue_score if match.red_id == winner.id else red_score
    method = victory_method

    if method in {Match.VictoryMethod.FALL, Match.VictoryMethod.NO_SHOW, Match.VictoryMethod.MEDICAL_FORFEIT, Match.VictoryMethod.DISQUALIFICATION}:
        return 5, 0
    if method == Match.VictoryMethod.TECHNICAL_SUPERIORITY:
        return 4, 0 if not loser_score else 1
    if method == Match.VictoryMethod.POINTS:
        return 3, 0 if not loser_score else 1
    return 3, 0


def _place_in_slot(match, slot, participant):
    if not match or not participant:
        return
    if slot == Match.Slot.RED:
        match.red = participant
    elif slot == Match.Slot.BLUE:
        match.blue = participant
    else:
        return
    match.refresh_status()
    match.save(update_fields=["red", "blue", "status"])


def _maybe_seed_nordic_semifinals(category):
    if category.system_type != Category.SystemType.NORDIC:
        return
    group_matches = category.matches.filter(stage=Match.Stage.GROUP)
    if not group_matches.exists() or group_matches.exclude(status=Match.Status.FINISHED).exists():
        return
    semifinals = list(category.matches.filter(stage=Match.Stage.SEMIFINAL).order_by("order_index"))
    if len(semifinals) != 2 or any(m.red_id or m.blue_id for m in semifinals):
        return

    standings_a = category_standings(category, group_label="A")
    standings_b = category_standings(category, group_label="B")
    if len(standings_a) < 2 or len(standings_b) < 2:
        return

    a1 = Participation.objects.get(id=standings_a[0]["participation_id"])
    a2 = Participation.objects.get(id=standings_a[1]["participation_id"])
    b1 = Participation.objects.get(id=standings_b[0]["participation_id"])
    b2 = Participation.objects.get(id=standings_b[1]["participation_id"])

    semifinals[0].red = a1
    semifinals[0].blue = b2
    semifinals[0].refresh_status()
    semifinals[0].save(update_fields=["red", "blue", "status"])

    semifinals[1].red = b1
    semifinals[1].blue = a2
    semifinals[1].refresh_status()
    semifinals[1].save(update_fields=["red", "blue", "status"])


def _direct_losers_to(participant, category):
    result = []
    relevant = category.matches.filter(
        winner=participant,
        status=Match.Status.FINISHED,
        stage__in=[Match.Stage.QUALIFICATION, Match.Stage.MAIN, Match.Stage.SEMIFINAL],
    ).order_by("round_number", "order_index")
    for match in relevant:
        loser = match.loser
        if loser:
            result.append(loser)
    return result


def _build_repechage_branch(category, finalist, branch, start_order):
    if category.matches.filter(stage__in=[Match.Stage.REPECHAGE, Match.Stage.BRONZE], branch_label=branch).exists():
        return start_order
    losers = _direct_losers_to(finalist, category)
    if len(losers) < 2:
        return start_order

    if len(losers) == 2:
        _make_match(
            category, start_order, 100, Match.Stage.BRONZE,
            f"Бронза {branch}", red=losers[0], blue=losers[1], branch_label=branch,
        )
        return start_order + 1

    previous = None
    for index in range(len(losers) - 1):
        is_last = index == len(losers) - 2
        stage = Match.Stage.BRONZE if is_last else Match.Stage.REPECHAGE
        label = f"Бронза {branch}" if is_last else f"Утешительная {branch} · {index + 1}"
        if index == 0:
            red = losers[0]
            blue = losers[1]
        else:
            red = None
            blue = losers[index + 1]
        match = _make_match(
            category, start_order, 90 + index, stage, label,
            red=red, blue=blue, branch_label=branch,
        )
        start_order += 1
        if previous:
            previous.next_match = match
            previous.next_slot = Match.Slot.RED
            previous.save(update_fields=["next_match", "next_slot"])
        previous = match
    return start_order


def _maybe_build_elimination_repechage(category):
    if category.system_type != Category.SystemType.ELIMINATION:
        return
    semifinals = category.matches.filter(stage=Match.Stage.SEMIFINAL).order_by("order_index")
    if semifinals.count() != 2 or semifinals.exclude(status=Match.Status.FINISHED).exists():
        return
    final = category.matches.filter(stage=Match.Stage.FINAL).first()
    if not final or not final.red_id or not final.blue_id:
        return
    start_order = (category.matches.order_by("-order_index").values_list("order_index", flat=True).first() or 0) + 1
    start_order = _build_repechage_branch(category, final.red, "A", start_order)
    _build_repechage_branch(category, final.blue, "B", start_order)


def _maybe_finish_category(category):
    matches = category.matches.all()
    if not matches.exists() or matches.exclude(status=Match.Status.FINISHED).exists():
        return
    category.status = Category.Status.FINISHED
    category.save(update_fields=["status"])


@transaction.atomic
def record_result(match: Match, winner_id: int, red_score: int, blue_score: int, victory_method: str):
    match = Match.objects.select_related("category", "red", "blue", "next_match", "loser_next_match").get(id=match.id)
    if match.status == Match.Status.FINISHED:
        raise ValueError("Результат этого поединка уже зафиксирован")
    if not match.red_id or not match.blue_id:
        raise ValueError("У поединка ещё не определены оба участника")
    if winner_id not in {match.red_id, match.blue_id}:
        raise ValueError("Победитель должен быть участником этого поединка")
    if victory_method not in Match.VictoryMethod.values:
        raise ValueError("Неизвестный способ победы")
    if red_score < 0 or blue_score < 0:
        raise ValueError("Баллы не могут быть отрицательными")

    winner = match.red if winner_id == match.red_id else match.blue
    loser = match.blue if winner_id == match.red_id else match.red
    winner_cp, loser_cp = _classification_points(match, winner, victory_method, red_score, blue_score)

    match.red_score = red_score
    match.blue_score = blue_score
    match.winner = winner
    match.victory_method = victory_method
    match.status = Match.Status.FINISHED
    if winner_id == match.red_id:
        match.red_classification_points = winner_cp
        match.blue_classification_points = loser_cp
    else:
        match.red_classification_points = loser_cp
        match.blue_classification_points = winner_cp
    match.save()

    if match.next_match_id:
        _place_in_slot(match.next_match, match.next_slot, winner)
    if match.loser_next_match_id:
        _place_in_slot(match.loser_next_match, match.loser_next_slot, loser)

    category = match.category
    if category.status == Category.Status.READY:
        category.status = Category.Status.RUNNING
        category.save(update_fields=["status"])
    _maybe_seed_nordic_semifinals(category)
    _maybe_build_elimination_repechage(category)
    assign_mats(category.competition)
    _maybe_finish_category(category)
    return match


def category_standings(category: Category, group_label=None):
    participants = _admitted(category)
    if group_label:
        participant_ids = set()
        for m in category.matches.filter(stage=Match.Stage.GROUP, group_label=group_label):
            if m.red_id:
                participant_ids.add(m.red_id)
            if m.blue_id:
                participant_ids.add(m.blue_id)
        participants = [p for p in participants if p.id in participant_ids]

    stats = {
        p.id: {
            "participation_id": p.id,
            "athlete": p.athlete.full_name,
            "team": p.team.name if p.team else "-",
            "draw_number": p.draw_number,
            "wins": 0,
            "losses": 0,
            "classification_points": 0,
            "falls": 0,
            "technical_superiority": 0,
            "points_for": 0,
            "points_against": 0,
        }
        for p in participants
    }

    qs = category.matches.filter(status=Match.Status.FINISHED)
    if group_label:
        qs = qs.filter(stage=Match.Stage.GROUP, group_label=group_label)
    elif category.system_type == Category.SystemType.ROUND_ROBIN:
        qs = qs.filter(stage=Match.Stage.ROUND_ROBIN)
    elif category.system_type == Category.SystemType.NORDIC:
        qs = qs.filter(stage=Match.Stage.GROUP)

    head_to_head = {}
    for m in qs.select_related("red", "blue", "winner"):
        if m.red_id not in stats or m.blue_id not in stats:
            continue
        stats[m.red_id]["points_for"] += m.red_score or 0
        stats[m.red_id]["points_against"] += m.blue_score or 0
        stats[m.red_id]["classification_points"] += m.red_classification_points
        stats[m.blue_id]["points_for"] += m.blue_score or 0
        stats[m.blue_id]["points_against"] += m.red_score or 0
        stats[m.blue_id]["classification_points"] += m.blue_classification_points
        if m.winner_id:
            loser_id = m.blue_id if m.winner_id == m.red_id else m.red_id
            stats[m.winner_id]["wins"] += 1
            stats[loser_id]["losses"] += 1
            head_to_head[frozenset({m.red_id, m.blue_id})] = m.winner_id
            if m.victory_method == Match.VictoryMethod.FALL:
                stats[m.winner_id]["falls"] += 1
            if m.victory_method == Match.VictoryMethod.TECHNICAL_SUPERIORITY:
                stats[m.winner_id]["technical_superiority"] += 1

    rows = list(stats.values())
    rows.sort(
        key=lambda x: (
            -x["wins"],
            -x["classification_points"],
            -x["falls"],
            -x["technical_superiority"],
            -x["points_for"],
            x["points_against"],
            x["draw_number"] or 9999,
        )
    )

    # Если ровно два соседних спортсмена полностью равны по основным критериям,
    # преимущество получает победитель личной встречи.
    i = 0
    while i < len(rows) - 1:
        a, b = rows[i], rows[i + 1]
        equal_key = (
            a["wins"], a["classification_points"], a["falls"], a["technical_superiority"],
            a["points_for"], a["points_against"],
        ) == (
            b["wins"], b["classification_points"], b["falls"], b["technical_superiority"],
            b["points_for"], b["points_against"],
        )
        if equal_key:
            winner_id = head_to_head.get(frozenset({a["participation_id"], b["participation_id"]}))
            if winner_id == b["participation_id"]:
                rows[i], rows[i + 1] = b, a
        i += 1

    for place, row in enumerate(rows, start=1):
        row["place"] = place
        row["score_difference"] = row["points_for"] - row["points_against"]
    return rows


def category_podium(category: Category):
    if category.system_type == Category.SystemType.ROUND_ROBIN:
        if category.status != Category.Status.FINISHED:
            return []
        standings = category_standings(category)
        return standings[:3]
    if category.system_type == Category.SystemType.NORDIC:
        final = category.matches.filter(stage=Match.Stage.FINAL, status=Match.Status.FINISHED).first()
        bronze = category.matches.filter(stage=Match.Stage.BRONZE, status=Match.Status.FINISHED).first()
        if not final:
            return []
        gold = final.winner
        silver = final.loser
        result = []
        if gold:
            result.append({"place": 1, "participation_id": gold.id, "athlete": gold.athlete.full_name, "team": gold.team.name if gold.team else "-"})
        if silver:
            result.append({"place": 2, "participation_id": silver.id, "athlete": silver.athlete.full_name, "team": silver.team.name if silver.team else "-"})
        if bronze and bronze.winner:
            result.append({"place": 3, "participation_id": bronze.winner.id, "athlete": bronze.winner.athlete.full_name, "team": bronze.winner.team.name if bronze.winner.team else "-"})
        return result

    final = category.matches.filter(stage=Match.Stage.FINAL, status=Match.Status.FINISHED).first()
    bronzes = list(category.matches.filter(stage=Match.Stage.BRONZE, status=Match.Status.FINISHED).order_by("branch_label"))
    if not final:
        return []
    result = []
    if final.winner:
        result.append({"place": 1, "participation_id": final.winner.id, "athlete": final.winner.athlete.full_name, "team": final.winner.team.name if final.winner.team else "-"})
    if final.loser:
        result.append({"place": 2, "participation_id": final.loser.id, "athlete": final.loser.athlete.full_name, "team": final.loser.team.name if final.loser.team else "-"})
    for bronze in bronzes:
        if bronze.winner:
            result.append({"place": 3, "participation_id": bronze.winner.id, "athlete": bronze.winner.athlete.full_name, "team": bronze.winner.team.name if bronze.winner.team else "-", "branch": bronze.branch_label})
    return result


def assign_mats(competition):
    """Закрепляет целые возрастно-весовые категории за коврами.

    Одна категория никогда не разбивается между несколькими коврами.
    Возрастные группы сортируются от младших к старшим и распределяются
    непрерывными блоками: младшие группы получают ковры с меньшими номерами.
    Все поединки категории наследуют mat_number своей Category.
    """
    mat_count = max(1, competition.mat_count or 1)
    categories = list(
        Category.objects.filter(competition=competition)
        .order_by("-birth_year_to", "-birth_year_from", "gender", "weight_limit", "id")
    )
    if not categories:
        return

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
        # Непрерывные блоки возраста: например, при 2 группах и 2 коврах
        # младшая группа целиком идёт на ковёр 1, старшая - на ковёр 2.
        group_to_mat[key] = min(mat_count, (index * mat_count) // group_count + 1)

    for category in categories:
        key = (category.birth_year_from, category.birth_year_to, category.gender, category.age_group)
        mat_number = group_to_mat[key]
        if category.mat_number != mat_number:
            category.mat_number = mat_number
            category.save(update_fields=["mat_number"])

    scheduled_by_mat = {number: 0 for number in range(1, mat_count + 1)}
    for category in categories:
        mat_number = category.mat_number or 1
        matches = category.matches.order_by("round_number", "order_index", "id")
        for match in matches:
            scheduled_by_mat[mat_number] += 1
            scheduled_order = scheduled_by_mat[mat_number]
            update_fields = []
            if match.mat_number != mat_number:
                match.mat_number = mat_number
                update_fields.append("mat_number")
            if match.scheduled_order != scheduled_order:
                match.scheduled_order = scheduled_order
                update_fields.append("scheduled_order")
            if update_fields:
                match.save(update_fields=update_fields)


def _demo_result_for_match(match: Match):
    """Возвращает детерминированный, но разнообразный результат для демонстрации."""
    seed = (match.category_id * 100003) + (match.id * 97) + (match.order_index * 31) + match.round_number
    rng = random.Random(seed)

    # Победители чередуются по цветам; небольшой случайный сдвиг убирает искусственный узор.
    winner_is_red = ((match.order_index + match.round_number + match.category_id) % 2 == 0)
    if rng.random() < 0.25:
        winner_is_red = not winner_is_red

    methods = [
        Match.VictoryMethod.POINTS,
        Match.VictoryMethod.POINTS,
        Match.VictoryMethod.POINTS,
        Match.VictoryMethod.TECHNICAL_SUPERIORITY,
        Match.VictoryMethod.TECHNICAL_SUPERIORITY,
        Match.VictoryMethod.FALL,
        Match.VictoryMethod.NO_SHOW,
        Match.VictoryMethod.MEDICAL_FORFEIT,
        Match.VictoryMethod.DISQUALIFICATION,
    ]
    method = methods[seed % len(methods)]

    if method == Match.VictoryMethod.POINTS:
        loser_score = rng.choice([0, 1, 2, 3, 4, 5, 6])
        winner_score = loser_score + rng.choice([1, 2, 2, 3, 4])
    elif method == Match.VictoryMethod.TECHNICAL_SUPERIORITY:
        loser_score = rng.choice([0, 0, 1, 2, 3, 4])
        winner_score = loser_score + 10
    elif method == Match.VictoryMethod.FALL:
        winner_score = rng.randint(0, 9)
        loser_score = rng.randint(0, 9)
    elif method == Match.VictoryMethod.NO_SHOW:
        winner_score = 0
        loser_score = 0
    elif method == Match.VictoryMethod.MEDICAL_FORFEIT:
        winner_score = rng.randint(0, 7)
        loser_score = rng.randint(0, 7)
    else:  # Дисквалификация
        winner_score = rng.randint(0, 8)
        loser_score = rng.randint(0, 8)

    if winner_is_red:
        return match.red_id, winner_score, loser_score, method
    return match.blue_id, loser_score, winner_score, method


@transaction.atomic
def simulate_category(category: Category):
    """Dev/demo helper: завершает категорию правдоподобными тестовыми результатами."""
    if not category.matches.exists():
        generate_bracket(category, shuffle=False)
    safety = 0
    while safety < 500:
        safety += 1
        ready = list(category.matches.filter(status=Match.Status.READY).order_by("order_index", "id"))
        if not ready:
            break
        for match in ready:
            winner_id, red_score, blue_score, method = _demo_result_for_match(match)
            record_result(match, winner_id, red_score, blue_score, method)
    return category
