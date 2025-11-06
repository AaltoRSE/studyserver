import uuid
from django.db import models
from polymorphic.models import PolymorphicModel
from users.models import Profile


class DataSource(PolymorphicModel):
    STATUS_CHOICES = (
        ("pending", "Pending Confirmation"),
        ("active", "Active"),
    )
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='data_sources')
    device_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100, help_text="A personal name for this source")
    date_added = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
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
        """Returns context and template name for instructions card."""
        return {}, None

    def get_confirm_url(self):
        return None

    def get_data_types(self):
        """Returns a list of available data type names for this source."""
        raise NotImplementedError("Subclasses must implement this method.")
    
    def fetch_data(self):
        """Fetches and returns data from the source. """
        raise NotImplementedError("Subclasses must implement this method.")

    def __str__(self):
        return f"{self.name} ({self.profile.user.username})"
