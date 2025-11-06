from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models.base import AwareDataSource, JsonUrlDataSource, Profile
import uuid


class DataSourcesViewsTest(TestCase):
    def setUp(self):
        # Create a test user and profile
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user)
        self.client.login(username='testuser', password='testpass')
        self.source = AwareDataSource.objects.create(
            profile=self.profile,
            name='Test Aware Source'
        )

    def test_add_source_type(self):
        response = self.client.get(reverse('add_data_source', args=['Aware']))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data_sources/add_data_source.html')

    def test_add_source_type_post(self):
        response = self.client.post(reverse('add_data_source', args=['Aware']), {'name': 'Test Aware Source'})
        self.assertEqual(response.status_code, 302)
        # redirect to aware_instructions
        self.assertTrue(response.url.startswith('/data-sources/instructions'))

    def test_user_cannot_edit_others_source(self):
        """Tests that a user gets a 404 when trying to edit another user's source."""
        user2 = User.objects.create_user(username='user2', password='password123')
        Profile.objects.create(user=user2)
        self.client.login(username='user2', password='password123')

        response = self.client.get(reverse('edit_data_source', args=[self.source.id]))
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_delete_others_source(self):
        """Tests that a user cannot delete another user's source."""
        user2 = User.objects.create_user(username='user2', password='password123')
        Profile.objects.create(user=user2)
        self.client.login(username='user2', password='password123')

        # Try to POST to the delete URL for the first user's source
        response = self.client.post(reverse('delete_data_source', args=[self.source.id]))
        self.assertEqual(response.status_code, 404)

        # Verify the source still exists
        self.assertTrue(AwareDataSource.objects.filter(id=self.source.id).exists())

    def test_aware_mobile_setup_view(self):
        source = AwareDataSource.objects.create(
            profile=self.profile,
            name='Test Aware Source'
        )
        response = self.client.get(reverse('aware_mobile_setup', args=[source.config_token]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data_sources/aware/mobile_setup.html')
        self.assertIn('source', response.context)
        

class DataSourceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user)


class AwareDataSourceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user = self.user)
        self.source = AwareDataSource.objects.create(
            profile=self.profile,
            name='Test Aware Source'
        )
    
    @patch('data_sources.db_connector.get_device_id_for_label')
    def test_confirm_device_success(self, mock_get_device_id):
        device_id = uuid.uuid4()
        mock_get_device_id.return_value = device_id
        success, message = self.source.confirm_device()
        self.assertTrue(success)
        self.assertEqual(message, "AWARE device confirmed and linked successfully!")
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, 'active')
        self.assertEqual(self.source.device_id, device_id)


    
