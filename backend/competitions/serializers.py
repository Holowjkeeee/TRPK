from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Application, Athlete, Category, Competition, Match, Participation, Team

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "role", "role_display", "is_staff"]

    def get_role(self, obj):
        return getattr(getattr(obj, "profile", None), "role", "organizer")

    def get_role_display(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.get_role_display() if profile else "Организатор"


class CompetitionSerializer(serializers.ModelSerializer):
    categories_count = serializers.IntegerField(source="categories.count", read_only=True)
    participants_count = serializers.IntegerField(source="participations.count", read_only=True)
    admitted_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    matches_count = serializers.IntegerField(source="matches.count", read_only=True)

    class Meta:
        model = Competition
        fields = [
            "id", "name", "date", "venue", "registration_deadline", "mat_count", "status", "status_display",
            "created_by", "created_at", "categories_count", "participants_count", "admitted_count", "matches_count",
        ]
        read_only_fields = ["created_by", "created_at"]

    def get_admitted_count(self, obj):
        return obj.participations.filter(admission_status=Participation.AdmissionStatus.ADMITTED).count()


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "city", "coach_name"]


class AthleteSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    effective_birth_year = serializers.IntegerField(read_only=True)
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)

    class Meta:
        model = Athlete
        fields = [
            "id", "last_name", "first_name", "middle_name", "full_name", "birth_date", "birth_year",
            "effective_birth_year", "gender", "gender_display",
        ]


class CategorySerializer(serializers.ModelSerializer):
    participants_count = serializers.SerializerMethodField()
    admitted_count = serializers.SerializerMethodField()
    system_type_display = serializers.CharField(source="get_system_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    matches_count = serializers.IntegerField(source="matches.count", read_only=True)
    bracket_generated = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "competition", "name", "age_group", "birth_year_from", "birth_year_to", "weight_limit",
            "gender", "mat_number", "system_type", "system_type_display", "status", "status_display", "participants_count",
            "admitted_count", "matches_count", "bracket_generated",
        ]

    def get_participants_count(self, obj):
        return obj.declared_participations.count()

    def get_admitted_count(self, obj):
        return obj.confirmed_participations.filter(admission_status=Participation.AdmissionStatus.ADMITTED).count()

    def get_bracket_generated(self, obj):
        return obj.matches.exists()


class ApplicationSerializer(serializers.ModelSerializer):
    team = TeamSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id", "competition", "team", "original_name", "status", "status_display", "imported_rows",
            "duplicate_rows", "error_rows", "errors", "created_at",
        ]


class ParticipationBriefSerializer(serializers.ModelSerializer):
    athlete = AthleteSerializer(read_only=True)
    team = TeamSerializer(read_only=True)

    class Meta:
        model = Participation
        fields = ["id", "athlete", "team", "draw_number", "admission_status"]


class ParticipationSerializer(serializers.ModelSerializer):
    athlete = AthleteSerializer(read_only=True)
    team = TeamSerializer(read_only=True)
    declared_category = CategorySerializer(read_only=True)
    confirmed_category = CategorySerializer(read_only=True)
    category = serializers.SerializerMethodField()
    admission_status_display = serializers.CharField(source="get_admission_status_display", read_only=True)
    review_status_display = serializers.CharField(source="get_review_status_display", read_only=True)
    weigh_in_status_display = serializers.CharField(source="get_weigh_in_status_display", read_only=True)

    class Meta:
        model = Participation
        fields = [
            "id", "competition", "athlete", "team", "application", "declared_category", "declared_category_label",
            "confirmed_category", "category", "weigh_in_status", "weigh_in_status_display", "weigh_in_comment",
            "medical_clearance", "insurance_checked", "documents_checked", "admission_status",
            "admission_status_display", "admission_reason", "review_status", "review_status_display", "draw_number",
        ]

    def get_category(self, obj):
        category = obj.confirmed_category or obj.declared_category
        return CategorySerializer(category).data if category else None


class MatchSerializer(serializers.ModelSerializer):
    red = ParticipationBriefSerializer(read_only=True)
    blue = ParticipationBriefSerializer(read_only=True)
    winner = ParticipationBriefSerializer(read_only=True)
    loser = serializers.SerializerMethodField()
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    victory_method_display = serializers.CharField(source="get_victory_method_display", read_only=True)

    class Meta:
        model = Match
        fields = [
            "id", "competition", "category", "order_index", "round_number", "stage", "stage_display", "stage_label",
            "group_label", "branch_label", "red", "blue", "red_score", "blue_score", "red_classification_points",
            "blue_classification_points", "winner", "loser", "victory_method", "victory_method_display", "status",
            "status_display", "next_match", "next_slot", "loser_next_match", "loser_next_slot", "mat_number",
            "scheduled_order",
        ]

    def get_loser(self, obj):
        loser = obj.loser
        return ParticipationBriefSerializer(loser).data if loser else None
