from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import AwareDataSource, JsonUrlDataSource
from users.models import Profile
from django import forms
import uuid



class AddDataSourceViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user)
        self.client.login(username='testuser', password='testpass')

    def test_auto_create_data_source_with_only_name_field(self):
        response = self.client.get(reverse('add_data_source', args=['Aware']))
        self.assertEqual(response.status_code, 302)
        source = AwareDataSource.objects.filter(profile=self.profile).latest('id')
        expected_url = reverse('instructions', args=[source.id])
        self.assertEqual(response.url, expected_url)
        self.assertTrue(
            AwareDataSource.objects.filter(profile=self.profile, name__startswith='Aware').exists()
        )
        self.assertTrue(source.name.startswith('Aware'))


    def test_render_form_when_extra_fields(self):
        with patch('data_sources.forms.AwareDataSourceForm.base_fields', new={'name': forms.CharField(), 'extra': forms.CharField()}):
            response = self.client.get(reverse('add_data_source', args=['Aware']))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'data_sources/add_data_source.html')
            self.assertContains(response, 'name')

    def test_create_data_source_via_post(self):
        response = self.client.post(reverse('add_data_source', args=['Aware']), {'name': 'My New Source'})
        self.assertEqual(response.status_code, 302)
        source = AwareDataSource.objects.filter(profile=self.profile).latest('id')
        expected_url = reverse('instructions', args=[source.id])
        self.assertEqual(response.url, expected_url)
        self.assertTrue(
            AwareDataSource.objects.filter(profile=self.profile, name='My New Source').exists()
        )
        self.assertEqual(source.name, 'My New Source')

    def test_create_json_data_source_with_extra_field(self):
        post_data = {
            'name': 'My JSON Source',
            'url': 'https://example.com/data.json'
        }
        response = self.client.post(reverse('add_data_source', args=['JsonUrl']), post_data)
        self.assertEqual(response.status_code, 302)

        source = JsonUrlDataSource.objects.filter(profile=self.profile, name='My JSON Source').latest('id')
        self.assertEqual(response.url, reverse('dashboard'))
        self.assertEqual(source.url, 'https://example.com/data.json')
    



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


# Test for JsonUrlDataSource
class JsonUrlDataSourceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user)
        self.source = JsonUrlDataSource.objects.create(
            profile=self.profile,
            name='Test JSON Source',
            url='https://example.com/data.json'
        )


# Test for GooglePortabilityDataSource
from .models.google_portability import GooglePortabilityDataSource
class GooglePortabilityDataSourceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user)

    def test_create_google_source_redirects_to_oauth(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('add_data_source', args=['GooglePortability']))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/data-sources/oauth/start/', response.url)


# Test for TikTokPortabilityDataSource
from .models.tiktok_portability import TikTokPortabilityDataSource
class TikTokPortabilityDataSourceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user)

    def test_create_tiktok_source_redirects_to_oauth(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('add_data_source', args=['TikTokPortability']))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/data-sources/oauth/start/', response.url)


# Test for DataSource (base class)
from .models.base import DataSource
class DataSourceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user)




    
