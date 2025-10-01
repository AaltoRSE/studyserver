import mysql.connector
from django.conf import settings


def get_aware_data(aware_device_id, table_name='battery', limit=100):
    """
    Connects to the AWARE DB and fetches the latest records for a specific
    AWARE device ID. Returns a list of dictionaries.
    """
    if not aware_device_id:
        print("Invalid AWARE device ID provided.", aware_device_id)
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
            "ORDER BY timestamp DESC LIMIT %s"
        )
        
        cursor.execute(query, (aware_device_id, limit))
        results = cursor.fetchall()

        cursor.close()
        database.close()

        return results

    except mysql.connector.Error as e:
        print(f"Error connecting to Aware database: {e}")
        return None

def get_aware_device_id_for_label(device_label):
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
        return None

    except mysql.connector.Error as e:
        print(f"Error in get_aware_device_id_for_label: {e}")
        return None
