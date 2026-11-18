from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from docx import Document

from competitions.models import Athlete, Category, Competition, Participation, TeamMembership
from competitions.services.word_applications import import_application_docx


class WordImportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="pass")
        self.competition = Competition.objects.create(name="Тест", date=date(2026, 11, 20), venue="Зал")
        self.category = Category.objects.create(
            competition=self.competition,
            name="Юноши 2012-2013, до 55 кг",
            age_group="Юноши 2012-2013",
            birth_year_from=2012,
            birth_year_to=2013,
            weight_limit=55,
            gender="male",
        )

    def test_imports_word_table_with_weight_category(self):
        doc = Document()
        doc.add_paragraph("Команда: Богатырь")
        table = doc.add_table(rows=1, cols=4)
        headers = ["ФИО", "Год рождения", "Весовая категория", "Пол"]
        for i, header in enumerate(headers):
            table.rows[0].cells[i].text = header
        row = table.add_row().cells
        row[0].text = "Иванов Иван Иванович"
        row[1].text = "2012"
        row[2].text = "55 кг"
        row[3].text = "м"
        stream = BytesIO()
        doc.save(stream)

        uploaded = SimpleUploadedFile("application.docx", stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        application = import_application_docx(self.competition, uploaded, self.user)

        self.assertEqual(application.imported_rows, 1)
        participation = Participation.objects.get()
        self.assertEqual(participation.team.name, "Богатырь")
        self.assertEqual(participation.declared_category, self.category)
        self.assertEqual(participation.declared_category_label, "55 кг")
    def _upload(self, competition, team_name, filename="application.docx"):
        doc = Document()
        doc.add_paragraph(f"Команда: {team_name}")
        table = doc.add_table(rows=1, cols=4)
        for i, header in enumerate(["ФИО", "Год рождения", "Весовая категория", "Пол"]):
            table.rows[0].cells[i].text = header
        row = table.add_row().cells
        row[0].text = "Иванов Иван Иванович"
        row[1].text = "2012"
        row[2].text = "55 кг"
        row[3].text = "м"
        stream = BytesIO()
        doc.save(stream)
        uploaded = SimpleUploadedFile(filename, stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        return import_application_docx(competition, uploaded, self.user)

    def test_reuses_existing_athlete_for_same_team_in_another_competition(self):
        self._upload(self.competition, "Богатырь", "first.docx")
        second = Competition.objects.create(name="Тест 2", date=date(2026, 12, 1), venue="Зал")
        Category.objects.create(competition=second, name="Юноши 2012-2013, до 55 кг", age_group="Юноши 2012-2013", birth_year_from=2012, birth_year_to=2013, weight_limit=55, gender="male")
        self._upload(second, "Богатырь", "second.docx")

        self.assertEqual(Athlete.objects.filter(last_name="Иванов", first_name="Иван").count(), 1)
        athlete = Athlete.objects.get(last_name="Иванов", first_name="Иван")
        self.assertEqual(athlete.team_memberships.count(), 1)
        self.assertEqual(athlete.participations.count(), 2)

    def test_keeps_same_athlete_and_adds_membership_after_team_change(self):
        self._upload(self.competition, "Богатырь", "first.docx")
        second = Competition.objects.create(name="Тест 2", date=date(2026, 12, 1), venue="Зал")
        Category.objects.create(competition=second, name="Юноши 2012-2013, до 55 кг", age_group="Юноши 2012-2013", birth_year_from=2012, birth_year_to=2013, weight_limit=55, gender="male")
        self._upload(second, "Сокол", "second.docx")

        athlete = Athlete.objects.get(last_name="Иванов", first_name="Иван")
        self.assertEqual(Athlete.objects.count(), 1)
        self.assertEqual(TeamMembership.objects.filter(athlete=athlete).count(), 2)
        current = TeamMembership.objects.get(athlete=athlete, is_current=True)
        self.assertEqual(current.team.name, "Сокол")
        self.assertEqual(athlete.participations.get(competition=self.competition).team.name, "Богатырь")
        self.assertEqual(athlete.participations.get(competition=second).team.name, "Сокол")

