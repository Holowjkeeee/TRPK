from collections import defaultdict
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from competitions.models import Category, Competition, FinalProtocol, Match, Participation
from competitions.services.brackets import category_podium, category_standings


def _athlete_payload(participation):
    if not participation:
        return None
    return {
        "participation_id": participation.id,
        "athlete": participation.athlete.full_name,
        "team": participation.team.name if participation.team else "-",
        "draw_number": participation.draw_number,
    }


def _match_payload(match):
    red = _athlete_payload(match.red)
    blue = _athlete_payload(match.blue)
    winner = _athlete_payload(match.winner)
    score = None
    if match.red_score is not None and match.blue_score is not None:
        score = f"{match.red_score}:{match.blue_score}"
    return {
        "id": match.id,
        "stage": match.stage,
        "stage_label": match.stage_label or match.get_stage_display(),
        "round_number": match.round_number,
        "group_label": match.group_label,
        "branch_label": match.branch_label,
        "red": red,
        "blue": blue,
        "score": score,
        "winner": winner,
        "victory_method": match.get_victory_method_display() if match.victory_method else "",
        "status": match.status,
        "status_display": match.get_status_display(),
    }


def protocol_blocking_issues(competition: Competition):
    issues = []
    categories = list(competition.categories.all().order_by("birth_year_from", "weight_limit", "id"))
    if not categories:
        issues.append("В соревновании не создано ни одной категории")
        return issues

    meaningful_categories = 0
    for category in categories:
        admitted_count = Participation.objects.filter(
            competition=competition,
            confirmed_category=category,
            admission_status=Participation.AdmissionStatus.ADMITTED,
        ).count()
        if admitted_count == 0:
            continue
        meaningful_categories += 1
        if admitted_count == 1:
            issues.append(f"{category.name}: один допущенный спортсмен - требуется решение судейской коллегии")
            continue
        if not category.matches.exists():
            issues.append(f"{category.name}: турнирная сетка не сформирована")
            continue
        unfinished = category.matches.exclude(status=Match.Status.FINISHED).count()
        if unfinished:
            issues.append(f"{category.name}: не завершено поединков - {unfinished}")
            continue
        if not category_podium(category):
            issues.append(f"{category.name}: итоговые места ещё не определены")

    if meaningful_categories == 0:
        issues.append("Нет допущенных спортсменов, по которым можно сформировать итоговые результаты")
    return issues


def _category_payload(category: Category):
    admitted = Participation.objects.filter(
        competition=category.competition,
        confirmed_category=category,
        admission_status=Participation.AdmissionStatus.ADMITTED,
    ).select_related("athlete", "team")

    matches = list(
        category.matches.select_related(
            "red__athlete", "red__team", "blue__athlete", "blue__team", "winner__athlete", "winner__team"
        ).order_by("round_number", "order_index", "id")
    )

    podium = category_podium(category)
    standings = []
    groups = {}
    if category.system_type == Category.SystemType.ROUND_ROBIN:
        standings = category_standings(category)
    elif category.system_type == Category.SystemType.NORDIC:
        groups = {
            "A": category_standings(category, group_label="A"),
            "B": category_standings(category, group_label="B"),
        }

    return {
        "id": category.id,
        "name": category.name,
        "age_group": category.age_group,
        "weight_limit": str(category.weight_limit),
        "gender": category.get_gender_display(),
        "system_type": category.system_type,
        "system_type_display": category.get_system_type_display() if category.system_type else "-",
        "status": category.status,
        "status_display": category.get_status_display(),
        "admitted_count": admitted.count(),
        "matches_count": len(matches),
        "finished_matches_count": sum(1 for match in matches if match.status == Match.Status.FINISHED),
        "podium": podium,
        "standings": standings,
        "groups": groups,
        "matches": [_match_payload(match) for match in matches],
    }


def _team_medals(categories):
    medals = defaultdict(lambda: {"team": "-", "gold": 0, "silver": 0, "bronze": 0, "total": 0})
    for category in categories:
        for item in category.get("podium", []):
            team = item.get("team") or "-"
            row = medals[team]
            row["team"] = team
            place = item.get("place")
            if place == 1:
                row["gold"] += 1
            elif place == 2:
                row["silver"] += 1
            elif place == 3:
                row["bronze"] += 1
            row["total"] += 1
    result = list(medals.values())
    result.sort(key=lambda x: (-x["gold"], -x["silver"], -x["bronze"], -x["total"], x["team"]))
    for index, row in enumerate(result, start=1):
        row["place"] = index
    return result


def build_protocol_data(competition: Competition):
    issues = protocol_blocking_issues(competition)
    categories = [
        _category_payload(category)
        for category in competition.categories.all().order_by("birth_year_from", "weight_limit", "id")
        if Participation.objects.filter(
            competition=competition,
            confirmed_category=category,
            admission_status=Participation.AdmissionStatus.ADMITTED,
        ).exists()
    ]

    admitted_count = competition.participations.filter(admission_status=Participation.AdmissionStatus.ADMITTED).count()
    finished_matches = competition.matches.filter(status=Match.Status.FINISHED).count()
    matches_count = competition.matches.count()
    existing = FinalProtocol.objects.filter(competition=competition).select_related("generated_by").first()

    return {
        "competition": {
            "id": competition.id,
            "name": competition.name,
            "date": competition.date.isoformat(),
            "venue": competition.venue,
            "mat_count": competition.mat_count,
            "status": competition.status,
            "status_display": competition.get_status_display(),
        },
        "summary": {
            "categories_count": len(categories),
            "admitted_count": admitted_count,
            "matches_count": matches_count,
            "finished_matches_count": finished_matches,
        },
        "can_finalize": not issues,
        "blocking_issues": issues,
        "categories": categories,
        "team_medals": _team_medals(categories),
        "generated_protocol": None if not existing else {
            "id": existing.id,
            "generated_at": existing.generated_at.isoformat(),
            "generated_by": existing.generated_by.username if existing.generated_by else "-",
            "filename": existing.document.name.rsplit("/", 1)[-1] if existing.document else "",
        },
    }


def _set_cell_text(cell, value, bold=False):
    cell.text = ""
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run(str(value))
    run.bold = bold
    run.font.name = "Times New Roman"
    run.font.size = Pt(11)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def _set_cell_shading(cell, fill="FFFFFF"):
    tc_pr = cell._tc.get_or_add_tcPr()
    for old in tc_pr.findall(qn("w:shd")):
        tc_pr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _style_table(table):
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row in table.rows:
        for cell in row.cells:
            _set_cell_shading(cell)
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(11)


def _add_title(document, text, size=16):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    return paragraph


def _add_heading(document, text, level=1):
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(8)
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(text)
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(14 if level == 1 else 12)
    return paragraph


def generate_protocol_docx(data):
    document = Document()
    section = document.sections[0]
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(1.8)

    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11)

    competition = data["competition"]
    _add_title(document, "ИТОГОВЫЙ ПРОТОКОЛ", 18)
    _add_title(document, competition["name"], 14)
    meta = document.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_run = meta.add_run(f"{competition['date']} · {competition['venue']} · ковров: {competition['mat_count']}")
    meta_run.font.name = "Times New Roman"
    meta_run.font.size = Pt(11)

    summary = data["summary"]
    _add_heading(document, "Сводные данные")
    table = document.add_table(rows=2, cols=4)
    headers = ["Категорий", "Допущено", "Поединков", "Завершено"]
    values = [summary["categories_count"], summary["admitted_count"], summary["matches_count"], summary["finished_matches_count"]]
    for i, value in enumerate(headers):
        _set_cell_text(table.rows[0].cells[i], value, bold=True)
        _set_cell_text(table.rows[1].cells[i], values[i])
    _style_table(table)

    if data["team_medals"]:
        _add_heading(document, "Командный медальный зачёт")
        table = document.add_table(rows=1, cols=6)
        for i, header in enumerate(["#", "Команда", "1 место", "2 место", "3 место", "Всего"]):
            _set_cell_text(table.rows[0].cells[i], header, bold=True)
        for item in data["team_medals"]:
            cells = table.add_row().cells
            for i, value in enumerate([item["place"], item["team"], item["gold"], item["silver"], item["bronze"], item["total"]]):
                _set_cell_text(cells[i], value)
        _style_table(table)

    for category in data["categories"]:
        _add_heading(document, category["name"])
        info = document.add_paragraph()
        run = info.add_run(
            f"Возрастная группа: {category['age_group']}; система: {category['system_type_display']}; "
            f"участников: {category['admitted_count']}; поединков: {category['matches_count']}."
        )
        run.font.name = "Times New Roman"
        run.font.size = Pt(11)

        if category["podium"]:
            podium_table = document.add_table(rows=1, cols=4)
            for i, header in enumerate(["Место", "Спортсмен", "Команда", "Ветка"]):
                _set_cell_text(podium_table.rows[0].cells[i], header, bold=True)
            for item in category["podium"]:
                cells = podium_table.add_row().cells
                values = [item.get("place", ""), item.get("athlete", ""), item.get("team", "-"), item.get("branch", "")]
                for i, value in enumerate(values):
                    _set_cell_text(cells[i], value)
            _style_table(podium_table)

        if category["system_type"] == Category.SystemType.ROUND_ROBIN and category["standings"]:
            _add_heading(document, "Итоговая классификация", level=2)
            standings_table = document.add_table(rows=1, cols=6)
            for i, header in enumerate(["Место", "Спортсмен", "Команда", "Победы", "Кл. очки", "Баллы"]):
                _set_cell_text(standings_table.rows[0].cells[i], header, bold=True)
            for item in category["standings"]:
                cells = standings_table.add_row().cells
                values = [item["place"], item["athlete"], item["team"], item["wins"], item["classification_points"], f"{item['points_for']}:{item['points_against']}"]
                for i, value in enumerate(values):
                    _set_cell_text(cells[i], value)
            _style_table(standings_table)

        _add_heading(document, "Результаты поединков", level=2)
        matches_table = document.add_table(rows=1, cols=6)
        for i, header in enumerate(["Этап", "Красный", "Счёт", "Синий", "Победитель", "Способ победы"]):
            _set_cell_text(matches_table.rows[0].cells[i], header, bold=True)
        for match in category["matches"]:
            if match["status"] != Match.Status.FINISHED:
                continue
            red = match["red"]["athlete"] if match["red"] else "-"
            blue = match["blue"]["athlete"] if match["blue"] else "-"
            winner = match["winner"]["athlete"] if match["winner"] else "-"
            values = [match["stage_label"], red, match["score"] or "-", blue, winner, match["victory_method"] or "-"]
            cells = matches_table.add_row().cells
            for i, value in enumerate(values):
                _set_cell_text(cells[i], value)
        _style_table(matches_table)

    document.add_paragraph()
    footer = document.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = footer.add_run(f"Сформировано системой MATFLOW: {timezone.localtime().strftime('%d.%m.%Y %H:%M')}")
    run.font.name = "Times New Roman"
    run.font.size = Pt(9)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@transaction.atomic
def generate_final_protocol(competition: Competition, user=None):
    readiness = build_protocol_data(competition)
    if not readiness["can_finalize"]:
        raise ValueError("Итоговый протокол нельзя сформировать: " + "; ".join(readiness["blocking_issues"]))

    if competition.status != Competition.Status.FINISHED:
        competition.status = Competition.Status.FINISHED
        competition.save(update_fields=["status"])

    data = build_protocol_data(competition)
    payload = generate_protocol_docx(data)
    protocol, _ = FinalProtocol.objects.get_or_create(competition=competition)
    if protocol.document:
        protocol.document.delete(save=False)
    protocol.generated_by = user
    protocol.snapshot = data
    filename = f"final_protocol_competition_{competition.id}.docx"
    protocol.document.save(filename, ContentFile(payload), save=False)
    protocol.save()
    return protocol
