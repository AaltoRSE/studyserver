from django.urls import path
from django.urls import path, include
from . import views

urlpatterns = [
    path('add/', views.select_data_source_type, name='select_data_source_type'),
    path('add/<str:source_type>/', views.add_data_source, name='add_data_source'),
    path('<int:source_id>/delete/', views.delete_data_source, name='delete_data_source'),
    path('<int:source_id>/', views.view_data_source, name='view_data_source'),
    path('<int:source_id>/edit/', views.edit_data_source, name='edit_data_source'),

    path('aware/', include('data_sources.urls_aware')),
    path('google/', include('data_sources.urls_google_portability')),
]
