import re
from decimal import Decimal, InvalidOperation

from competitions.models import Athlete, Category, Participation


def extract_weight_limit(value):
    if value in (None, ""):
        return None
    text = str(value).replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return Decimal(match.group(0))
    except InvalidOperation:
        return None


def category_matches_athlete(category: Category, athlete: Athlete):
    birth_year = athlete.effective_birth_year
    if not birth_year:
        return False
    if not (category.birth_year_from <= birth_year <= category.birth_year_to):
        return False
    if athlete.gender != Athlete.Gender.UNKNOWN and category.gender not in {athlete.gender, Athlete.Gender.UNKNOWN}:
        return False
    return True


def find_declared_category(competition, athlete, label):
    weight_limit = extract_weight_limit(label)
    if weight_limit is None:
        return None

    queryset = Category.objects.filter(competition=competition, weight_limit=weight_limit)
    for category in queryset.order_by("birth_year_from", "id"):
        if category_matches_athlete(category, athlete):
            return category
    return None


def available_transfer_categories(participation: Participation):
    categories = Category.objects.filter(competition=participation.competition).order_by("weight_limit", "name")
    return [category for category in categories if category_matches_athlete(category, participation.athlete)]


def recalculate_admission(participation: Participation):
    if participation.weigh_in_status == Participation.WeighInStatus.REJECTED:
        participation.admission_status = Participation.AdmissionStatus.REJECTED
        if not participation.admission_reason:
            participation.admission_reason = participation.weigh_in_comment or "Не допущен по результату взвешивания"
        return participation.admission_status

    ready_by_weight = participation.weigh_in_status in {
        Participation.WeighInStatus.MATCHED,
        Participation.WeighInStatus.TRANSFERRED,
    }
    documents_ok = participation.documents_checked and participation.medical_clearance and participation.insurance_checked

    if ready_by_weight and documents_ok and participation.confirmed_category_id:
        participation.admission_status = Participation.AdmissionStatus.ADMITTED
        participation.admission_reason = ""
    else:
        participation.admission_status = Participation.AdmissionStatus.PENDING
        participation.admission_reason = ""

    return participation.admission_status
