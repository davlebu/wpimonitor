import pyodbc
from pathlib import Path

root_dir = Path
import sqlite3


def create_bmi_table_statement(termin, statistics):
    with open(f'sql/{statistics}/CREATE_BMI_DATA.sql') as input:
        return input.read().replace('{termin}', termin)


def insert_bmi_data_statement(termin, statistics):
    with open(f'sql/{statistics}/INSERT_BMI_DATA.sql') as input:
        return input.read().replace('{termin}', termin)


def wpi_importe_statement(cut_date):
    with open('sql/wpi/WPI_IMPORTE.sql') as input:
        return input.read().replace('{IMPORT_CUT_DATE}', cut_date)
def emiso_importe_statement(cut_date):
    with open('sql/emiso/EMISO_IMPORTE.sql') as input:
        return input.read().replace('{IMPORT_CUT_DATE}', cut_date)

def wpi_importe_abgewiesen_statement(cut_date):
    with open('sql/wpi/WPI_IMPORTE_ABGEWIESEN.sql') as input:
        return input.read().replace('{IMPORT_CUT_DATE}', cut_date)

def emiso_importe_abgewiesen_statement(cut_date):
        with open('sql/emiso/EMISO_IMPORTE_ABGEWIESEN.sql') as input:
            return input.read().replace('{IMPORT_CUT_DATE}', cut_date)


def connect_to_sql_server(db_config, stage='PROD'):
    try:
        database = db_config['database']
        driver = db_config['driver']
        server = db_config['servers'][stage]

        # Create connection string
        conn_str = f'DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes'

        # Connect to the database
        return pyodbc.connect(conn_str)
    except Exception as e:
        print(f"Error connecting to SQL Server: {e}")
        return None


# Function to load data from SQL Server
def load_sql_data(connection, query):
    try:
        cursor = connection.cursor()
        cursor.execute(query)

        # Get column names
        columns = [column[0] for column in cursor.description]

        # Fetch all data
        results = []
        for row in cursor.fetchall():
            result = {}
            for i, value in enumerate(row):
                result[columns[i]] = value
            results.append(result)

        return results
    except Exception as e:
        print(f"Error executing SQL query: {e}")
        return []


def insert_into_bmi_table(data_dict, db_path, termin, statistics):
    """
    Insert data from a dictionary into the BMI table with parameterized query.

    Args:
        data_dict (dict): Dictionary containing the data to insert
        db_path (str): Path to the SQLite database file
    """

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(create_bmi_table_statement(termin,statistics=statistics))
        conn.commit()
        for record_id, record_data in data_dict.items():
            # Get the termin value for table name formatting
            termin = record_data.get('termin', '')

            # Format the SQL statement with the termin value
            sql_statement = insert_bmi_data_statement(termin, statistics=statistics)

            # Prepare the parameters for the SQL statement
            # Set default values for missing fields
            params = [
                '',  # abweisen_check_befund_check_beschreibung_extern
                '',  # abweisen_check_befund_check_beschreibung_kurz
                '',  # abweisen_check_befund_check_details
                '',  # abweisen_check_befund_check_gruppe
                '',  # abweisen_check_befund_check_name
                record_data.get('anwendungs_id', ''),
                record_data.get('befoerderungs_datum', ''),
                record_data.get('blz', ''),
                record_data.get('comment', ''),
                record_data.get('datei', ''),
                record_data.get('datei_id', ''),
                record_data.get('dateiname', ''),
                record_data.get('empfangszeit', ''),
                record_data.get('erstellt', ''),
                record_data.get('externe_referenz', ''),
                record_data.get('id1', ''),
                record_data.get('id2', ''),
                '',  # import_anwendungs_id
                '',  # import_befoerderungs_datum
                '',  # import_blz
                '',  # import_datei_id
                '',  # import_dateiname
                '',  # import_empfangszeit
                '',  # import_externe_referenz
                1 if record_data.get('import_found', False) else 0,
                '',  # import_melder_id
                '',  # import_melder_id_art
                '',  # import_meldetermin
                record_data.get('institutstyp', ''),
                record_data.get('last_updated', ''),
                record_data.get('melder_id_bmi', ''),
                record_data.get('melder_id_art', ''),
                record_data.get('meldetermin', ''),
                1 if record_data.get('ok', False) else 0,
                1 if record_data.get('rejected_import_found', False) else 0,
                record_data.get('termin', ''),
                record_data.get('typ', '')
            ]

            # Execute the SQL statement
            cursor.execute(sql_statement, params)

            # Commit the transaction
        conn.commit()
        print(f"Successfully inserted data for {termin} in {statistics}")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        conn.rollback()
    finally:
        conn.close()
