import mysql.connector
from django.conf import settings


def get_aware_tables(device_id):
    """ Gets a list of available tables that have data for the given device_id. """
    if not device_id:
        print("Invalid AWARE device ID provided.", device_id)
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
                query = f"SELECT 1 FROM `{table_name}` WHERE device_id = %s LIMIT 1"
                cursor.execute(query, (device_id,))
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



def get_aware_data(device_id, table_name='battery', limit=1000, start_date=None, end_date=None):
    """
    Connects to the AWARE DB and fetches the latest records for a specific
    AWARE device ID. Returns a list of dictionaries.
    """
    if not device_id:
        print("Invalid AWARE device ID provided.", device_id)
        return []

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
            "WHERE device_id = %s "
        )
        params = [device_id]

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

def get_device_id_for_label(device_label):
    """Finds the device_id from the 'aware_device' table using the label."""
    try:
        db_connection = mysql.connector.connect(
            host=settings.AWARE_DB_HOST,
            port=settings.AWARE_DB_PORT,
            user=settings.AWARE_DB_RO_USER,
            password=settings.AWARE_DB_RO_PASSWORD,
            database=settings.AWARE_DB_NAME
        )
        cursor = db_connection.cursor(dictionary=True)

        query = "SELECT device_id FROM aware_device WHERE label = %s LIMIT 1"
        cursor.execute(query, (device_label,))
        device_row = cursor.fetchone()

        cursor.close()
        db_connection.close()

        if device_row:
            return device_row['device_id']
        return []

    except mysql.connector.Error as e:
        print(f"Error in get_device_id_for_label: {e}")
        return []
