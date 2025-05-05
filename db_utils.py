import pyodbc
from pathlib import Path
root_dir=Path
import sqlite3
def create_bmi_table_statement (termin):
    with open ('sql/CREATE_BMI_DATA.sql') as input:
        return input.read().replace('{termin}', termin)


def insert_bmi_data_statement (termin):
    with open ('sql/INSERT_BMI_DATA.sql') as input:
        return input.read().replace('{termin}', termin)

def wpi_importe_statement (cut_date):
    with open ('sql/WPI_IMPORTE.sql') as input:
        return input.read().replace('{IMPORT_CUT_DATE}', cut_date)

def wpi_importe_abgewiesen_statement (cut_date):
    with open ('sql/WPI_IMPORTE_ABGEWIESEN.sql') as input:
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


def insert_into_bmi_table(data_dict, db_path,termin):
    """
    Insert data from a dictionary into the BMI table with parameterized query.

    Args:
        data_dict (dict): Dictionary containing the data to insert
        db_path (str): Path to the SQLite database file
    """


    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(create_bmi_table_statement(termin))


    try:
        cursor.execute(create_bmi_table_statement(termin))
        conn.commit()
        print(f"Successfully inserted data into BMI{termin} table")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        conn.rollback()
    finally:
        conn.close()


