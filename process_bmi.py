import requests
from bs4 import BeautifulSoup
import datetime
import utils

BMI_URL = 'https://bmi-login.inet.bundesbank.de/bmi/MeldungList.do?value(action)=aktion.gruppe.3&value(nformat)=0'
AUTH_FILE_PATH = r"C:\Users\s1504nn\auth_wpi.yml"

def fetch_bmi_data(termin,sachgebiet):
    auth_config = utils.load_yaml_config(AUTH_FILE_PATH)
    if not auth_config:
        print("Failed to load authentication configuration.")
        return
    try:
        username = auth_config['credentials']['username']
        password = auth_config['credentials']['password']

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
            'auswahl(isachgebiet)': sachgebiet,
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
                                'melder_id_bmi': melder_id,
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

def get_bmi_data_dict(termin, statistics):


    sachgebiet= '14' if statistics=='wpi' else '17'
    print(f"Fetching data from BMI website for termin {termin}...")
    html_content = fetch_bmi_data(termin, sachgebiet=sachgebiet)
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
    return bmi_dict