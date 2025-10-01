import requests
import uuid
from django.db import models
from polymorphic.models import PolymorphicModel
from users.models import Profile
from . import db_connector


class DataSource(PolymorphicModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='data_sources')
    name = models.CharField(max_length=100, help_text="A personal name for this source")
    date_added = models.DateTimeField(auto_now_add=True)

    @property
    def model_name(self):
        """Returns the simple class name of the real instance."""
        return self.get_real_instance().__class__.__name__

    @property
    def display_type(self):
        """Returns a user-friendly name for the data source type."""
        return "Generic Data Source"

    def __str__(self):
        return f"{self.name} ({self.profile.user.username})"


class JsonUrlDataSource(DataSource):
    url = models.URLField(max_length=500, help_text="The URL where the JSON data can be fetched")

    @property
    def display_type(self):
        """Returns a user-friendly name for the data source type."""
        return "JSON URL"

    def fetch_data(self):
        """Fetches and returns the JSON data from the source URL.
        
        No formatting or processing, just returns the string."""
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Could not fetch data from URL: {e}"}


class AwareDataSource(DataSource):
    STATUS_CHOICES = (
        ("pending", "Pending Confirmation"),
        ("active", "Active"),
    )
    device_label = models.CharField(max_length=150, unique=True, default=uuid.uuid4)
    aware_device_id = models.CharField(max_length=150, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    config_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    @property
    def display_type(self):
        return "AWARE Mobile"
    
    def confirm_device(self):
        if self.status == 'active':
            return (True, "This device is already active.")

        retrieved_device_id = db_connector.get_aware_device_id_for_label(self.device_label)

        if not retrieved_device_id:
            return (False, "No data with that device label. It may take a few hours for data to appear. Please ensure AWARE is running on your device.") 

        is_claimed = AwareDataSource.objects.filter(aware_device_id=retrieved_device_id).exclude(id=self.id).exists()
        if is_claimed:
            return (False, "Error: This device ID has already been claimed by another user. Contact the administrator if you believe this is an error.")
        
        self.aware_device_id = retrieved_device_id
        self.status = 'active'
        self.save()
        return (True, "AWARE device confirmed and linked successfully!")

    
    def fetch_data(self, table_name='battery', limit=100):
        """Get's the users data from the AWARE server"""
        if self.status == 'active' and self.aware_device_id:
            return db_connector.get_aware_data(self.aware_device_id, table_name, limit)
        return None # Not active or no device ID


