from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    class Role(models.TextChoices):
        ORGANIZER = "organizer", "Организатор"
        CHIEF_JUDGE = "chief_judge", "Главный судья"
        CHIEF_SECRETARY = "chief_secretary", "Главный секретарь"
        TIMEKEEPER = "timekeeper", "Секундометрист / оператор"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.ORGANIZER)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class Competition(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Подготовка"
        REGISTRATION = "registration", "Приём заявок"
        WEIGH_IN = "weigh_in", "Взвешивание"
        RUNNING = "running", "Проводится"
        FINISHED = "finished", "Завершено"

    name = models.CharField(max_length=255)
    date = models.DateField()
    venue = models.CharField(max_length=255)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    mat_count = models.PositiveSmallIntegerField(default=2)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_competitions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=255, unique=True)
    city = models.CharField(max_length=150, blank=True)
    coach_name = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Athlete(models.Model):
    class Gender(models.TextChoices):
        MALE = "male", "Мужской"
        FEMALE = "female", "Женский"
        UNKNOWN = "unknown", "Не указан"

    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    birth_year = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.UNKNOWN)

    class Meta:
        ordering = ["last_name", "first_name", "middle_name"]
        indexes = [models.Index(fields=["last_name", "first_name", "birth_year"])]

    @property
    def full_name(self):
        return " ".join(part for part in [self.last_name, self.first_name, self.middle_name] if part)

    @property
    def effective_birth_year(self):
        return self.birth_date.year if self.birth_date else self.birth_year

    def __str__(self):
        return self.full_name


class TeamMembership(models.Model):
    athlete = models.ForeignKey(Athlete, on_delete=models.CASCADE, related_name="team_memberships")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="athlete_memberships")
    is_current = models.BooleanField(default=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["team__name", "athlete__last_name", "athlete__first_name"]
        constraints = [models.UniqueConstraint(fields=["athlete", "team"], name="uq_athlete_team_membership")]

    def __str__(self):
        return f"{self.athlete.full_name} - {self.team.name}"


class Category(models.Model):
    class SystemType(models.TextChoices):
        ROUND_ROBIN = "round_robin", "Круговая"
        NORDIC = "nordic", "Нордическая"
        ELIMINATION = "elimination", "Прямое выбывание"

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        READY = "ready", "Готова"
        RUNNING = "running", "Проводится"
        FINISHED = "finished", "Завершена"

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=200)
    age_group = models.CharField(max_length=120)
    birth_year_from = models.PositiveSmallIntegerField()
    birth_year_to = models.PositiveSmallIntegerField()
    weight_limit = models.DecimalField(max_digits=6, decimal_places=2)
    gender = models.CharField(max_length=20, choices=Athlete.Gender.choices, default=Athlete.Gender.MALE)
    mat_number = models.PositiveSmallIntegerField(null=True, blank=True)
    system_type = models.CharField(max_length=30, choices=SystemType.choices, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ["birth_year_from", "weight_limit", "name"]
        constraints = [models.UniqueConstraint(fields=["competition", "birth_year_from", "birth_year_to", "weight_limit", "gender"], name="uq_category_per_competition")]

    def __str__(self):
        return f"{self.name} ({self.competition.name})"


class Application(models.Model):
    class Status(models.TextChoices):
        IMPORTED = "imported", "Импортирована"
        NEEDS_REVIEW = "needs_review", "Требует уточнения"
        FAILED = "failed", "Ошибка импорта"

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="applications")
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name="applications")
    source_file = models.FileField(upload_to="applications/%Y/%m/%d/")
    original_name = models.CharField(max_length=255)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.IMPORTED)
    imported_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="imported_applications")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_name


class Participation(models.Model):
    class AdmissionStatus(models.TextChoices):
        PENDING = "pending", "Ожидает проверки"
        ADMITTED = "admitted", "Допущен"
        REJECTED = "rejected", "Не допущен"

    class ReviewStatus(models.TextChoices):
        OK = "ok", "Данные приняты"
        NEEDS_REVIEW = "needs_review", "Требует уточнения"

    class WeighInStatus(models.TextChoices):
        PENDING = "pending", "Не проверено"
        MATCHED = "matched", "Соответствует заявленной категории"
        TRANSFER_REQUIRED = "transfer_required", "Требуется перенос"
        TRANSFERRED = "transferred", "Перенесён в другую категорию"
        REJECTED = "rejected", "Не допущен по результату взвешивания"

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="participations")
    athlete = models.ForeignKey(Athlete, on_delete=models.CASCADE, related_name="participations")
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name="participations")
    application = models.ForeignKey(Application, null=True, blank=True, on_delete=models.SET_NULL, related_name="participations")
    declared_category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="declared_participations")
    confirmed_category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="confirmed_participations")
    declared_category_label = models.CharField(max_length=100, blank=True)
    weigh_in_status = models.CharField(max_length=30, choices=WeighInStatus.choices, default=WeighInStatus.PENDING)
    weigh_in_comment = models.CharField(max_length=255, blank=True)
    medical_clearance = models.BooleanField(default=False)
    insurance_checked = models.BooleanField(default=False)
    documents_checked = models.BooleanField(default=False)
    admission_status = models.CharField(max_length=30, choices=AdmissionStatus.choices, default=AdmissionStatus.PENDING)
    admission_reason = models.CharField(max_length=255, blank=True)
    review_status = models.CharField(max_length=30, choices=ReviewStatus.choices, default=ReviewStatus.OK)
    draw_number = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["athlete__last_name", "athlete__first_name"]
        constraints = [models.UniqueConstraint(fields=["competition", "athlete"], name="uq_athlete_competition")]

    @property
    def category(self):
        return self.confirmed_category or self.declared_category

    def __str__(self):
        return f"{self.athlete.full_name} - {self.competition.name}"


class Match(models.Model):
    class Stage(models.TextChoices):
        ROUND_ROBIN = "round_robin", "Круговая встреча"
        GROUP = "group", "Групповой этап"
        QUALIFICATION = "qualification", "Квалификация"
        MAIN = "main", "Основная сетка"
        SEMIFINAL = "semifinal", "Полуфинал"
        FINAL = "final", "Финал"
        REPECHAGE = "repechage", "Утешительная встреча"
        BRONZE = "bronze", "Встреча за бронзу"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает участников"
        READY = "ready", "Готов к проведению"
        FINISHED = "finished", "Завершён"

    class VictoryMethod(models.TextChoices):
        POINTS = "points", "По баллам"
        TECHNICAL_SUPERIORITY = "technical_superiority", "Техническое превосходство"
        FALL = "fall", "Туше"
        NO_SHOW = "no_show", "Неявка"
        MEDICAL_FORFEIT = "medical_forfeit", "Медицинское снятие"
        DISQUALIFICATION = "disqualification", "Дисквалификация"

    class Slot(models.TextChoices):
        RED = "red", "Красный"
        BLUE = "blue", "Синий"

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="matches")
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="matches")
    order_index = models.PositiveIntegerField(default=0)
    round_number = models.PositiveIntegerField(default=1)
    stage = models.CharField(max_length=30, choices=Stage.choices)
    stage_label = models.CharField(max_length=100, blank=True)
    group_label = models.CharField(max_length=10, blank=True)
    branch_label = models.CharField(max_length=10, blank=True)

    red = models.ForeignKey(Participation, null=True, blank=True, on_delete=models.SET_NULL, related_name="matches_red")
    blue = models.ForeignKey(Participation, null=True, blank=True, on_delete=models.SET_NULL, related_name="matches_blue")
    red_score = models.PositiveIntegerField(null=True, blank=True)
    blue_score = models.PositiveIntegerField(null=True, blank=True)
    red_classification_points = models.PositiveSmallIntegerField(default=0)
    blue_classification_points = models.PositiveSmallIntegerField(default=0)
    winner = models.ForeignKey(Participation, null=True, blank=True, on_delete=models.SET_NULL, related_name="won_matches")
    victory_method = models.CharField(max_length=40, choices=VictoryMethod.choices, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    next_match = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="winner_sources")
    next_slot = models.CharField(max_length=10, choices=Slot.choices, blank=True)
    loser_next_match = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="loser_sources")
    loser_next_slot = models.CharField(max_length=10, choices=Slot.choices, blank=True)

    mat_number = models.PositiveSmallIntegerField(null=True, blank=True)
    scheduled_order = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category_id", "order_index", "id"]
        indexes = [
            models.Index(fields=["competition", "category", "status"], name="match_comp_cat_status_idx"),
            models.Index(fields=["category", "stage", "round_number"], name="match_cat_stage_round_idx"),
        ]

    @property
    def is_ready(self):
        return bool(self.red_id and self.blue_id and self.status != self.Status.FINISHED)

    @property
    def loser(self):
        if not self.winner_id:
            return None
        if self.red_id == self.winner_id:
            return self.blue
        if self.blue_id == self.winner_id:
            return self.red
        return None

    def refresh_status(self):
        if self.status == self.Status.FINISHED:
            return
        self.status = self.Status.READY if self.red_id and self.blue_id else self.Status.PENDING

    def __str__(self):
        return f"{self.category.name}: {self.stage_label or self.get_stage_display()} #{self.id}"


class FinalProtocol(models.Model):
    competition = models.OneToOneField(Competition, on_delete=models.CASCADE, related_name="final_protocol")
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_final_protocols",
    )
    generated_at = models.DateTimeField(auto_now=True)
    snapshot = models.JSONField(default=dict, blank=True)
    document = models.FileField(upload_to="protocols/%Y/%m/%d/", blank=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"Итоговый протокол - {self.competition.name}"
