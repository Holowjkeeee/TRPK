import re
from datetime import date, datetime
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import transaction
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from competitions.models import Application, Athlete, Participation
from competitions.services.admission import find_declared_category
from competitions.services.athlete_registry import get_or_create_team, resolve_athlete_for_team

HEADER_ALIASES = {
    "team": {"команда", "клуб", "организация", "спортшкола", "спортивная школа"},
    "full_name": {"фио", "ф.и.о.", "фамилия имя отчество", "спортсмен", "участник"},
    "last_name": {"фамилия"},
    "first_name": {"имя"},
    "middle_name": {"отчество"},
    "birth_date": {"дата рождения", "дата рожд.", "дата рожд"},
    "birth_year": {"год рождения", "год рожд.", "год рожд", "г.р."},
    "declared_category": {"весовая категория", "категория", "вес. категория", "весовая кат.", "весовая кат"},
    "gender": {"пол"},
    "coach_name": {"тренер", "фио тренера", "представитель команды"},
    "city": {"город", "населенный пункт", "населённый пункт"},
}


def _norm(value):
    value = str(value or "").replace("\xa0", " ").strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value.rstrip(":")


def _header_key(value):
    value = _norm(value)
    for key, aliases in HEADER_ALIASES.items():
        if value in aliases:
            return key
    return None


def _extract_default_team(document):
    patterns = [r"(?:команда|клуб|организация|спортшкола)\s*[:\-]\s*(.+)"]
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if re.search(r"[A-Za-zА-Яа-яЁё0-9]", candidate.replace("_", "")):
                    return candidate
    return None


def _parse_full_name(value):
    parts = [part for part in re.split(r"\s+", str(value or "").strip()) if part]
    if len(parts) < 2:
        raise ValueError("ФИО должно содержать минимум фамилию и имя")
    return parts[0], parts[1], " ".join(parts[2:]) if len(parts) > 2 else ""


def _parse_birth(value, year_only=False):
    if value in (None, ""):
        raise ValueError("Не указана дата/год рождения")
    if isinstance(value, datetime):
        return value.date(), value.year
    if isinstance(value, date):
        return value, value.year

    text = str(value).strip()
    if re.fullmatch(r"\d{4}", text):
        year = int(text)
        return None, year

    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt).date()
            return parsed, parsed.year
        except ValueError:
            pass

    if year_only:
        match = re.search(r"(19|20)\d{2}", text)
        if match:
            return None, int(match.group(0))
    raise ValueError(f"Некорректная дата рождения: {text}")


def _normalize_gender(value):
    value = _norm(value)
    if value in {"м", "муж", "мужской", "male", "юноши", "юноша"}:
        return Athlete.Gender.MALE
    if value in {"ж", "жен", "женский", "female", "девушки", "девушка"}:
        return Athlete.Gender.FEMALE
    return Athlete.Gender.UNKNOWN


def generate_application_template(competition):
    document = Document()
    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Cm(29.7)
    section.page_height = Cm(21.0)
    section.top_margin = Cm(1.3)
    section.bottom_margin = Cm(1.3)
    section.left_margin = Cm(1.3)
    section.right_margin = Cm(1.3)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("ЗАЯВКА НА УЧАСТИЕ В СОРЕВНОВАНИИ")
    run.bold = True
    run.font.size = Pt(14)

    p = document.add_paragraph()
    p.add_run("Соревнование: ").bold = True
    p.add_run(competition.name)
    p = document.add_paragraph()
    p.add_run("Дата: ").bold = True
    p.add_run(competition.date.strftime("%d.%m.%Y"))
    p = document.add_paragraph()
    p.add_run("Место проведения: ").bold = True
    p.add_run(competition.venue)
    document.add_paragraph("Команда: ________________________________________________")
    document.add_paragraph("Тренер / представитель: __________________________________")

    categories = list(competition.categories.order_by("birth_year_from", "weight_limit"))
    if categories:
        values = ", ".join(category.name for category in categories)
        document.add_paragraph(f"Категории соревнования: {values}")

    document.add_paragraph(
        "В таблице укажите категорию, в которую спортсмен заявляется (например, 57 кг или до 57 кг). "
        "Точный фактический вес в заявку не вносится: на взвешивании фиксируется только соответствие заявленной категории либо перенос."
    )

    headers = ["№", "ФИО", "Дата рождения", "Год рождения", "Весовая категория", "Пол"]
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for idx, header in enumerate(headers):
        table.rows[0].cells[idx].text = header

    for number in range(1, 16):
        row = table.add_row().cells
        row[0].text = str(number)
        row[5].text = "м"

    output = BytesIO()
    document.save(output)
    output.seek(0)
    return output.getvalue()


def _find_best_table(document):
    best = None
    best_score = -1
    for table in document.tables:
        for row_index, row in enumerate(table.rows[:3]):
            keys = [_header_key(cell.text) for cell in row.cells]
            score = sum(1 for key in keys if key)
            if score > best_score:
                best = (table, row_index, keys)
                best_score = score
    if best is None or best_score < 2:
        raise ValueError("В документе не найдена таблица со спортсменами")
    return best


@transaction.atomic
def import_application_docx(competition, uploaded_file, user):
    if not uploaded_file.name.lower().endswith(".docx"):
        raise ValueError("Поддерживаются только файлы .docx")

    payload = uploaded_file.read()
    try:
        document = Document(BytesIO(payload))
    except Exception as exc:
        raise ValueError("Не удалось открыть DOCX-файл") from exc

    default_team_name = _extract_default_team(document)
    table, header_index, header_keys = _find_best_table(document)

    application = Application.objects.create(
        competition=competition,
        source_file=ContentFile(payload, name=uploaded_file.name),
        original_name=uploaded_file.name,
        imported_by=user,
    )

    imported = 0
    duplicates = 0
    errors = []
    team_ids = set()

    for document_row_number, row in enumerate(table.rows[header_index + 1 :], start=header_index + 2):
        raw = [cell.text.strip() for cell in row.cells]
        if not any(raw):
            continue

        values = {}
        for idx, key in enumerate(header_keys):
            if key and idx < len(raw):
                values[key] = raw[idx]

        try:
            team_name = (values.get("team") or default_team_name or "").strip()
            if not team_name:
                raise ValueError("Не указана команда/клуб")

            if values.get("full_name"):
                last_name, first_name, middle_name = _parse_full_name(values["full_name"])
            else:
                last_name = (values.get("last_name") or "").strip()
                first_name = (values.get("first_name") or "").strip()
                middle_name = (values.get("middle_name") or "").strip()
                if not last_name or not first_name:
                    raise ValueError("Не указаны фамилия и имя спортсмена")

            if values.get("birth_date"):
                birth_date, birth_year = _parse_birth(values["birth_date"])
            elif values.get("birth_year"):
                birth_date, birth_year = _parse_birth(values["birth_year"], year_only=True)
            else:
                raise ValueError("Не указана дата/год рождения")

            category_label = (values.get("declared_category") or "").strip()
            if not category_label:
                raise ValueError("Не указана весовая категория")

            gender = _normalize_gender(values.get("gender"))
            team = get_or_create_team(
                team_name,
                city=(values.get("city") or ""),
                coach_name=(values.get("coach_name") or ""),
            )
            team_ids.add(team.id)

            athlete, _athlete_created, _membership_created = resolve_athlete_for_team(
                team=team,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                birth_date=birth_date,
                birth_year=birth_year,
                gender=gender,
            )

            declared_category = find_declared_category(competition, athlete, category_label)
            review_status = Participation.ReviewStatus.OK if declared_category else Participation.ReviewStatus.NEEDS_REVIEW

            participation, created = Participation.objects.get_or_create(
                competition=competition,
                athlete=athlete,
                defaults={
                    "team": team,
                    "application": application,
                    "declared_category": declared_category,
                    "declared_category_label": category_label,
                    "review_status": review_status,
                },
            )

            if not created:
                duplicates += 1
                participation.review_status = Participation.ReviewStatus.NEEDS_REVIEW
                participation.application = application
                participation.team = team
                participation.declared_category = declared_category
                participation.declared_category_label = category_label
                participation.save(update_fields=[
                    "review_status", "application", "team", "declared_category", "declared_category_label", "updated_at"
                ])
            else:
                imported += 1

            if declared_category is None:
                errors.append({
                    "row": document_row_number,
                    "error": f"Категория «{category_label}» не найдена для возраста/пола спортсмена. Запись импортирована и требует уточнения.",
                })

        except Exception as exc:
            errors.append({"row": document_row_number, "error": str(exc)})

    if len(team_ids) == 1:
        application.team_id = next(iter(team_ids))

    application.imported_rows = imported
    application.duplicate_rows = duplicates
    application.error_rows = len(errors)
    application.errors = errors
    application.status = Application.Status.NEEDS_REVIEW if duplicates or errors else Application.Status.IMPORTED
    application.save()
    return application
