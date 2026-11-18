from datetime import date

from django.test import TestCase

from competitions.models import Athlete, Category, Competition, Match, Participation
from competitions.services.brackets import assign_mats, generate_bracket, simulate_category


class BracketGenerationTests(TestCase):
    def setUp(self):
        self.competition = Competition.objects.create(
            name="Тест сеток",
            date=date.today(),
            venue="Зал",
            mat_count=2,
        )

    def make_category(self, weight, count):
        category = Category.objects.create(
            competition=self.competition,
            name=f"до {weight} кг",
            age_group="Юноши 2012-2013",
            birth_year_from=2012,
            birth_year_to=2013,
            weight_limit=weight,
            gender="male",
        )
        for index in range(count):
            athlete = Athlete.objects.create(
                last_name=f"Спортсмен{weight}_{index}",
                first_name="Тест",
                birth_year=2012,
                gender="male",
            )
            Participation.objects.create(
                competition=self.competition,
                athlete=athlete,
                declared_category=category,
                confirmed_category=category,
                declared_category_label=f"{weight} кг",
                weigh_in_status=Participation.WeighInStatus.MATCHED,
                documents_checked=True,
                medical_clearance=True,
                insurance_checked=True,
                admission_status=Participation.AdmissionStatus.ADMITTED,
            )
        return category

    def test_round_robin_for_five(self):
        category = self.make_category(50, 5)
        generate_bracket(category, shuffle=False)
        category.refresh_from_db()
        self.assertEqual(category.system_type, Category.SystemType.ROUND_ROBIN)
        self.assertEqual(category.matches.count(), 10)
        self.assertEqual(category.matches.filter(status=Match.Status.READY).count(), 10)

    def test_nordic_for_seven(self):
        category = self.make_category(55, 7)
        generate_bracket(category, shuffle=False)
        category.refresh_from_db()
        self.assertEqual(category.system_type, Category.SystemType.NORDIC)
        self.assertEqual(category.matches.filter(stage=Match.Stage.SEMIFINAL).count(), 2)
        self.assertEqual(category.matches.filter(stage=Match.Stage.FINAL).count(), 1)
        self.assertEqual(category.matches.filter(stage=Match.Stage.BRONZE).count(), 1)
        simulate_category(category)
        self.assertFalse(category.matches.exclude(status=Match.Status.FINISHED).exists())


    def test_category_is_never_split_between_mats(self):
        category = self.make_category(65, 5)
        generate_bracket(category, shuffle=False)
        category.refresh_from_db()
        mats = set(category.matches.values_list("mat_number", flat=True))
        self.assertEqual(mats, {category.mat_number})

    def test_younger_and_older_age_groups_use_different_mats(self):
        younger = self.make_category(70, 5)
        older = Category.objects.create(
            competition=self.competition,
            name="Старшие до 74 кг",
            age_group="Юноши 2010-2011",
            birth_year_from=2010,
            birth_year_to=2011,
            weight_limit=74,
            gender="male",
        )
        assign_mats(self.competition)
        younger.refresh_from_db()
        older.refresh_from_db()
        self.assertEqual(younger.mat_number, 1)
        self.assertEqual(older.mat_number, 2)

    def test_elimination_for_ten(self):
        category = self.make_category(60, 10)
        generate_bracket(category, shuffle=False)
        category.refresh_from_db()
        self.assertEqual(category.system_type, Category.SystemType.ELIMINATION)
        self.assertEqual(category.matches.filter(stage=Match.Stage.QUALIFICATION).count(), 2)
        self.assertEqual(category.matches.filter(stage=Match.Stage.FINAL).count(), 1)
        simulate_category(category)
        self.assertEqual(category.matches.filter(stage=Match.Stage.BRONZE).count(), 2)
        self.assertFalse(category.matches.exclude(status=Match.Status.FINISHED).exists())
