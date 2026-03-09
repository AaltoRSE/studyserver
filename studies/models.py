import uuid
from django.apps import apps
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import datetime
from users.models import Profile
from data_sources.models import DataSource


def _parse_config_date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        return dt
    except (ValueError, TypeError):
        return None


class Study(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    researchers = models.ManyToManyField(
        Profile,
        related_name='studies',
        limit_choices_to={'user_type': 'researcher'},
    )
    required_data_sources = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of required source types, e.g., ['AwareDataSource']"
    )
    optional_data_sources = models.JSONField(
        default=list,
        blank=True,
        help_text="List of optional source types, e.g., ['JsonUrlDataSource']"
    )

    domain = models.CharField(
        max_length=200,
        unique=True,
        null=True,
        blank=True,
        help_text="Domain name of the study's landing page"
    )

    config_url = models.URLField(max_length=500, help_text="URL for fetching study configuration")
    source_configurations = models.JSONField(
        default=dict,
        blank=True,
        help_text="Mapping of source configuration files for the study"
    )

    @property
    def raw_content_base_url(self):
        """ Convert a repo URL to its raw content base URL for some known services. """
        if not self.config_url:
            return None
        if 'github.com' in self.config_url:
            return self.config_url.replace('github.com', 'raw.githubusercontent.com') + '/main/'
        if 'gitlab.com' in self.config_url:
            return f"{self.config_url}/-/raw/{self.repo_branch}/"

        # raw urls also should work directly
        return self.config_url

    def get_data_type_dates(self, source_type, data_type):
        """Return (data_start, data_end) datetimes for a data type from source_configurations."""
        config = self.source_configurations.get(source_type)
        if not isinstance(config, dict):
            return None, None
        type_config = config.get(data_type, {})
        return (
            _parse_config_date(type_config.get('data_start')),
            _parse_config_date(type_config.get('data_end')),
        )

    def get_earliest_data_start(self, source_type):
        """Return the earliest configured data_start across all data types, or None."""
        config = self.source_configurations.get(source_type)
        if not isinstance(config, dict):
            return None
        starts = [
            _parse_config_date(v.get('data_start'))
            for v in config.values() if isinstance(v, dict)
        ]
        starts = [s for s in starts if s is not None]
        return min(starts) if starts else None

    def __str__(self):
        return self.title


class StudyParticipant(models.Model):
    participant = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='study_participations',
        limit_choices_to={'user_type': 'participant'}
    )
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='participations')
    pseudo_id = models.UUIDField(default=uuid.uuid4, editable=False)

    class Meta:
        unique_together = ('participant', 'study')

    def __str__(self):
        name = self.participant.user.username if self.participant else f"[deleted-{self.pseudo_id}]"
        return f"{name} in {self.study.title}"


class Consent(models.Model):
    participant = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='consents',
        limit_choices_to={'user_type': 'participant'}
    )
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='consents')
    data_source = models.ForeignKey(
        DataSource, 
        on_delete=models.SET_NULL,
        related_name='consents',
        null=True,
        blank=True
    )
    study_participant = models.ForeignKey(
        StudyParticipant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consents',
    )
    source_type = models.CharField(max_length=100)
    is_optional = models.BooleanField(default=False)
    is_complete = models.BooleanField(default=False)
    consent_text_accepted = models.BooleanField(default=False)
    consent_date = models.DateTimeField(null=True, blank=True)
    data_start = models.DateTimeField(
        null=True, blank=True,
        help_text="Start of the data collection period. May predate consent_date."
    )
    revocation_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Consent of {self.participant.user.username} for {self.study.title}"


