from django.db import models
from polymorphic.models import PolymorphicModel
from users.models import Profile

class DataSource(PolymorphicModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='data_sources')
    name = models.CharField(max_length=100, help_text="A personal name for this source")
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.profile.user.username})"

class JsonUrlDataSource(DataSource):
    url = models.URLField(max_length=500, help_text="The URL where the JSON data can be fetched")

