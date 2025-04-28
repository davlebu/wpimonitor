import requests
import yaml
import pyodbc
import sqlite3
from bs4 import BeautifulSoup
import urllib3
import os
import datetime

# Disable SSL certificate verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Default values for constants (will be overridden by database values if available)
DEFAULT_IMPORT_CUT_DATE = '20250101'  # Filter for befoerderungs_datum
DEFAULT_AUTH_FILE_PATH = r"C:\Users\s1504nn\auth_wpi.yml"
DB_CFG_FILE = "db_cfg.yml"
BMI_URL = 'https://bmi-login.inet.bundesbank.de/bmi/MeldungList.do?value(action)=aktion.gruppe.3&value(nformat)=0'


# Function to get configuration from SQLite database
def get_config_from_db():
    try:
        conn = sqlite3.connect('bmi_data.db')
        cursor = conn.cursor()
        
        # Check if config table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='config'")
        if cursor.fetchone() is None:
            # Create config table if it doesn't exist
            cursor.execute('''
                CREATE TABLE config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    description TEXT,
                    last_updated TIMESTAMP
                )
            ''')
            
            # Insert default values
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("INSERT INTO config VALUES (?, ?, ?, ?)", 
                          ('IMPORT_CUT_DATE', DEFAULT_IMPORT_CUT_DATE, 'Filter date for befoerderungs_datum', now))
            cursor.execute("INSERT INTO config VALUES (?, ?, ?, ?)", 
                          ('AUTH_FILE_PATH', DEFAULT_AUTH_FILE_PATH, 'Path to authentication file', now))
            conn.commit()
            
            config = {
                'IMPORT_CUT_DATE': DEFAULT_IMPORT_CUT_DATE,
                'AUTH_FILE_PATH': DEFAULT_AUTH_FILE_PATH
            }
        else:
            # Read values from config table
            cursor.execute("SELECT key, value FROM config")
            config = dict(cursor.fetchall())
            
            # If keys don't exist, add them with default values
            if 'IMPORT_CUT_DATE' not in config:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("INSERT INTO config VALUES (?, ?, ?, ?)", 
                              ('IMPORT_CUT_DATE', DEFAULT_IMPORT_CUT_DATE, 'Filter date for befoerderungs_datum', now))
                config['IMPORT_CUT_DATE'] = DEFAULT_IMPORT_CUT_DATE
                
            if 'AUTH_FILE_PATH' not in config:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("INSERT INTO config VALUES (?, ?, ?, ?)", 
                              ('AUTH_FILE_PATH', DEFAULT_AUTH_FILE_PATH, 'Path to authentication file', now))
                config['AUTH_FILE_PATH'] = DEFAULT_AUTH_FILE_PATH
                
            conn.commit()
            
        conn.close()
        return config
    except Exception as e:
        print(f"Error reading configuration from database: {e}")
        return {
            'IMPORT_CUT_DATE': DEFAULT_IMPORT_CUT_DATE,
            'AUTH_FILE_PATH': DEFAULT_AUTH_FILE_PATH
        }


# Function to load YAML configuration
def load_yaml_config(file_path):
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading YAML file {file_path}: {e}")
        return None


# Function to fetch data from BMI website
def fetch_bmi_data(auth_config, termin):
    try:
        # Prepare auth credentials
        username = auth_config['credentials']['username']
        password = auth_config['credentials']['password']

        # Set headers similar to the request.txt
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ru,de;q=0.9,de-DE;q=0.8,en;q=0.7,en-GB;q=0.6,en-US;q=0.5',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://bmi-login.inet.bundesbank.de',
            'Referer': 'https://bmi-login.inet.bundesbank.de/bmi/MeldungFinder.do?value(action)=aktion.gruppe.2',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Microsoft Edge";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }

        # Prepare form data based on request.txt
        data = {
            'value(nisfinder)': 'true',
            'value(nismeldungkeys)': '',
            'auswahl(isachgebiet)': '14',
            'value(aelz)': '',
            'value(alieferung)': '',
            'value(ntest)': 'cb.all',
            'value(nlieferungstatus)': 'cb.all',
            'value(teingang_von)': '',
            'value(teingang_bis)': '',
            'value(nabholstatus)': 'cb.all',
            'value(ntyp_identnr)': '1',
            'value(alz)': '',
            'auswahl(itermin)': termin,  # Using the passed parameter instead of hardcoded value
            'value(ntyp)': 'cb.all',
            'value(nlistsize)': '5000'
        }

        # Make the request with BasicAuth and SSL verification disabled
        response = requests.post(
            BMI_URL,
            headers=headers,
            data=data,
            auth=(username, password),
            verify=False
        )

        if response.status_code == 200:
            return response.text
        else:
            print(f"Error fetching data: Status code {response.status_code}")
            return None

    except Exception as e:
        print(f"Error fetching BMI data: {e}")
        return None


# Function to parse HTML response
def parse_bmi_html(html_content):
    bmi_dict = {}
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find all rows in the table
        rows = soup.find_all('tr')

        for row in rows:
            # Find all cells in the row
            cells = row.find_all('td')

            # Only process rows with the correct number of cells (table data rows)
            if len(cells) == 8:  # Adjust based on the actual table structure
                try:
                    # Extract checkbox value (ID1##ID2)
                    checkbox = cells[0].find('input', type='checkbox')
                    if checkbox and 'value' in checkbox.attrs:
                        value = checkbox['value']
                        ids = value.split('##')
                        if len(ids) == 2:
                            id1 = ids[0]
                            id2 = ids[1]

                            # Extract other cell values
                            melder_id = cells[1].text.strip()
                            institutstyp = cells[2].text.strip()
                            termin = cells[3].text.strip()
                            datei = cells[4].text.strip()
                            erstellt = cells[5].text.strip()
                            typ = cells[6].text.strip()

                            # Store in dictionary with id2 as key
                            bmi_dict[id2] = {
                                'id1': id1,
                                'id2': id2,
                                'melder_id': melder_id,
                                'institutstyp': institutstyp,
                                'termin': termin,
                                'datei': datei.replace('.zip_', '.zip - '),
                                'erstellt': erstellt,
                                'typ': typ,
                                'import_found': False,
                                'rejected_import_found': False,
                                'comment': '',  # Added new column
                                'ok': False,  # Added new column
                                'last_updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Added timestamp
                            }
                except Exception as e:
                    print(f"Error parsing row: {e}")
                    continue
    except Exception as e:
        print(f"Error parsing HTML: {e}")

    return bmi_dict


# Function to connect to MS-SQL Server
def connect_to_sql_server(db_config, auth_config, stage='PROD'):
    try:
        database = db_config['database']
        driver = db_config['driver']
        server = db_config['servers'][stage]

        # Get credentials
        username = auth_config['credentials']['username']
        password = auth_config['credentials']['password']

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


# Function to create or update SQLite database
def create_or_update_sqlite_database(bmi_dict):
    try:
        # Group by termin
        termin_groups = {}
        for key, value in bmi_dict.items():
            termin = value['termin']
            if termin not in termin_groups:
                termin_groups[termin] = {}
            termin_groups[termin][key] = value

        # Connect to SQLite database
        conn = sqlite3.connect('bmi_data.db')
        cursor = conn.cursor()

        # Process each termin group
        for termin, data in termin_groups.items():
            if not data:
                continue

            table_name = f"BMI{termin}"

            # Get all columns from all records to ensure we cover everything
            all_columns = set()
            for record in data.values():
                all_columns.update(record.keys())

            # Ensure specific columns mentioned in the requirements are included
            required_columns = ['id2', 'datei_id', 'import_datei_id', 'abweisen_check_befund_check_beschreibung_kurz',
                                'import_found', 'rejected_import_found', 'comment', 'ok', 'last_updated']
            for col in required_columns:
                if col not in all_columns:
                    all_columns.add(col)

            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            table_exists = cursor.fetchone() is not None

            if not table_exists:
                # Prepare column definitions for new table
                column_defs = []
                for col in sorted(all_columns):  # Sort for consistent order
                    if col == 'id2':
                        column_defs.append(f'"{col}" TEXT PRIMARY KEY')
                    elif col in ['import_found', 'rejected_import_found', 'ok']:
                        column_defs.append(f'"{col}" BOOLEAN')
                    else:
                        column_defs.append(f'"{col}" TEXT')

                # Create table
                create_table_sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
                cursor.execute(create_table_sql)
                print(f"Created new table {table_name}")
            else:
                # Table exists, check and add any missing columns
                cursor.execute(f"PRAGMA table_info({table_name})")
                existing_columns = {row[1] for row in cursor.fetchall()}

                for col in all_columns:
                    if col not in existing_columns:
                        # Determine column type
                        col_type = "BOOLEAN" if col in ['import_found', 'rejected_import_found', 'ok'] else "TEXT"
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN \"{col}\" {col_type}")
                        print(f"Added column {col} to table {table_name}")

            # Insert or update data
            for record in data.values():
                # Ensure all columns are present in the record
                for col in all_columns:
                    if col not in record:
                        record[col] = None

                # Check if record exists
                cursor.execute(f"SELECT * FROM {table_name} WHERE id2=?", (record['id2'],))
                existing_record = cursor.fetchone()

                if existing_record:
                    # Record exists, get column names
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    column_info = cursor.fetchall()
                    column_names = [info[1] for info in column_info]

                    # Create a dictionary of the existing record
                    existing_dict = {}
                    for i, col in enumerate(column_names):
                        existing_dict[col] = existing_record[i]

                    # Check if data has changed
                    data_changed = False
                    update_cols = []
                    update_vals = []

                    for col in sorted(all_columns):
                        if col in ['comment', 'ok']:  # Skip user-editable fields
                            continue

                        # Convert to string for comparison
                        new_val = record.get(col)
                        if new_val is not None and not isinstance(new_val, str):
                            new_val = str(new_val)

                        old_val = existing_dict.get(col)
                        if old_val is not None and not isinstance(old_val, str):
                            old_val = str(old_val)

                        if new_val != old_val:
                            data_changed = True
                            update_cols.append(col)
                            update_vals.append(new_val)

                    if data_changed:
                        # Update timestamp when data changes
                        update_cols.append('last_updated')
                        update_vals.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                        # Create update SQL
                        update_sql = f"UPDATE {table_name} SET " + ", ".join(
                            [f"\"{col}\"=?" for col in update_cols]) + " WHERE id2=?"
                        update_vals.append(record['id2'])
                        cursor.execute(update_sql, update_vals)
                        print(f"Updated record {record['id2']} in table {table_name}")
                else:
                    # Insert new record
                    placeholders = ', '.join(['?' for _ in all_columns])
                    column_names = ', '.join([f'"{col}"' for col in sorted(all_columns)])
                    values = [record.get(col) for col in sorted(all_columns)]

                    insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
                    cursor.execute(insert_sql, values)
                    print(f"Inserted new record {record['id2']} into table {table_name}")

        # Commit changes and close connection
        conn.commit()
        conn.close()

        print("SQLite database updated successfully.")
    except Exception as e:
        print(f"Error creating/updating SQLite database: {e}")


# Function to process BMI data for a specific termin
def process_bmi_data(termin):
    print(f"Starting BMI data processor for termin {termin}...")

    # Get configuration from database
    config = get_config_from_db()
    IMPORT_CUT_DATE = config.get('IMPORT_CUT_DATE', DEFAULT_IMPORT_CUT_DATE)
    AUTH_FILE_PATH = config.get('AUTH_FILE_PATH', DEFAULT_AUTH_FILE_PATH)
    
    print(f"Using IMPORT_CUT_DATE: {IMPORT_CUT_DATE}")
    print(f"Using AUTH_FILE_PATH: {AUTH_FILE_PATH}")

    # Load auth configuration
    auth_config = load_yaml_config(AUTH_FILE_PATH)
    if not auth_config:
        print("Failed to load authentication configuration.")
        return

    # Load database configuration
    db_config = load_yaml_config(DB_CFG_FILE)
    if not db_config:
        print("Failed to load database configuration.")
        return

    # Fetch data from BMI website
    print(f"Fetching data from BMI website for termin {termin}...")
    html_content = fetch_bmi_data(auth_config, termin)
    if not html_content:
        print("Failed to fetch data from BMI website.")
        # For testing purposes, try loading from a file
        try:
            with open('response.html', 'r', encoding='utf-8') as file:
                html_content = file.read()
                print("Loaded HTML from response.html for testing.")
        except Exception as e:
            print(f"Could not load response.html: {e}")
            return

    # Parse HTML response
    print("Parsing HTML response...")
    bmi_dict = parse_bmi_html(html_content)
    if not bmi_dict:
        print("No data found in HTML response.")
        return
    print(f"Found {len(bmi_dict)} entries in BMI data.")

    # Connect to MS-SQL Server
    print("Connecting to MS-SQL Server...")
    sql_conn = connect_to_sql_server(db_config, auth_config, stage='PROD')
    if not sql_conn:
        print("Failed to connect to MS-SQL Server.")
        return

    # Load data from SQL queries
    print(f"Executing SQL queries with cutoff date {IMPORT_CUT_DATE}...")

    # Execute wpi-importe.sql
    wpi_importe_query = f"""
    SELECT [anwendungs_id]
          ,[blz]
          ,[befoerderungs_datum]
          ,[externe_referenz]
          ,[datei_id]
          ,[empfangszeit]
          ,[dateiname]
          ,[meldetermin]
          ,[melder_id]
          ,[melder_id_art]
      FROM [REPORTING].[dbo].[wpi-importe]
    WHERE befoerderungs_datum > {IMPORT_CUT_DATE}
    """

    wpi_importe_data = load_sql_data(sql_conn, wpi_importe_query)
    wpi_importe_dict = {record['datei_id']: record for record in wpi_importe_data}
    print(f"Loaded {len(wpi_importe_dict)} records from wpi-importe.")

    # Execute wpi-importe-abgewiesen-flat.sql
    wpi_importe_abgewiesen_query = f"""
    SELECT [meldetermin]
          ,[melder_id_art]
          ,[melder_id]
          ,[import_anwendungs_id]
          ,[import_blz]
          ,[import_befoerderungs_datum]
          ,[import_externe_referenz]
          ,[import_datei_id]
          ,[import_empfangszeit]
          ,[import_dateiname]
          ,[abweisen_check_befund_check_name]
          ,[abweisen_check_befund_check_gruppe]
          ,[abweisen_check_befund_check_beschreibung_kurz]
          ,[abweisen_check_befund_check_beschreibung_extern]
          ,[abweisen_check_befund_check_details]
          ,[import_meldetermin]
          ,[import_melder_id_art]
          ,[import_melder_id]
      FROM [REPORTING].[dbo].[wpi-importe-abgewiesen-flat]
      WHERE import_befoerderungs_datum > '{IMPORT_CUT_DATE}'
    """

    wpi_importe_abgewiesen_data = load_sql_data(sql_conn, wpi_importe_abgewiesen_query)
    wpi_importe_abgewiesen_flat_dict = {record['import_datei_id']: record for record in wpi_importe_abgewiesen_data}
    print(f"Loaded {len(wpi_importe_abgewiesen_flat_dict)} records from wpi-importe-abgewiesen-flat.")

    # Close SQL connection
    sql_conn.close()

    # Match data and update bmi_dict
    print("Matching data between sources...")
    match_count_import = 0
    match_count_rejected = 0

    for key, value in bmi_dict.items():
        datei = value['datei']

        # Check if datei is in wpi_importe_dict
        if datei in wpi_importe_dict:
            value['import_found'] = True
            match_count_import += 1

            # Add all attributes from wpi_importe_dict
            import_record = wpi_importe_dict[datei]
            for attr_key, attr_value in import_record.items():
                # Convert any non-string values to strings
                if attr_value is not None and not isinstance(attr_value, str):
                    attr_value = str(attr_value)
                value[attr_key] = attr_value

        # Check if datei is in wpi_importe_abgewiesen_flat_dict
        if datei in wpi_importe_abgewiesen_flat_dict:
            value['rejected_import_found'] = True
            match_count_rejected += 1

            # Add all attributes from wpi_importe_abgewiesen_flat_dict
            rejected_record = wpi_importe_abgewiesen_flat_dict[datei]
            for attr_key, attr_value in rejected_record.items():
                # Convert any non-string values to strings
                if attr_value is not None and not isinstance(attr_value, str):
                    attr_value = str(attr_value)
                value[attr_key] = attr_value

    print(f"Found {match_count_import} matches in wpi-importe.")
    print(f"Found {match_count_rejected} matches in wpi-importe-abgewiesen-flat.")

    # Create or update SQLite database
    print("Creating/updating SQLite database...")
    create_or_update_sqlite_database(bmi_dict)

    print(f"Process completed successfully for termin {termin}.")


def process_data(termin):
    # Example usage
    process_bmi_data(termin)

