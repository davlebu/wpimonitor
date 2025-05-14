import requests
import yaml
import pyodbc
import sqlite3
from bs4 import BeautifulSoup
import urllib3
import os
import datetime
import process_bmi
import utils
import db_utils
from utils import load_yaml_config
# Disable SSL certificate verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Constants
IMPORT_CUT_DATE = '20250101'  # Filter for befoerderungs_datum
DB_CFG_FILE = "db_cfg.yml"



def process_data(termin, statistics):
    print(f"Starting BMI data processor for termin {termin}...")



    # Load database configuration
    db_config = load_yaml_config(DB_CFG_FILE)
    if not db_config:
        print("Failed to load database configuration.")
        return

    # Get dta from BMI
    bmi_dict=process_bmi.get_bmi_data_dict(termin, statistics)

    # Connect to MS-SQL Server
    print("Connecting to MS-SQL Server...")
    sql_conn = db_utils.connect_to_sql_server(db_config, stage='PROD')
    if not sql_conn:
        print("Failed to connect to MS-SQL Server.")
        return



    importe_query=db_utils.emiso_importe_statement(IMPORT_CUT_DATE) if statistics=='emiso' else db_utils.wpi_importe_statement(IMPORT_CUT_DATE)

    importe_data = db_utils.load_sql_data(sql_conn, importe_query)
    importe_dict = {record['datei_id']: record for record in importe_data}
    print(f"Loaded {len(importe_dict)} records from wpi-importe.")

    importe_abgewiesen_query = db_utils.emiso_importe_abgewiesen_statement(IMPORT_CUT_DATE) if statistics=='emiso' else db_utils.wpi_importe_abgewiesen_statement(IMPORT_CUT_DATE)

    importe_abgewiesen_data = db_utils.load_sql_data(sql_conn, importe_abgewiesen_query)
    importe_abgewiesen_dict = {record['import_datei_id']: record for record in importe_abgewiesen_data}
    print(f"Loaded {len(importe_abgewiesen_dict)} records from wpi-importe-abgewiesen-flat.")

    sql_conn.close()

    print("Matching data between sources...")
    match_count_import = 0
    match_count_rejected = 0

    for key, value in bmi_dict.items():
        dateiname_bmi = value['datei']

        # Check if datei is in wpi_importe_dict
        if dateiname_bmi in importe_dict:
            value['import_found'] = True
            match_count_import += 1

            # Add all attributes from wpi_importe_dict
            import_record = importe_dict[dateiname_bmi]
            for attr_key, attr_value in import_record.items():
                # Convert any non-string values to strings
                if attr_value is not None and not isinstance(attr_value, str):
                    attr_value = str(attr_value)
                value[attr_key] = attr_value

        # Check if datei is in wpi_importe_abgewiesen_flat_dict
        if dateiname_bmi in importe_abgewiesen_dict:
            value['rejected_import_found'] = True
            match_count_rejected += 1

            # Add all attributes from wpi_importe_abgewiesen_flat_dict
            rejected_record = importe_abgewiesen_dict[dateiname_bmi]
            for attr_key, attr_value in rejected_record.items():
                # Convert any non-string values to strings
                if attr_value is not None and not isinstance(attr_value, str):
                    attr_value = str(attr_value)
                value[attr_key] = attr_value

    print(f"Found {match_count_import} matches in importe.")
    print(f"Found {match_count_rejected} matches in importe-abgewiesen-flat.")

    # Create or update SQLite database
    print("Creating/updating SQLite database...")
    db_utils.insert_into_bmi_table(data_dict=bmi_dict, termin=termin, db_path='bmi_data.db', statistics=statistics)
    print(f"Process completed successfully lala for termin {termin}.")

def main():
    # Example usage
    current_month = "202504"
    process_data(current_month, statistics='emiso')






if __name__ == "__main__":
    main()