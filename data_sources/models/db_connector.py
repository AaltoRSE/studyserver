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
        # Query the aware_device table for devices matching this label
        headers = _get_headers()
        if not headers:
            logger.error("Failed to obtain authentication token")
            return []
        
        response = requests.get(
            f"{AWARE_FILTER_BASE_URL}/data",
            params={
                'table': 'aware_device',
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
        # Convert device_ids to comma-separated string for single API call
        device_ids_str = ','.join(device_ids)
        
        response = requests.get(
            f"{AWARE_FILTER_BASE_URL}/tables-for-device",
            params={'device_id': device_ids_str},
            headers=headers,
            verify=False
        )
        
        if response.status_code == 200:
            result = response.json()
            for table_info in result.get('tables_with_data', []):
                table_name = table_info['table']
                if table_name not in tables_with_data:
                    tables_with_data.append(table_name)

        logger.info(f"Retrieved {len(tables_with_data)} tables for label: {device_label}")
        return tables_with_data
        
    except Exception as e:
        logger.error(f"Error retrieving tables for label {device_label}: {e}")
        return []


def get_aware_data(device_label, table_name='battery', limit=None, start_date=None, end_date=None, offset=0):
    """
    Retrieves all records from the AWARE Filter API for a specific device label and table.
    Handles pagination by making multiple requests until all data is fetched or limit is reached.
    
    Args:
        device_label (str): Device label to query
        table_name (str): Table name to query (default: 'battery')
        limit (int, optional): Maximum records to return. If None, fetches all available data (default: None)
        start_date (datetime): Filter records with timestamp >= start_date
        end_date (datetime): Filter records with timestamp <= end_date
        offset (int): Skip this many records before returning results (default: 0)
    
    Returns:
        list: Records matching the query, up to limit
    """
    if not device_label:
        logger.warning("Invalid device label provided.")
        return []

    device_ids = get_device_ids_for_label(device_label)
    if not device_ids:
        logger.warning(f"No device IDs found for label: {device_label}")
        return []

    headers = _get_headers()
    if not headers:
        logger.error("Failed to get authentication headers")
        return []

    results = []
    API_PAGE_SIZE = 10000  # Request this many records per API call
    current_offset = 0
    
    # Convert device_ids list to comma-separated string
    device_ids_str = ','.join(device_ids)

    try:
        while limit is None or len(results) < limit:
            # Calculate how many records we need to fetch
            remaining_limit = None if limit is None else limit - len(results)
            fetch_limit = min(API_PAGE_SIZE, remaining_limit) if remaining_limit is not None else API_PAGE_SIZE
            
            params = {
                'table': table_name,
                'device_id': device_ids_str,
                'limit': fetch_limit,
                'offset': current_offset
            }
            
            if start_date:
                params['start_time'] = int(start_date.timestamp() * 1000)
            if end_date:
                params['end_time'] = int(end_date.timestamp() * 1000)
            
            response = requests.get(
                f"{AWARE_FILTER_BASE_URL}/data",
                params=params,
                headers=headers,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                records = data.get('data', [])
                
                if not records:
                    break
                
                results.extend(records)
                current_offset += len(records)
                
                logger.info(f"Retrieved {len(records)} records from table {table_name} for devices {device_ids_str} at offset {current_offset}")
                
                # Check if there are more records available
                has_more = data.get('has_more', False)
                if not has_more:
                    break
                    
            else:
                logger.error(f"Error querying AWARE API for {table_name}: {response.status_code}")
                break
                
    except requests.RequestException as e:
        logger.error(f"Error fetching data from AWARE API: {e}")
        return []
    
    # Sort by timestamp to ensure consistent pagination
    if results and 'timestamp' in results[0]:
        results.sort(key=lambda x: x.get('timestamp', 0))
    
    # Apply offset and limit to the aggregated results
    start_idx = offset
    end_idx = offset + limit if limit is not None else None
    paginated_results = results[start_idx:end_idx]
    
    logger.info(f"Total: retrieved {len(paginated_results)} records from table {table_name} for device label {device_label} (offset={offset}, limit={limit}, total_available={len(results)})")
    return paginated_results

