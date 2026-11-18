from django.contrib.auth import get_user_model
from django.test import TestCase

from competitions.models import Competition, Match, Participation
from competitions.services.demo_data import generate_test_competitions


class DemoDataTests(TestCase):
    def test_generates_iteration_three_demo_competitions(self):
        user = get_user_model().objects.create_user(username="admin")
        competitions = generate_test_competitions(user=user)
        self.assertEqual(len(competitions), 4)
        self.assertEqual(Competition.objects.filter(name__startswith="[ТЕСТ]").count(), 4)
        grid_competition = Competition.objects.get(name__contains="5 / 7 / 10")
        self.assertGreaterEqual(grid_competition.categories.count(), 12)
        counts = sorted(
            count for count in (
                category.confirmed_participations.filter(admission_status=Participation.AdmissionStatus.ADMITTED).count()
                for category in grid_competition.categories.all()
            ) if count
        )
        self.assertEqual(counts, [5, 7, 10])

        protocol_competition = Competition.objects.get(name__contains="итогового протокола")
        self.assertEqual(protocol_competition.status, Competition.Status.FINISHED)
        self.assertFalse(protocol_competition.matches.exclude(status="finished").exists())

        finished = list(protocol_competition.matches.filter(status=Match.Status.FINISHED))
        self.assertTrue(any(match.winner_id == match.red_id for match in finished))
        self.assertTrue(any(match.winner_id == match.blue_id for match in finished))
        self.assertGreater(len({match.victory_method for match in finished}), 2)
        self.assertTrue(any((match.red_score, match.blue_score) != (3, 1) for match in finished))
