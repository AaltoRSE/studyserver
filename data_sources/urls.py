from django.urls import path
from django.urls import path, include
from . import views

urlpatterns = [
    path('add/', views.select_data_source_type, name='select_data_source_type'),
    path('add/<str:source_type>/', views.add_data_source, name='add_data_source'),
    path('<int:source_id>/delete/', views.delete_data_source, name='delete_data_source'),
    path('<int:source_id>/', views.view_data_source, name='view_data_source'),
    path('<int:source_id>/edit/', views.edit_data_source, name='edit_data_source'),
    path('instructions/<int:source_id>/', views.instructions, name='instructions'),
    path('<int:source_id>/confirm/', views.confirm_data_source, name='confirm_data_source'),
    path('config/<uuid:token>/<str:view_type>/', views.token_view_dispatcher, name='datasource_token_view'),

    path('google/', include('data_sources.urls_google_portability')),
]
