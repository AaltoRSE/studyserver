from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import AwareDataSource, Profile


class DataSourcesViewsTest(TestCase):
    def setUp(self):
        # Create a test user and profile
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user)
        self.client.login(username='testuser', password='testpass')

    def test_add_aware_source_get(self):
        response = self.client.get(reverse('add_aware_source'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data_sources/add_aware_source.html')

    def test_add_aware_source_post_valid(self):
        response = self.client.post(
            reverse('add_aware_source'),
            {'name': 'Test Aware Source'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            AwareDataSource.objects.filter(
                name='Test Aware Source',
                profile=self.profile
            ).exists()
        )

    def test_aware_instructions_view(self):
        source = AwareDataSource.objects.create(
            profile=self.profile,
            name='Test Aware Source'
        )
        response = self.client.get(reverse('aware_instructions', args=[source.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data_sources/aware_instructions.html')
        self.assertIn('qr_code_image', response.context)
        
    def test_aware_instructions_view_invalid_source(self):
        response = self.client.get(reverse('aware_instructions', args=[999]))
        self.assertEqual(response.status_code, 404)
    
    def test_aware_instructions_view_unauthenticated(self):
        self.client.logout()
        source = AwareDataSource.objects.create(
            profile=self.profile,
            name='Test Aware Source'
        )
        response = self.client.get(reverse('aware_instructions', args=[source.id]))
        self.assertEqual(response.status_code, 302)

    def test_aware_mobile_setup_view(self):
        source = AwareDataSource.objects.create(
            profile=self.profile,
            name='Test Aware Source'
        )
        response = self.client.get(reverse('aware_mobile_setup', args=[source.config_token]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data_sources/aware_mobile_setup.html')
        self.assertIn('source', response.context)
        
        
class AwareDataSourceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user = self.user)
        self.source = AwareDataSource.objects.create(
            profile=self.profile,
            name='Test Aware Source'
        )
    
    @patch('data_sources.db_connector.get_aware_device_id_for_label')
    def test_confirm_device_success(self, mock_get_device_id):
        mock_get_device_id.return_value = 'device123'
        success, message = self.source.confirm_device()
        self.assertTrue(success)
        self.assertEqual(message, "AWARE device confirmed and linked successfully!")
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, 'active')
        self.assertEqual(self.source.aware_device_id, 'device123')
