import requests
import uuid
from django.db import models
from django.urls import reverse
from polymorphic.models import PolymorphicModel
from users.models import Profile
from . import db_connector


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
        return "Generic Data Source"
    
    def get_confirm_url(self):
        print("Getting confirm URL")
        return None

    def get_data_types(self):
        """Returns a list of available data type names for this source."""
        raise NotImplementedError("Subclasses must implement this method.")
    
    def fetch_data(self):
        """Fetches and returns data from the source. """
        raise NotImplementedError("Subclasses must implement this method.")

    def __str__(self):
        return f"{self.name} ({self.profile.user.username})"


class JsonUrlDataSource(DataSource):
    url = models.URLField(max_length=500, help_text="The URL where the JSON data can be fetched")

    @property
    def display_type(self):
        """Returns a user-friendly name for the data source type."""
        return "JSON URL"
    
    def get_data_types(self):
        return ["raw_json"]

    def fetch_data(self, data_type, limit=10000, start_date=None, end_date=None):
        """Fetches and returns the JSON data from the source URL.
        
        No formatting or processing, just returns the string."""
        if data_type != 'raw_json':
            return {"error": "Invalid data type requested."}
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, list):
                # Response must be a list. Assuming this is a single object, wrap in a list.
                result = [result]
            
            enriched_data = []
            for row in result:
                if 'device_id' in row:
                    row['json_device_id'] = row['device_id']
                row['device_id'] = str(self.device_id)
                enriched_data.append(row)

            return enriched_data
        except requests.exceptions.RequestException as e:
            return {"error": f"Could not fetch data from URL: {e}"}


class AwareDataSource(DataSource):
    device_label = models.CharField(max_length=150, unique=True, default=uuid.uuid4)
    config_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    requires_setup = True
    requires_confirmation = True

    def get_setup_url(self):
        base_url = reverse('aware_instructions', args=[self.config_token])
        return base_url
    
    def get_confirm_url(self):
        print("Getting confirm URL")
        base_url = reverse('confirm_aware_source', args=[self.id])
        print("Confirm URL:", base_url)
        return base_url

    @property
    def display_type(self):
        return "AWARE Mobile"
    
    def confirm_device(self):
        if self.status == 'active':
            return (True, "This device is already active.")

        retrieved_device_id = db_connector.get_device_id_for_label(self.device_label)

        if not retrieved_device_id:
            return (False, "No data with that device label. It may take a few hours for data to appear. Please ensure AWARE is running on your device.") 

        is_claimed = AwareDataSource.objects.filter(device_id=retrieved_device_id).exclude(id=self.id).exists()
        if is_claimed:
            return (False, "Error: This device ID has already been claimed by another user. Contact the administrator if you believe this is an error.")
        
        self.device_id = retrieved_device_id
        self.status = 'active'
        self.save()
        return (True, "AWARE device confirmed and linked successfully!")
    
    def get_data_types(self):
        """  Returns a list of available data type names for this source. """
        if self.status == 'active' and self.device_id:
            device_id_str = str(self.device_id)
            tables = db_connector.get_aware_tables(device_id_str)
            return tables if tables else []
        return []

    
    def fetch_data(self, data_type='battery', limit=10000, start_date=None, end_date=None):
        """Get's the users data from the AWARE server"""
        if self.status == 'active' and self.device_id:
            device_id_str = str(self.device_id)
            return db_connector.get_aware_data(
                device_id_str, data_type, limit, start_date, end_date
            )
        return []

