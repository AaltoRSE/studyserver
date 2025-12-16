import mysql.connector
from django.conf import settings


def get_device_ids_for_label(device_label):
    """Gets a list of device_ids associated with the given device_label."""
    if not device_label:
        print("Invalid AWARE device label provided.", device_label)
        return []

    device_ids = []
    try:
        database = mysql.connector.connect(
            host=settings.AWARE_DB_HOST,
            port=settings.AWARE_DB_PORT,
            user=settings.AWARE_DB_RO_USER,
            password=settings.AWARE_DB_RO_PASSWORD,
            database=settings.AWARE_DB_NAME
        )
        cursor = database.cursor()

        query = "SELECT device_id FROM aware_device WHERE label = %s"
        cursor.execute(query, (device_label,))
        rows = cursor.fetchall()
        device_ids = [row[0] for row in rows]

        cursor.close()
        database.close()
        return device_ids

    except mysql.connector.Error as e:
        print(f"Error in get_device_ids_for_label: {e}")
        return []


def get_aware_tables(device_label):
    """ Gets a list of available tables that have data for the given device_label. """
    if not device_label:
        print("Invalid AWARE device label provided.", device_label)
        return []
    
    device_ids = get_device_ids_for_label(device_label)
    if not device_ids:
        return []

    tables_with_data = []
    try:
        database = mysql.connector.connect(
            host=settings.AWARE_DB_HOST,
            port=settings.AWARE_DB_PORT,
            user=settings.AWARE_DB_RO_USER,
            password=settings.AWARE_DB_RO_PASSWORD,
            database=settings.AWARE_DB_NAME
        )
        cursor = database.cursor()

        cursor.execute("SHOW TABLES")
        all_tables = [table[0] for table in cursor.fetchall()]
        for table_name in all_tables:
            try:
                query = f"SELECT 1 FROM `{table_name}` WHERE device_id IN ({','.join(['%s'] * len(device_ids))}) LIMIT 1"
                cursor.execute(query, tuple(device_ids))
                if cursor.fetchone():
                    tables_with_data.append(table_name)

            except mysql.connector.Error:
                # The table might not have a device_id column, skip it
                continue

        cursor.close()
        database.close()
        return tables_with_data

    except mysql.connector.Error as e:
        print(f"Error in get_aware_tables: {e}")
        return []



def get_aware_data(device_label, table_name='battery', limit=1000, start_date=None, end_date=None):
    """
    Connects to the AWARE DB and fetches the latest records for a specific
    AWARE device ID. Returns a list of dictionaries.
    """
    if not device_label:
        print("Invalid AWARE device label provided.", device_label)
        return []
    
    device_ids = get_device_ids_for_label(device_label)

    try:
        database = mysql.connector.connect(
            host=settings.AWARE_DB_HOST,
            port=settings.AWARE_DB_PORT,
            user=settings.AWARE_DB_RO_USER,
            password=settings.AWARE_DB_RO_PASSWORD,
            database=settings.AWARE_DB_NAME
        )
        cursor = database.cursor(dictionary=True)

        # Use a parameterized query to prevent SQL injection
        query = (
            f"SELECT * FROM {table_name} "
            "WHERE device_id IN (" + ",".join(["%s"] * len(device_ids)) + ") "
        )
        params = list(device_ids)

        if start_date:
            query += " AND timestamp >= %s"
            # AWARE timestamps are in milliseconds (13 digits)
            params.append(start_date.timestamp() * 1000) 
        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date.timestamp() * 1000)
        
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, tuple(params))
        results = cursor.fetchall()

        cursor.close()
        database.close()

        return results

    except mysql.connector.Error as e:
        print(f"Error connecting to Aware database: {e}")
        return []
