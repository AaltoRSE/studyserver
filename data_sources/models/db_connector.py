import requests
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

# AWARE Filter API configuration
AWARE_FILTER_HOST = os.getenv('AWARE_FILTER_HOST', getattr(settings, 'AWARE_FILTER_HOST', 'localhost'))
AWARE_FILTER_PORT = os.getenv('AWARE_FILTER_PORT', getattr(settings, 'AWARE_FILTER_PORT', '3446'))
AWARE_FILTER_BASE_URL = f"https://{AWARE_FILTER_HOST}:{AWARE_FILTER_PORT}"
STUDY_PASSWORD = os.getenv('STUDY_PASSWORD', getattr(settings, 'STUDY_PASSWORD', ''))

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

_cached_token = None


def _get_auth_token():
    """
    Retrieve or refresh the JWT token for API authentication.
    Caches the token for reuse.
    """
    global _cached_token
    
    if _cached_token:
        return _cached_token
    
    try:
        response = requests.post(
            f"{AWARE_FILTER_BASE_URL}/login",
            json={"password": STUDY_PASSWORD},
            verify=False
        )
        
        if response.status_code == 200:
            token_data = response.json()
            _cached_token = token_data.get('token')
            logger.info("Successfully authenticated with AWARE Filter API")
            return _cached_token
        else:
            logger.error(f"Authentication failed: {response.status_code} - {response.text}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error authenticating with AWARE Filter API: {e}")
        return None


def _get_headers():
    """Get headers with Bearer token for API requests."""
    token = _get_auth_token()
    if not token:
        return None
    
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }


def get_device_ids_for_label(device_label):
    """Gets a list of device_ids associated with the given device_label."""
    if not device_label:
        logger.warning("Invalid AWARE device label provided.")
        return []

    try:
        # Query the device_lookup table for devices matching this label
        headers = _get_headers()
        if not headers:
            logger.error("Failed to obtain authentication token")
            return []
        
        response = requests.get(
            f"{AWARE_FILTER_BASE_URL}/data",
            params={
                'table': 'device_lookup',
                'label': device_label
            },
            headers=headers,
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            device_ids = [item['device_id'] for item in data.get('data', []) 
                         if 'device_id' in item]
            logger.info(f"Retrieved {len(device_ids)} device IDs for label: {device_label}")
            return device_ids
        else:
            logger.error(f"Failed to retrieve device IDs: {response.status_code} - {response.text}")
            return []
            
    except requests.RequestException as e:
        logger.error(f"Error retrieving device IDs for label {device_label}: {e}")
        return []


def get_aware_tables(device_label):
    """Gets a list of available tables that have data for the given device_label."""
    if not device_label:
        logger.warning("Invalid AWARE device label provided.")
        return []

    device_ids = get_device_ids_for_label(device_label)
    if not device_ids:
        logger.info(f"No devices found for label: {device_label}")
        return []

    tables_with_data = []
    headers = _get_headers()
    if not headers:
        logger.error("Failed to obtain authentication token")
        return []

    try:
        # Query the tables endpoint to get available tables for these devices
        for device_id in device_ids:
            response = requests.get(
                f"{AWARE_FILTER_BASE_URL}/data",
                params={'device_id': device_id},
                headers=headers,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                tables = data.get('tables', [])
                for table in tables:
                    if table not in tables_with_data:
                        tables_with_data.append(table)
            else:
                logger.warning(f"Failed to retrieve tables for device {device_id}: {response.status_code}")

        logger.info(f"Retrieved {len(tables_with_data)} tables for label: {device_label}")
        return tables_with_data
        
    except requests.RequestException as e:
        logger.error(f"Error retrieving tables for label {device_label}: {e}")
        return []


def get_aware_data(device_label, table_name='battery', limit=1000, start_date=None, end_date=None):
    """
    Retrieves records from the AWARE Filter API for a specific device label and table.
    Returns a list of dictionaries.
    """
    if not device_label:
        logger.warning("Invalid AWARE device label provided.")
        return []

    device_ids = get_device_ids_for_label(device_label)
    if not device_ids:
        logger.warning(f"No devices found for label: {device_label}")
        return []

    headers = _get_headers()
    if not headers:
        logger.error("Failed to obtain authentication token")
        return []

    results = []

    try:
        # Query the data for each device ID
        for device_id in device_ids:
            query_params = {
                'table': table_name,
                'device_id': device_id
            }

            # Add time filters if provided
            if start_date:
                query_params['start_time'] = int(start_date.timestamp() * 1000)
            if end_date:
                query_params['end_time'] = int(end_date.timestamp() * 1000)

            # Query the data from the API using the correct endpoint
            response = requests.get(
                f"{AWARE_FILTER_BASE_URL}/data",
                params=query_params,
                headers=headers,
                verify=False
            )

            if response.status_code == 200:
                data = response.json()
                records = data.get('data', [])
                results.extend(records)
                logger.info(f"Retrieved {len(records)} records from table {table_name} for device {device_id}")
            else:
                logger.error(f"Failed to retrieve data from {table_name} for device {device_id}: {response.status_code} - {response.text}")

        # Apply limit if needed (API may not support it, so apply client-side)
        if limit:
            results = results[:limit]
        
        logger.info(f"Total: retrieved {len(results)} records from table {table_name} for device label {device_label}")
        return results

    except requests.RequestException as e:
        logger.error(f"Error retrieving data from AWARE Filter API for table {table_name}: {e}")
        return results
