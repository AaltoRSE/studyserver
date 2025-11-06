from django.db import models
from django.urls import reverse
import qrcode
from .base import DataSource
from . import db_connector
import uuid
import qrcode
import io
import base64



class AwareDataSource(DataSource):
    
    device_label = models.CharField(max_length=150, unique=True, default=uuid.uuid4)
    config_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    requires_setup = True
    requires_confirmation = True


    def get_setup_url(self):
        base_url = reverse('aware_instructions', args=[self.id])
        return base_url
    
    def get_confirm_url(self):
        base_url = reverse('confirm_aware_source', args=[self.id])
        return base_url

    @property
    def display_type(self):
        return "AWARE Mobile Data"
    
    def get_instructions_card(self, request, consent_id=None, study_id=None):
        mobile_setup_url = request.build_absolute_uri(
            reverse(
                'aware_mobile_setup',
                kwargs={'token': self.config_token}
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
