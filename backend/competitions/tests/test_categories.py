from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from competitions.models import Category, Competition


class CategoryBulkCreateTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='admin', password='pass', is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.competition = Competition.objects.create(name='Категории', date=date(2026, 12, 5), venue='Зал')

    def test_bulk_create_weight_set(self):
        response = self.client.post('/api/categories/bulk-create/', {
            'competition': self.competition.id,
            'age_group': 'Юноши 2012-2013',
            'birth_year_from': 2012,
            'birth_year_to': 2013,
            'gender': 'male',
            'weights': [32, 35, 38, 41, 44, 48, 52, 57, 62, 68, 75, 85, 92, 100, 110],
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Category.objects.filter(competition=self.competition).count(), 15)

        second = self.client.post('/api/categories/bulk-create/', {
            'competition': self.competition.id,
            'age_group': 'Юноши 2012-2013',
            'birth_year_from': 2012,
            'birth_year_to': 2013,
            'gender': 'male',
            'weights': [32, 35, 38],
        }, format='json')
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data['created'], 0)
        self.assertEqual(Category.objects.filter(competition=self.competition).count(), 15)
