"""Три показательных теста из раздела 5 курсовой: модульный, функциональный, интеграционный."""
from datetime import date
from io import BytesIO
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from docx import Document
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from competitions.models import Athlete, Category, Competition, Participation, UserProfile
from competitions.services.word_applications import import_application_docx
from competitions.services.brackets import select_system


class TournamentSystemUnitTest(SimpleTestCase):
    def test_select_system_thresholds(self):
        # Один модульный тест на три ключевые границы из предметной области.
        self.assertEqual(select_system(5), Category.SystemType.ROUND_ROBIN)
        self.assertEqual(select_system(7), Category.SystemType.NORDIC)
        self.assertEqual(select_system(8), Category.SystemType.ELIMINATION)
        with self.assertRaises(ValueError):
            select_system(1)
        print("[Модульный] 5 -> круговая; 7 -> нордическая; 8 -> прямое выбывание: OK")


class AdmissionFunctionalTest(TestCase):
    def test_documents_and_category_confirmation_through_api(self):
        # Функциональная проверка варианта использования A1.3 через реальный REST API.
        user = get_user_model().objects.create_user(username="secretary", password="test")
        user.profile.role = UserProfile.Role.CHIEF_SECRETARY
        user.profile.save(update_fields=["role"])
        competition = Competition.objects.create(name="Контроль допуска", date=date(2026, 11, 20), venue="Зал", created_by=user)
        category = Category.objects.create(competition=competition, name="до 55 кг", age_group="2012–2013", birth_year_from=2012, birth_year_to=2013, weight_limit=55, gender="male")
        athlete = Athlete.objects.create(last_name="Иванов", first_name="Иван", birth_year=2012, gender="male")
        participation = Participation.objects.create(competition=competition, athlete=athlete, declared_category=category)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f"/api/participations/{participation.pk}/confirm-category/", format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["admission_status"], Participation.AdmissionStatus.PENDING)

        response = client.patch(f"/api/participations/{participation.pk}/documents/", {
            "documents_checked": True, "medical_clearance": True, "insurance_checked": True,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["admission_status"], Participation.AdmissionStatus.ADMITTED)
        participation.refresh_from_db()
        self.assertEqual(participation.confirmed_category, category)
        self.assertEqual(participation.admission_status, Participation.AdmissionStatus.ADMITTED)
        print("[Функциональный] POST confirm-category + PATCH documents -> ADMITTED: OK")


class WordApplicationIntegrationTest(TestCase):
    def test_docx_import_reuses_athlete_in_second_competition(self):
        # A1.1: чтение DOCX -> сопоставление существующего Athlete -> новая Participation в БД.
        user = get_user_model().objects.create_user(username="import_secretary", password="test")
        first = Competition.objects.create(name="Турнир 1", date=date(2026, 11, 20), venue="Зал")
        second = Competition.objects.create(name="Турнир 2", date=date(2026, 12, 5), venue="Зал")
        for competition in (first, second):
            Category.objects.create(competition=competition, name="до 55 кг", age_group="2012–2013", birth_year_from=2012, birth_year_to=2013, weight_limit=55, gender="male")

        def upload(competition, filename):
            document = Document()
            document.add_paragraph("Команда: Богатырь")
            table = document.add_table(rows=1, cols=4)
            for index, header in enumerate(("ФИО", "Год рождения", "Весовая категория", "Пол")):
                table.rows[0].cells[index].text = header
            row = table.add_row().cells
            row[0].text, row[1].text, row[2].text, row[3].text = "Иванов Иван Иванович", "2012", "55 кг", "м"
            stream = BytesIO()
            document.save(stream)
            uploaded = SimpleUploadedFile(filename, stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            return import_application_docx(competition, uploaded, user)

        first_import = upload(first, "first.docx")
        second_import = upload(second, "second.docx")
        self.assertEqual(first_import.imported_rows, 1)
        self.assertEqual(second_import.imported_rows, 1)
        self.assertEqual(Athlete.objects.count(), 1, "Спортсмен не должен дублироваться")
        athlete = Athlete.objects.get(last_name="Иванов", first_name="Иван")
        self.assertEqual(athlete.participations.count(), 2)
        self.assertEqual(athlete.team_memberships.count(), 1)
        self.assertEqual(athlete.participations.get(competition=second).declared_category.weight_limit, 55)
        print("[Интеграционный] DOCX 1 + DOCX 2 -> 1 Athlete, 2 Participation: OK")
