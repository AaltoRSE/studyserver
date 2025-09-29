import requests
from django.db import models
from polymorphic.models import PolymorphicModel
from users.models import Profile

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
        """ The user-friendly name for this specific data source type """
        return "JSON URL"

    def fetch_data(self):
        """Fetches and returns the JSON data from the source URL."""
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Could not fetch data from URL: {e}"}

