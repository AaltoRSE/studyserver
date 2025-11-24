from django.http import FileResponse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
import os

def download_static_file(request, file_path):
    """Generic view for downloading files from STATIC_ROOT"""
    full_path = os.path.join(settings.STATIC_ROOT, file_path)
    
    # Security: prevent directory traversal
    if not os.path.abspath(full_path).startswith(os.path.abspath(settings.STATIC_ROOT)):
        messages.error(request, "Invalid file path.")
        return redirect('dashboard')
    
    if not os.path.exists(full_path):
        messages.error(request, "File not found.")
        return redirect('dashboard')
    
    filename = os.path.basename(full_path)
    response = FileResponse(open(full_path, 'rb'), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response