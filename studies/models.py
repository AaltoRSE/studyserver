from django.db import models
from users.models import Profile
from data_sources.models import DataSource


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
    config_url = models.URLField(max_length=500, help_text="URL for fetching study configuration")
    
    def __str__(self):
        return self.title


class Consent(models.Model):
    participant = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='consents',
        limit_choices_to={'user_type': 'participant'}
    )
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='consents')
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='consents')
    is_complete = models.BooleanField(default=False)
    consent_date = models.DateTimeField(auto_now_add=True)
    revocation_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('participant', 'study')
    
    def __str__(self):
        return f"Consent of {self.participant.user.username} for {self.study.title}"
