import uuid
from django.db import models
from polymorphic.models import PolymorphicModel
from users.models import Profile


class DataSource(PolymorphicModel):
    status = models.CharField(
        max_length=20,
        choices=(
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("active", "Active"),
        ),
        default='pending'
    )
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='data_sources')
    device_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100, help_text="A personal name for this source")
    date_added = models.DateTimeField(auto_now_add=True)
    
    config_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    oauth_state = models.CharField(max_length=100, blank=True, null=True)
    
    requires_confirmation = False
    requires_setup = False

    @property
    def model_name(self):
        """Returns the simple class name of the real instance."""
        return self.get_real_instance().__class__.__name__

    @property
    def display_type(self):
        """Returns a user-friendly name for the data source type."""
        return "Generic Data"

    def get_instructions_card(self, request, consent_id=None, study_id=None):
        """HTML card shown in instructions and dashboard."""
        return None
    
    def get_setup_url(self):
        """URL to redirect to after creating the source"""
        return None
    
    def revoke_and_delete(self):
        """Revoke any permissions and delete the source."""
        pass

    def get_confirm_url(self):
        return None
    
    def confirm_and_download(self):
        """Confirm the source and download any initial data if needed."""
        return None
    
    def process(self):
        """ Run periodic processing tasks for this data source.
        """
        return None

    def get_data_types(self):
        """Returns a list of available data type names for this source."""
        raise NotImplementedError("Subclasses must implement this method.")
    
    def fetch_data(self):
        """Fetches and returns data from the source. """
        raise NotImplementedError("Subclasses must implement this method.")

    def __str__(self):
        return f"{self.name} ({self.profile.user.username})"
