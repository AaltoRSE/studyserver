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
            is_transformed = table_name.endswith("_transformed")
            column_to_check = "device_uid" if is_transformed else "device_id"

            if is_transformed:
                try:
                    table_name_without_suffix = table_name.replace("_transformed", "")
                    device_id_format = ",".join(["%s"] * len(device_ids))
                    query_string = f"SELECT id FROM device_lookup WHERE device_uuid IN ({device_id_format})"
                    cursor.execute(
                        query_string,
                        tuple(device_ids)
                    )

                    rows = cursor.fetchall()
                    device_uids = [row[0] for row in rows if isinstance(row, tuple) and len(row) > 0]
                    print(device_ids, device_uids)
                    if not device_uids:
                        continue

                    device_uid_format = ",".join(["%s"] * len(device_uids))
                    query = f"SELECT 1 FROM `{table_name}` WHERE {column_to_check} IN ({device_uid_format}) LIMIT 1"
                    cursor.execute(query, tuple(device_uids))

                    if cursor.fetchone():
                        tables_with_data.append(table_name_without_suffix)

                except mysql.connector.Error:
                    continue
                    
            else:
                try:
                    query = f"SELECT 1 FROM `{table_name}` WHERE {column_to_check} IN ({','.join(['%s'] * len(device_ids))}) LIMIT 1"
                    cursor.execute(query, tuple(device_ids))

                    if cursor.fetchone():
                        tables_with_data.append(table_name)

                except mysql.connector.Error:
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
    results = []

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

        if table_name not in all_tables and f"{table_name}_transformed" not in all_tables:
            print(f"Table {table_name} does not exist in AWARE database.")
            return []
        cursor.close()

        cursor = database.cursor(dictionary=True)
        # Query the original table
        query = (
            f"SELECT * FROM {table_name} "
            f"WHERE device_id IN ({','.join(['%s'] * len(device_ids))}) "
        )
        params = list(device_ids)

        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date.timestamp() * 1000) 
        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date.timestamp() * 1000)

        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, tuple(params))
        results.extend(cursor.fetchall())

        # Query the transformed table
        transformed_table_name = f"{table_name}_transformed"
        device_id_format = ",".join(["%s"] * len(device_ids))
        query_string = f"SELECT id FROM device_lookup WHERE device_uuid IN ({device_id_format})"
        cursor.execute(
            query_string,
            tuple(device_ids)
        )
        rows = cursor.fetchall()
        device_uids = [row['id'] for row in rows if isinstance(row, dict) and len(row) > 0]

        if device_uids:
            query = (
                f"SELECT * FROM {transformed_table_name} "
                f"WHERE device_uid IN ({','.join(['%s'] * len(device_uids))}) "
            )
            params = list(device_uids)

            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date.timestamp() * 1000) 
            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date.timestamp() * 1000)

            query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, tuple(params))
            results.extend(cursor.fetchall())

        cursor.close()
        database.close()

        return results

    except mysql.connector.Error as e:
        print(f"Error connecting to Aware database: {e}")
        return results
