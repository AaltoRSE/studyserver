from django.db import models

from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    USER_TYPE_CHOICES = (
        ("researcher", "Researcher"),
        ("participant", "Participant"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.user_type}"
