from django.urls import path
from . import views

urlpatterns = [
    path('add/json/', views.add_json_source, name='add_json_source'),
]