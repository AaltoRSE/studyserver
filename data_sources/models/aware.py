from django.shortcuts import render, redirect
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.http import JsonResponse
from django.contrib import messages
import qrcode
from .base import DataSource
from studies.models import Consent
from . import db_connector
import uuid
import qrcode
import io
import base64
import requests


class AwareDataSource(DataSource):
    
    device_label = models.CharField(max_length=150, unique=True, default=uuid.uuid4)
    

    requires_setup = True
    requires_confirmation = True


    def get_setup_url(self):
        base_url = reverse('instructions', args=[self.id])
        return base_url
    
    def get_confirm_url(self):
        base_url = reverse('confirm_data_source', args=[self.id])
        return base_url

    @property
    def display_type(self):
        return "AWARE Mobile Data"
    
    def get_instructions_card(self, request, consent_id=None, study_id=None):
        mobile_setup_url = request.build_absolute_uri(
            reverse(
                'datasource_token_view',
                kwargs={'token': self.config_token, 'view_type': 'setup'}
            )
        )
        qr_img = qrcode.make(mobile_setup_url)
        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        context = {
            'source': self,
            'consent_id': consent_id,
            'qr_code_image': qr_b64,
            'qr_link': mobile_setup_url,
        }
        return context, 'data_sources/aware/instructions_card.html'

    def check_for_device(self):
        if self.status == 'active':
            return (True, "This device is already active.")

        retrieved_device_ids = db_connector.get_device_ids_for_label(self.device_label)

        if not retrieved_device_ids:
            return (False, "No data with that device label. It may take a few hours for data to appear. Please ensure AWARE is running on your device.") 

        is_claimed = AwareDataSource.objects.filter(device_id__in=retrieved_device_ids).exclude(id=self.id).exclude(profile=self.profile).exists()
        if is_claimed:
            return (False, "Error: This device ID has already been claimed by another user. Contact the administrator if you believe this is an error.")
        
        self.device_id = retrieved_device_ids[0]
        self.status = 'active'
        self.save()
        return (True, "AWARE device confirmed and linked successfully!")
    
    def _process_data(self):
        result, message = self.check_for_device()
        if not result:
            print(f"Data processing error for {self}: {message}")
    
    def confirm(self, request):
        result, message = self.check_for_device()
        return result, message

    def handle_token_view(self, request, token, view_type):
        if str(self.config_token) != str(token):
            return (False, "Invalid configuration token.")

        if view_type == "setup":
            config_url = request.build_absolute_uri(
                reverse('datasource_token_view', kwargs={'token': self.config_token, 'view_type': 'config'})
            )

            context = {
                'source': self,
                'config_url': config_url,
                'device_label': self.device_label
            }
            return render(
                request,
                'data_sources/aware/mobile_setup.html',
                context
            )
        
        elif view_type == "config":
            active_consents = Consent.objects.filter(
                participant=self.profile,
                data_source_id=self.id,
                is_complete=True,
                revocation_date__isnull=True
            )
            studies = [consent.study for consent in active_consents]
            config_json = {
                "_id": "PolAlpha",
                "study_info": {
                    "study_title": "Polalpha",
                    "study_description": "Alpha study for POLWELL and POLEMIC",
                    "researcher_first": "Jarno",
                    "researcher_last": "Rantaharju",
                    "researcher_contact": "<jarno.rantaharju@aalto.fi>"
                },
                #"database": {
                #    "rootPassword": "-",
                #    "rootUsername": "-",
                #    "database_host": settings.AWARE_DB_HOST,
                #    "database_port": settings.AWARE_DB_PORT,
                #    "database_name": settings.AWARE_DB_NAME,
                #    "database_password": settings.AWARE_DB_INSERT_PASSWORD,
                #    "database_username": settings.AWARE_DB_INSERT_USER,
                #    "require_ssl": True,
                #    "config_without_password": False
                #},
                "createdAt": "",
                "updatedAt": "2025-09-25T12:30:13.411Z",
                "questions": [],
                "schedules": [],
                "sensors": [
                    {"setting": "device_label", "value": self.device_label},
                    {"setting": "status_webservice", "value": "true"},
                    {"setting": "webservice_server", "value": f"https://aware.cs.aalto.fi:3446/index.php/webservice/index/Polalpha/{settings.STUDY_PASSWORD}"},
                    {"setting": "frequency_webservice", "value": "60"},
                    {"setting": "status_battery", "value": "true"},
                    {"setting": "status_accelerometer", "value": "true"}
                ]
            }
            for study in studies:
                config_filename = study.source_configurations.get('AwareDataSource', "aware_config.json")
                base_url = study.raw_content_base_url
                if not base_url:
                    continue
                full_config_url = f"{base_url}/{config_filename}"
                try:
                    response = requests.get(full_config_url, timeout=5)
                    response.raise_for_status()
                    study_config = response.json()
                    config_json['questions'].extend(study_config.get('questions', []))
                    config_json['schedules'].extend(study_config.get('schedules', []))
                    sensors = study_config.get('sensors', [])
                    config_json['sensors'].extend(sensors)
                except requests.exceptions.RequestException:
                    continue
            return JsonResponse(config_json)

    
    def get_data_types(self):
        """  Returns a list of available data type names for this source. """
        print("Getting AWARE data types...", self.device_label)
        if self.status == 'active' and self.device_id:
            tables = db_connector.get_aware_tables(self.device_label)
            return tables if tables else []
        return []

    
    def fetch_data(self, data_type='battery', limit=None, start_date=None, end_date=None, offset=0):
        """Get's the users data from the AWARE server"""
        print("Getting AWARE data...", self.device_label)
        if self.status == 'active' and self.device_id:
            return db_connector.get_aware_data(
                self.device_label, data_type, limit, start_date, end_date, offset
            )
        return []
