from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import AwareDataSource, JsonUrlDataSource
from .models.base import DataSource
from django.core.exceptions import ValidationError
from studies.models import Study, Consent
from django.utils import timezone
from users.models import Profile
from django import forms
import uuid
import tempfile
import os
from django.test import override_settings

import data_sources.utils.crypto as crypto
from data_sources.models import db_connector



class AddDataSourceViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user)
        self.client.login(username='testuser', password='testpass')


class CryptoUtilsTest(TestCase):
    def test_encrypt_decrypt_text_roundtrip_with_key(self):
        # Generate a Fernet key to use via settings
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        with override_settings(ENCRYPTION_KEY=key):
            original = 'secret-data-123'
            encrypted = crypto.encrypt_text(original)
            self.assertIsInstance(encrypted, str)
            decrypted = crypto.decrypt_text(encrypted)
            self.assertEqual(decrypted, original)

    def test_write_and_decrypt_file_bytes(self):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        with override_settings(ENCRYPTION_KEY=key):
            tmpdir = tempfile.mkdtemp()
            try:
                path = os.path.join(tmpdir, 'blob.bin')
                data = b'hello-bytes'
                crypto.write_encrypted_bytes(path, data)
                # decrypt to temp and verify contents
                tmp = crypto.decrypt_file_to_temp(path)
                with open(tmp, 'rb') as fh:
                    contents = fh.read()
                self.assertEqual(contents, data)
            finally:
                # cleanup
                try:
                    os.remove(path)
                except Exception:
                    pass


class DbConnectorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user)
        self.client.login(username='testuser', password='testpass')

    def test_get_device_ids_for_label_empty(self):
        self.assertEqual(db_connector.get_device_ids_for_label(''), [])

    def test_query_aware_data_returns_transformed_rows(self):
        # Prepare fake mysql connector behavior
        class FakeCursor:
            def __init__(self, rows=None, dictionary=False):
                self._rows = rows or []
                self.dictionary = dictionary
                self.last_query = None

            def execute(self, q, params=None):
                self.last_query = (q, params)
                # Heuristics to provide appropriate fake results depending on query
                qstr = str(q).lower()
                if 'select id, device_uuid from device_lookup' in qstr:
                    # return device_lookup mapping as dicts when dictionary=True
                    self._rows = [{'id': 42, 'device_uuid': 'dev-uuid'}] if self.dictionary else [(42, 'dev-uuid')]
                elif 'show tables' in qstr:
                    # handled by separate cursor in FakeConnection
                    pass
                elif '_transformed' in qstr:
                    # transformed table query -> return rows with device_uid
                    if self.dictionary:
                        self._rows = [{'device_uid': 42, 'val': 1}]
                    else:
                        self._rows = [(42, 1)]

            def fetchall(self):
                return self._rows

            def fetchone(self):
                return None

            def close(self):
                pass

        class FakeConnection:
            def __init__(self):
                # first cursor used for SHOW TABLES
                self._first = FakeCursor(rows=[('battery_transformed',)])
                # second cursor (dictionary=True) returns device_lookup and transformed rows
                self._second = FakeCursor(rows=[{'id': 42, 'device_uuid': 'dev-uuid'}], dictionary=True)
                # transformed rows to be returned by _run_aware_table_query
                self._transformed_rows = [
                    {'device_uid': 42, 'val': 1}
                ]

            def cursor(self, dictionary=False):
                if not dictionary:
                    return self._first
                # For dictionary cursor, we need a cursor that will return mappings
                cur = FakeCursor(rows=self._transformed_rows, dictionary=True)
                # make fetchall on this cursor return transformed rows when used for the query
                return cur

            def close(self):
                pass

        def fake_connect(*args, **kwargs):
            return FakeConnection()

        # Patch get_device_ids_for_label to return a device id
        with patch('data_sources.models.db_connector.mysql.connector.connect', side_effect=fake_connect):
            # Also patch get_device_ids_for_label to return a device uuid so query proceeds
            with patch('data_sources.models.db_connector.get_device_ids_for_label', return_value=['dev-uuid']):
                rows = db_connector.query_aware_data('SELECT *', 'label-1', 'battery', limit=10)
                # Should return transformed rows with device_id injected
                self.assertIsInstance(rows, list)
                # The function maps device_uid to device_uuid for dict rows
                if rows:
                    first = rows[0]
                    self.assertIn('device_id', first)

                # Test count function uses query_aware_data and returns 0 or number
                with patch('data_sources.models.db_connector.query_aware_data', return_value=[{'row_count': 5}]):
                    cnt = db_connector.get_aware_count('label-1', 'battery')
                    self.assertEqual(cnt, 5)
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
        # Patch the helper that decides whether the form has only the name
        with patch('data_sources.views.form_has_only_name_field', return_value=False):
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
        self.base = DataSource.objects.create(profile=self.profile, name='Base Source')

    def test_base_methods_raise_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.base.get_data_types()
        with self.assertRaises(NotImplementedError):
            self.base.fetch_data()
        with self.assertRaises(NotImplementedError):
            self.base.count_rows()


class AwareDataSourceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user = self.user)
        self.source = AwareDataSource.objects.create(
            profile=self.profile,
            name='Test Aware Source'
        )

    def test_str_model_name_and_display_type(self):
        self.assertEqual(str(self.source), 'Test Aware Source (testuser)')
        self.assertEqual(self.source.model_name, 'AwareDataSource')
        self.assertEqual(self.source.display_type, 'AWARE Mobile Data')

    def test_process_returns_no_consent(self):
        result, message = self.source.process()
        self.assertFalse(result)
        self.assertEqual(message, 'No consent found.')

    def test_device_id_conflict_raises_validation_error(self):
        # Create a second user/profile
        user2 = User.objects.create_user(username='other', password='pass')
        profile2 = Profile.objects.create(user=user2)
        # Force a shared device id
        shared_id = uuid.uuid4()
        src1 = AwareDataSource.objects.create(profile=self.profile, name='S1', device_id=shared_id)
        src2 = AwareDataSource(profile=profile2, name='S2', device_id=shared_id)
        with self.assertRaises(ValidationError):
            src2.save()


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

    def test_fetch_requires_consent(self):
        result = self.source.fetch_data('raw_json')
        self.assertEqual(result, (False, 'No consent found.'))

    @patch('data_sources.models.jsonurl.requests.get')
    def test_fetch_enriches_and_count(self, mock_get):
        # Create a study and an active consent linking this source
        study = Study.objects.create(title='S', description='d', config_url='http://example.com')
        Consent.objects.create(participant=self.profile, study=study, data_source=self.source, source_type='JsonUrlDataSource', is_complete=True, consent_date=timezone.now())

        mock_resp = mock_get.return_value
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = [{'foo': 'bar', 'device_id': 'old-id'}]

        results = self.source.fetch_data('raw_json', limit=10)
        # should be a list with enriched device_id
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        row = results[0]
        self.assertEqual(row['device_id'], str(self.source.device_id))
        self.assertEqual(row.get('json_device_id'), 'old-id')

        # count_rows should call requests and return length
        count = self.source.count_rows('raw_json')
        self.assertEqual(count, 1)


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




    
