from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ApplicationViewSet, CategoryViewSet, CompetitionViewSet, MatchViewSet, ParticipationViewSet, TeamViewSet, me

router = DefaultRouter()
router.register("competitions", CompetitionViewSet, basename="competition")
router.register("categories", CategoryViewSet, basename="category")
router.register("teams", TeamViewSet, basename="team")
router.register("applications", ApplicationViewSet, basename="application")
router.register("participations", ParticipationViewSet, basename="participation")
router.register("matches", MatchViewSet, basename="match")

urlpatterns = [path("me/", me, name="me")] + router.urls
