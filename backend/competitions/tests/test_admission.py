from datetime import date

from django.test import TestCase

from competitions.models import Athlete, Category, Competition, Participation
from competitions.services.admission import find_declared_category, recalculate_admission


class AdmissionTests(TestCase):
    def setUp(self):
        self.competition = Competition.objects.create(name="Тест", date=date(2026, 11, 20), venue="Зал")
        self.athlete = Athlete.objects.create(last_name="Иванов", first_name="Иван", birth_year=2012, gender="male")
        self.category55 = Category.objects.create(competition=self.competition, name="до 55 кг", age_group="2012-2013", birth_year_from=2012, birth_year_to=2013, weight_limit=55, gender="male")
        self.category60 = Category.objects.create(competition=self.competition, name="до 60 кг", age_group="2012-2013", birth_year_from=2012, birth_year_to=2013, weight_limit=60, gender="male")

    def test_finds_declared_category_by_label(self):
        self.assertEqual(find_declared_category(self.competition, self.athlete, "55 кг"), self.category55)

    def test_admits_when_documents_and_category_are_confirmed(self):
        participation = Participation.objects.create(
            competition=self.competition,
            athlete=self.athlete,
            declared_category=self.category55,
            confirmed_category=self.category55,
            weigh_in_status=Participation.WeighInStatus.MATCHED,
            documents_checked=True,
            medical_clearance=True,
            insurance_checked=True,
        )
        recalculate_admission(participation)
        self.assertEqual(participation.admission_status, Participation.AdmissionStatus.ADMITTED)

    def test_transfer_keeps_new_category(self):
        participation = Participation.objects.create(
            competition=self.competition,
            athlete=self.athlete,
            declared_category=self.category55,
            confirmed_category=self.category60,
            weigh_in_status=Participation.WeighInStatus.TRANSFERRED,
            documents_checked=True,
            medical_clearance=True,
            insurance_checked=True,
        )
        recalculate_admission(participation)
        self.assertEqual(participation.admission_status, Participation.AdmissionStatus.ADMITTED)
        self.assertEqual(participation.confirmed_category, self.category60)
