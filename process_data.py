import requests
import yaml
import pyodbc
import sqlite3
from bs4 import BeautifulSoup
import urllib3
import os
import datetime
import platform

# Disable SSL certificate verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Default values for constants (will be overridden by database values if available)
DEFAULT_IMPORT_CUT_DATE = '20250101'  # Filter for befoerderungs_datum

# Set default auth file path based on OS
if platform.system() == 'Windows':
    DEFAULT_AUTH_FILE_PATH = r"C:\Users\s1504nn\auth_wpi.yml"
else:  # macOS or Linux
    DEFAULT_AUTH_FILE_PATH = os.path.expanduser("~/auth_wpi.yml")

DB_CFG_FILE = "db_cfg.yml"
BMI_URL = 'https://bmi-login.inet.bundesbank.de/bmi/MeldungList.do?value(action)=aktion.gruppe.3&value(nformat)=0'


# Function to get configuration from SQLite database
def get_config_from_db():
    try:
        conn = sqlite3.connect('bmi_data.db')
        cursor = conn.cursor()
        
        # Check if settings table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        if cursor.fetchone() is None:
            # Settings table doesn't exist yet, use defaults
            config = {
                'IMPORT_CUT_DATE': DEFAULT_IMPORT_CUT_DATE,
                'AUTH_FILE_PATH': DEFAULT_AUTH_FILE_PATH
            }
        else:
            # Read values from settings table
            cursor.execute("SELECT key, value FROM settings")
            settings = dict(cursor.fetchall())
            
            # Map settings to config keys
            config = {
                'IMPORT_CUT_DATE': settings.get('import_cut_date', '') or DEFAULT_IMPORT_CUT_DATE,
                'AUTH_FILE_PATH': settings.get('auth_file_path', '') or DEFAULT_AUTH_FILE_PATH
            }
            
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
def create_or_update_sqlite_database(bmi_dict, termin):
    try:
        conn = sqlite3.connect('bmi_data.db')
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        table_name = f"BMI{termin}"
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id1 TEXT,
            id2 TEXT PRIMARY KEY,
            melder_id TEXT,
            institutstyp TEXT,
            termin TEXT,
            datei TEXT,
            erstellt TEXT,
            typ TEXT,
            import_found INTEGER,
            rejected_import_found INTEGER,
            comment TEXT,
            ok INTEGER,
            last_updated TEXT
        )
        ''')
        
        # Insert or update records
        for id2, data in bmi_dict.items():
            # Check if record exists
            cursor.execute(f"SELECT id2 FROM {table_name} WHERE id2 = ?", (id2,))
            record = cursor.fetchone()
            
            if record:
                # Update existing record, preserving comment and ok status
                cursor.execute(f'''
                SELECT comment, ok FROM {table_name} WHERE id2 = ?
                ''', (id2,))
                existing = cursor.fetchone()
                
                if existing:
                    comment = existing[0]
                    ok = existing[1]
                else:
                    comment = ''
                    ok = 0
                
                # Update record
                cursor.execute(f'''
                UPDATE {table_name} SET
                    id1 = ?,
                    melder_id = ?,
                    institutstyp = ?,
                    termin = ?,
                    datei = ?,
                    erstellt = ?,
                    typ = ?,
                    import_found = ?,
                    rejected_import_found = ?,
                    comment = ?,
                    ok = ?,
                    last_updated = ?
                WHERE id2 = ?
                ''', (
                    data.get('id1', ''),
                    data.get('melder_id', ''),
                    data.get('institutstyp', ''),
                    data.get('termin', ''),
                    data.get('datei', ''),
                    data.get('erstellt', ''),
                    data.get('typ', ''),
                    1 if data.get('import_found', False) else 0,
                    1 if data.get('rejected_import_found', False) else 0,
                    comment,
                    ok,
                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    id2
                ))
            else:
                # Insert new record
                cursor.execute(f'''
                INSERT INTO {table_name} (
                    id1, id2, melder_id, institutstyp, termin, datei, erstellt, typ,
                    import_found, rejected_import_found, comment, ok, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data.get('id1', ''),
                    id2,
                    data.get('melder_id', ''),
                    data.get('institutstyp', ''),
                    data.get('termin', ''),
                    data.get('datei', ''),
                    data.get('erstellt', ''),
                    data.get('typ', ''),
                    1 if data.get('import_found', False) else 0,
                    1 if data.get('rejected_import_found', False) else 0,
                    data.get('comment', ''),
                    1 if data.get('ok', False) else 0,
                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
        
        conn.commit()
        conn.close()
        return True
    
    except Exception as e:
        print(f"Error creating/updating SQLite database: {e}")
        try:
            conn.close()
        except:
            pass
        return False


# Function to process BMI data for a given termin
def process_bmi_data(termin, settings=None):
    """Process BMI data for a given termin"""
    try:
        # Get configuration
        if settings is None:
            config = get_config_from_db()
        else:
            # Map from settings dict to config dict format
            config = {
                'IMPORT_CUT_DATE': settings.get('import_cut_date', '') or DEFAULT_IMPORT_CUT_DATE,
                'AUTH_FILE_PATH': settings.get('auth_file_path', '') or DEFAULT_AUTH_FILE_PATH
            }
        
        # Load authentication configuration
        auth_config = load_yaml_config(config['AUTH_FILE_PATH'])
        if not auth_config:
            print("Error: Could not load authentication configuration.")
            return False
        
        # Load database configuration
        db_config = load_yaml_config(DB_CFG_FILE)
        if not db_config:
            print("Error: Could not load database configuration.")
            return False
        
        # Fetch data from BMI website
        html_content = fetch_bmi_data(auth_config, termin)
        if not html_content:
            print("Error: Could not fetch data from BMI website.")
            return False
        
        # Parse BMI HTML response
        bmi_dict = parse_bmi_html(html_content)
        if not bmi_dict:
            print("Error: Could not parse BMI data.")
            return False
        
        # Connect to SQL Server
        sql_conn = connect_to_sql_server(db_config, auth_config)
        if not sql_conn:
            print("Error: Could not connect to SQL Server.")
            return False
        
        # Load data from SQL Server
        sql_query = f"""
        SELECT 
            p.BELEG_ID,
            p.PROTOKOLL_TYP_BEZEICHNUNG,
            CONVERT(varchar, p.BEFOERDERUNGS_DATUM, 112) as BEFOERDERUNGS_DATUM,
            CONVERT(varchar, p.ERSTELLT_AM, 112) as ERSTELLT_AM,
            p.ERSTELLT_VON,
            f.FILE_NAME,
            f.FILE_TYP
        FROM PROTOKOLL p
        LEFT JOIN PROT_FILES f ON p.BELEG_ID = f.BELEG_ID
        WHERE p.BEFOERDERUNGS_DATUM > '{config['IMPORT_CUT_DATE']}'
        """
        
        sql_data = load_sql_data(sql_conn, sql_query)
        if not sql_data:
            print("Error: Could not load data from SQL Server.")
            sql_conn.close()
            return False
        
        # Update BMI dictionary with SQL data
        for row in sql_data:
            file_name = row.get('FILE_NAME', '')
            if file_name:
                for key, entry in bmi_dict.items():
                    if file_name.lower() in entry['datei'].lower():
                        entry['import_found'] = True
                        break
        
        # Create or update SQLite database
        success = create_or_update_sqlite_database(bmi_dict, termin)
        if not success:
            print("Error: Could not update SQLite database.")
            return False
        
        print(f"Successfully processed data for termin {termin}")
        return True
    
    except Exception as e:
        print(f"Error processing BMI data: {e}")
        return False


def process_data(termin):
    # Example usage
    process_bmi_data(termin)

