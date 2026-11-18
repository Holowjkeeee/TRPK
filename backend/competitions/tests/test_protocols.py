from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from competitions.models import Athlete, Category, Competition, FinalProtocol, Participation
from competitions.services.brackets import generate_bracket, simulate_category
from competitions.services.protocols import build_protocol_data, generate_final_protocol


class FinalProtocolTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="secretary", password="test")
        self.competition = Competition.objects.create(
            name="Протокол - тест",
            date=date.today(),
            venue="СК Тест",
            mat_count=2,
            created_by=self.user,
        )
        self.category = Category.objects.create(
            competition=self.competition,
            name="Юноши до 50 кг",
            age_group="Юноши 2012-2013",
            birth_year_from=2012,
            birth_year_to=2013,
            weight_limit=50,
            gender="male",
        )
        for index in range(5):
            athlete = Athlete.objects.create(
                last_name=f"Протоколов{index}",
                first_name="Тест",
                birth_year=2012,
                gender="male",
            )
            Participation.objects.create(
                competition=self.competition,
                athlete=athlete,
                declared_category=self.category,
                confirmed_category=self.category,
                declared_category_label="50 кг",
                weigh_in_status=Participation.WeighInStatus.MATCHED,
                documents_checked=True,
                medical_clearance=True,
                insurance_checked=True,
                admission_status=Participation.AdmissionStatus.ADMITTED,
            )
        generate_bracket(self.category, shuffle=False)

    def test_preview_blocks_unfinished_competition(self):
        data = build_protocol_data(self.competition)
        self.assertFalse(data["can_finalize"])
        self.assertTrue(any("не завершено поединков" in item for item in data["blocking_issues"]))

    def test_generates_docx_after_all_matches_finished(self):
        simulate_category(self.category)
        data = build_protocol_data(self.competition)
        self.assertTrue(data["can_finalize"])
        self.assertEqual(data["summary"]["categories_count"], 1)
        self.assertEqual(len(data["categories"][0]["podium"]), 3)

        protocol = generate_final_protocol(self.competition, self.user)
        self.assertTrue(FinalProtocol.objects.filter(competition=self.competition).exists())
        self.assertTrue(protocol.document.name.endswith(".docx"))
        protocol.document.open("rb")
        payload = protocol.document.read(2)
        protocol.document.close()
        self.assertEqual(payload, b"PK")

        self.competition.refresh_from_db()
        self.assertEqual(self.competition.status, Competition.Status.FINISHED)
