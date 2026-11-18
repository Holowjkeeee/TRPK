from io import BytesIO

from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Application, Category, Competition, FinalProtocol, Match, Participation, Team
from .serializers import (
    ApplicationSerializer,
    CategorySerializer,
    CompetitionSerializer,
    MatchSerializer,
    ParticipationSerializer,
    TeamSerializer,
    UserSerializer,
)
from .services.admission import available_transfer_categories, category_matches_athlete, recalculate_admission
from .services.brackets import assign_mats, category_podium, category_standings, generate_bracket, record_result, simulate_category
from .services.demo_data import generate_test_competitions
from .services.protocols import build_protocol_data, generate_final_protocol
from .services.word_applications import generate_application_template, import_application_docx


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


class CompetitionViewSet(viewsets.ModelViewSet):
    queryset = Competition.objects.select_related("created_by").all()
    serializer_class = CompetitionSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="generate-test-data")
    def generate_test_data(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Создание тестовых данных доступно только администратору"}, status=403)
        competitions = generate_test_competitions(user=request.user, replace=True)
        return Response(
            {
                "detail": "Тестовые соревнования созданы",
                "competitions": CompetitionSerializer(competitions, many=True).data,
            },
            status=201,
        )

    @action(detail=True, methods=["get"], url_path="application-template")
    def application_template(self, request, pk=None):
        competition = self.get_object()
        payload = generate_application_template(competition)
        filename = f"application_template_{competition.id}.docx"
        return FileResponse(
            BytesIO(payload),
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    @action(detail=True, methods=["post"], url_path="import-application")
    def import_application(self, request, pk=None):
        competition = self.get_object()
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response({"detail": "Файл не выбран"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            application = import_application_docx(competition, uploaded_file, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApplicationSerializer(application).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="protocol")
    def protocol(self, request, pk=None):
        competition = self.get_object()
        if request.method == "POST":
            role = getattr(getattr(request.user, "profile", None), "role", "organizer")
            if not request.user.is_staff and role not in {"organizer", "chief_secretary", "chief_judge"}:
                return Response({"detail": "Недостаточно прав для выпуска итогового протокола"}, status=status.HTTP_403_FORBIDDEN)
            try:
                generate_final_protocol(competition, request.user)
            except ValueError as exc:
                return Response({"detail": str(exc), **build_protocol_data(competition)}, status=status.HTTP_400_BAD_REQUEST)
            competition.refresh_from_db()
        return Response(build_protocol_data(competition))

    @action(detail=True, methods=["get"], url_path="protocol-download")
    def protocol_download(self, request, pk=None):
        competition = self.get_object()
        try:
            protocol = competition.final_protocol
        except FinalProtocol.DoesNotExist:
            return Response({"detail": "Итоговый протокол ещё не сформирован"}, status=status.HTTP_404_NOT_FOUND)
        if not protocol.document:
            return Response({"detail": "Файл итогового протокола отсутствует"}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(
            protocol.document.open("rb"),
            as_attachment=True,
            filename=f"final_protocol_{competition.id}.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        queryset = Category.objects.select_related("competition").all()
        competition_id = self.request.query_params.get("competition_id")
        if competition_id:
            queryset = queryset.filter(competition_id=competition_id)
        return queryset

    def perform_create(self, serializer):
        category = serializer.save()
        assign_mats(category.competition)

    def perform_destroy(self, instance):
        competition = instance.competition
        instance.delete()
        assign_mats(competition)

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        competition_id = request.data.get("competition")
        try:
            competition = Competition.objects.get(id=competition_id)
            birth_year_from = int(request.data.get("birth_year_from"))
            birth_year_to = int(request.data.get("birth_year_to"))
        except (Competition.DoesNotExist, TypeError, ValueError):
            return Response({"detail": "Некорректные параметры соревнования или возрастной группы"}, status=400)

        gender = request.data.get("gender") or "male"
        if gender not in {choice[0] for choice in Category._meta.get_field("gender").choices}:
            return Response({"detail": "Некорректное значение пола"}, status=400)
        age_group = str(request.data.get("age_group") or f"{birth_year_from}-{birth_year_to}").strip()
        weights = request.data.get("weights") or [32, 35, 38, 41, 44, 48, 52, 57, 62, 68, 75, 85, 92, 100, 110]
        try:
            weights = sorted({float(weight) for weight in weights if float(weight) > 0})
        except (TypeError, ValueError):
            return Response({"detail": "Список весов содержит некорректное значение"}, status=400)

        created = 0
        for weight in weights:
            weight_text = str(int(weight)) if weight.is_integer() else str(weight).rstrip("0").rstrip(".")
            _, was_created = Category.objects.get_or_create(
                competition=competition,
                birth_year_from=birth_year_from,
                birth_year_to=birth_year_to,
                weight_limit=weight,
                gender=gender,
                defaults={
                    "name": f"{age_group}, до {weight_text} кг",
                    "age_group": age_group,
                },
            )
            created += int(was_created)

        assign_mats(competition)
        queryset = self.get_queryset().filter(competition=competition)
        return Response({
            "detail": f"Добавлено категорий: {created}",
            "created": created,
            "categories": CategorySerializer(queryset, many=True).data,
        }, status=201)

    @action(detail=True, methods=["post"], url_path="generate-bracket")
    def generate_bracket_action(self, request, pk=None):
        category = self.get_object()
        try:
            generate_bracket(category, shuffle=True)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        category.refresh_from_db()
        return Response(CategorySerializer(category).data)

    @action(detail=True, methods=["get"], url_path="bracket")
    def bracket(self, request, pk=None):
        category = self.get_object()
        matches = category.matches.select_related(
            "red__athlete", "red__team", "blue__athlete", "blue__team", "winner__athlete", "winner__team"
        ).order_by("round_number", "order_index", "id")
        return Response(
            {
                "category": CategorySerializer(category).data,
                "matches": MatchSerializer(matches, many=True).data,
                "standings": category_standings(category) if category.system_type in {Category.SystemType.ROUND_ROBIN, Category.SystemType.NORDIC} else [],
                "podium": category_podium(category),
            }
        )

    @action(detail=True, methods=["get"], url_path="standings")
    def standings(self, request, pk=None):
        category = self.get_object()
        group = request.query_params.get("group") or None
        return Response(category_standings(category, group_label=group))

    @action(detail=True, methods=["post"], url_path="simulate-results")
    def simulate_results(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"detail": "Демо-заполнение доступно только администратору"}, status=403)
        category = self.get_object()
        try:
            simulate_category(category)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return self.bracket(request, pk=pk)


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer


class ApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        queryset = Application.objects.select_related("team", "competition").all()
        competition_id = self.request.query_params.get("competition_id")
        if competition_id:
            queryset = queryset.filter(competition_id=competition_id)
        return queryset


class ParticipationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ParticipationSerializer

    def get_queryset(self):
        queryset = Participation.objects.select_related(
            "athlete", "team", "declared_category", "confirmed_category", "application", "competition"
        ).order_by("athlete__last_name", "athlete__first_name", "athlete__middle_name")
        competition_id = self.request.query_params.get("competition_id")
        if competition_id:
            queryset = queryset.filter(competition_id=competition_id)
        return queryset

    def _save_and_serialize(self, participation):
        recalculate_admission(participation)
        participation.save()
        return Response(self.get_serializer(participation).data)

    @action(detail=True, methods=["patch"], url_path="documents")
    def documents(self, request, pk=None):
        participation = self.get_object()
        participation.documents_checked = bool(request.data.get("documents_checked", False))
        participation.medical_clearance = bool(request.data.get("medical_clearance", False))
        participation.insurance_checked = bool(request.data.get("insurance_checked", False))
        return self._save_and_serialize(participation)

    @action(detail=True, methods=["post"], url_path="confirm-category")
    def confirm_category(self, request, pk=None):
        participation = self.get_object()
        if participation.declared_category is None:
            return Response({"detail": "Заявленная категория не распознана. Сначала выберите категорию переноса."}, status=400)
        participation.confirmed_category = participation.declared_category
        participation.weigh_in_status = Participation.WeighInStatus.MATCHED
        participation.weigh_in_comment = str(request.data.get("comment") or "")[:255]
        participation.review_status = Participation.ReviewStatus.OK
        return self._save_and_serialize(participation)

    @action(detail=True, methods=["post"], url_path="needs-transfer")
    def needs_transfer(self, request, pk=None):
        participation = self.get_object()
        participation.confirmed_category = None
        participation.weigh_in_status = Participation.WeighInStatus.TRANSFER_REQUIRED
        participation.weigh_in_comment = str(request.data.get("comment") or "Требуется решение по весовой категории")[:255]
        participation.admission_status = Participation.AdmissionStatus.PENDING
        participation.admission_reason = ""
        participation.save()
        return Response(self.get_serializer(participation).data)

    @action(detail=True, methods=["get"], url_path="transfer-categories")
    def transfer_categories(self, request, pk=None):
        participation = self.get_object()
        categories = available_transfer_categories(participation)
        return Response(CategorySerializer(categories, many=True).data)

    @action(detail=True, methods=["post"], url_path="transfer")
    def transfer(self, request, pk=None):
        participation = self.get_object()
        category_id = request.data.get("category_id")
        try:
            category = Category.objects.get(id=category_id, competition=participation.competition)
        except (Category.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Выбранная категория не найдена в этом соревновании"}, status=400)

        if not category_matches_athlete(category, participation.athlete):
            return Response({"detail": "Категория не подходит по возрасту или полу спортсмена"}, status=400)

        participation.confirmed_category = category
        participation.weigh_in_status = Participation.WeighInStatus.TRANSFERRED
        participation.weigh_in_comment = str(request.data.get("comment") or "Перенос согласован")[:255]
        participation.review_status = Participation.ReviewStatus.OK
        return self._save_and_serialize(participation)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        participation = self.get_object()
        participation.confirmed_category = None
        participation.weigh_in_status = Participation.WeighInStatus.REJECTED
        participation.weigh_in_comment = str(request.data.get("reason") or "Не допущен по результату взвешивания")[:255]
        participation.admission_status = Participation.AdmissionStatus.REJECTED
        participation.admission_reason = participation.weigh_in_comment
        participation.save()
        return Response(self.get_serializer(participation).data)


class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MatchSerializer

    def get_queryset(self):
        queryset = Match.objects.select_related(
            "competition", "category", "red__athlete", "red__team", "blue__athlete", "blue__team", "winner__athlete", "winner__team"
        )
        competition_id = self.request.query_params.get("competition_id")
        category_id = self.request.query_params.get("category_id")
        status_value = self.request.query_params.get("status")
        if competition_id:
            queryset = queryset.filter(competition_id=competition_id)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset.order_by("category_id", "order_index", "id")

    @action(detail=True, methods=["post"], url_path="result")
    def result(self, request, pk=None):
        match = self.get_object()
        try:
            winner_id = int(request.data.get("winner_id"))
            red_score = int(request.data.get("red_score", 0))
            blue_score = int(request.data.get("blue_score", 0))
            victory_method = str(request.data.get("victory_method") or "")
            record_result(match, winner_id, red_score, blue_score, victory_method)
        except (TypeError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=400)
        match.refresh_from_db()
        return Response(MatchSerializer(match).data)
