# WPI Monitor Dashboard

A web application for monitoring WPI (WpInvest) data across different termins.

## Features

- Dashboard with termin selection
- Data table with sortable and filterable columns
- Quick filter for missing files
- Pagination for large datasets
- Detailed view and editing capabilities for entries
- Statistics on missing files
- Data update functionality

## Installation

1. Clone the repository
2. Install the required dependencies:

```
pip install -r requirements.txt
```

3. Ensure you have the `auth_wpi.yml` file in the correct location (as specified in main.py) with the proper credentials.

## Usage

1. Start the application:

```
python app.py
```

2. Open your browser and navigate to `http://localhost:5000`

3. Select a termin from the dropdown to view data for that period

4. Use the table filters and sorting options to find specific entries

5. Click on a row to view details and edit comments or status

6. Use the "Update Data" button to fetch the latest data for the selected termin

## Technical Details

The application consists of:

- A Flask backend that serves the API and web interface
- SQLite database for data storage
- Integration with existing WPI data processing
- Bootstrap 5 for responsive UI
- JavaScript for interactive features

## API Endpoints

- `/api/termins` - Get a list of available termins
- `/api/data/<termin>` - Get data for a specific termin with filtering and pagination
- `/api/entry/<termin>/<id2>` - Get or update details for a specific entry
- `/api/update` - Trigger data update process for a termin 