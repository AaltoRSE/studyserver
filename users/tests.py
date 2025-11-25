from django.test import TestCase, Client
from django.test import override_settings
from django.urls import reverse
from users.models import Profile
from rest_framework.authtoken.models import Token
from studies.models import Study, Consent
from django.contrib.auth.models import User
from django.urls import path
from django.contrib import messages
from django.http import HttpResponseRedirect
from study_server.urls import urlpatterns as real_urlpatterns

def test_message_view(request):
    messages.info(request, 'This is an info message.')
    return HttpResponseRedirect(reverse('dashboard'))

urlpatterns = real_urlpatterns + [
    path('test-message/', test_message_view, name='test_message_view'),
]

class StaticPagesTest(TestCase):
    def test_terms_of_service_renders(self):
        response = self.client.get(reverse('terms_of_service'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.content.decode().strip()) > 0)

    def test_privacy_statement_renders(self):
        response = self.client.get(reverse('privacy_statement'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.content.decode().strip()) > 0)

class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.study = Study.objects.create(
            title='Test Study',
            description='A test study',
            domain="testserver",
            config_url="test_url"
        )
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(
            user=self.user,
            user_type='participant'
        )

    def test_home_redirects_to_dashboard_if_in_study(self):
        Consent.objects.create(
            participant=self.profile,
            study = self.study
        )
        self.client.login(username='testuser', password='testpass')
        response = self.client.get('/')
        self.assertRedirects(response, reverse('dashboard'))

    def test_home_renders_study_detail_if_not_in_study(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get('/')
        self.assertContains(response, "fetching study page: Invalid URL")
    
class SignupViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_signup_page_loads(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
        })
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.filter(username='newuser').exists())


class SignupResearcherViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_signup_researcher_page_loads(self):
        response = self.client.get(reverse('signup_researcher'))
        self.assertEqual(response.status_code, 200)

    def test_signup_researcher_creates_user(self):
        response = self.client.post(reverse('signup_researcher'), {
            'username': 'newresearcher',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
        })
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.filter(username='newresearcher').exists())


class ManageTokenViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apitest', password='pass')
        self.profile = Profile.objects.create(user=self.user, user_type='participant')
        #self.token = Token.objects.create(user=self.user)
        self.client.login(username='apitest', password='pass')

    def test_token_is_shown(self):
        response = self.client.get(reverse('manage_token'))
        self.assertEqual(response.status_code, 200)
        token = Token.objects.get(user=self.user).key
        self.assertIn(token, response.content.decode())

    def test_token_refresh(self):
        old_token = Token.objects.get(user=self.user).key
        response = self.client.post(reverse('manage_token'), {'regenerate': '1'}, follow=True)
        new_token = Token.objects.get(user=self.user).key
        self.assertNotEqual(old_token, new_token)
        self.assertIn(new_token, response.content.decode())


class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.profile = Profile.objects.create(user=self.user, user_type='participant')
        self.study = Study.objects.create(title="PolAlpha Study")
        self.consent = Consent.objects.create(participant=self.profile, study=self.study)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders_for_participant(self):
        self.client.login(username='testuser', password='pass')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, self.study.title)

    @override_settings(ROOT_URLCONF=__name__)
    def test_dashboard_renders_info_message(self):
        """ use the message framework to show a message """
        self.client.login(username='testuser', password='pass')
        response = self.client.get(reverse('test_message_view'), follow=True)
        self.assertContains(response, 'This is an info message.')


class ResearcherDashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='researcher', password='pass')
        self.profile = Profile.objects.create(user=self.user, user_type='researcher')
        self.study = Study.objects.create(title="Research Study")
        self.study.researchers.add(self.profile)
        self.client.login(username='researcher', password='pass')
    
    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('researcher_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders_for_researcher(self):
        response = self.client.get(reverse('researcher_dashboard'))
        self.assertContains(response, self.study.title)

    

