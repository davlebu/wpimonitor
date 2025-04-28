import os
import sqlite3
import json
from flask import Flask, render_template, request, jsonify
from process_data import process_bmi_data, DEFAULT_IMPORT_CUT_DATE, DEFAULT_AUTH_FILE_PATH

app = Flask(__name__)

# Default settings using values from process_data.py
DEFAULT_SETTINGS = {
    'import_cut_date': DEFAULT_IMPORT_CUT_DATE,
    'auth_file_path': DEFAULT_AUTH_FILE_PATH
}

def initialize_settings():
    """Initialize the settings table if it doesn't exist"""
    conn = sqlite3.connect('bmi_data.db')
    cursor = conn.cursor()
    
    # Create settings table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    
    # Check if settings already exist
    cursor.execute("SELECT COUNT(*) FROM settings")
    count = cursor.fetchone()[0]
    
    # If no settings exist, insert defaults
    if count == 0:
        for key, value in DEFAULT_SETTINGS.items():
            cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))
    else:
        # Make sure both required settings exist
        cursor.execute("SELECT key FROM settings")
        existing_keys = [row[0] for row in cursor.fetchall()]
        
        for key, value in DEFAULT_SETTINGS.items():
            if key not in existing_keys:
                cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))
    
    conn.commit()
    conn.close()

def get_settings():
    """Get all settings from the database"""
    conn = sqlite3.connect('bmi_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    
    settings = {}
    for row in rows:
        settings[row['key']] = row['value']
    
    # Ensure all settings exist with non-empty values
    for key, default_value in DEFAULT_SETTINGS.items():
        if key not in settings or not settings[key]:
            settings[key] = default_value
    
    conn.close()
    return settings

def update_settings(new_settings):
    """Update settings in the database"""
    conn = sqlite3.connect('bmi_data.db')
    cursor = conn.cursor()
    
    for key, value in new_settings.items():
        cursor.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
    
    conn.commit()
    conn.close()
    return True

def get_termins():
    """Get all available termins from the database"""
    conn = sqlite3.connect('bmi_data.db')
    cursor = conn.cursor()
    
    # Find all tables starting with BMI, which represent termins
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'BMI%'")
    tables = cursor.fetchall()
    
    termins = []
    for table in tables:
        termin = table[0].replace('BMI', '')
        termins.append(termin)
    
    conn.close()
    return sorted(termins, reverse=True)  # Most recent first

def get_data_for_termin(termin, page=1, page_size=20, sort_by='datei', sort_order='asc', filters=None):
    """Get data for a specific termin with pagination, sorting and filtering"""
    conn = sqlite3.connect('bmi_data.db')
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()
    
    table_name = f"BMI{termin}"
    
    # Start building the query
    query = f"SELECT * FROM {table_name}"
    params = []
    
    # Apply filters if any
    if filters:
        where_clauses = []
        for column, value in filters.items():
            if column == 'import_found' and value.lower() == 'false':
                where_clauses.append(f"({column} IS NULL OR {column} = 0)")
            elif column == 'ok' and value.lower() == 'true':
                where_clauses.append(f"{column} = 1")
            elif value:
                where_clauses.append(f"{column} LIKE ?")
                params.append(f"%{value}%")
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
    
    # Apply sorting
    if sort_by:
        query += f" ORDER BY {sort_by} {sort_order}"
    
    # Add pagination
    offset = (page - 1) * page_size
    query += f" LIMIT {page_size} OFFSET {offset}"
    
    # Execute the query
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    # Convert rows to dictionaries
    result = []
    for row in rows:
        result.append({key: row[key] for key in row.keys()})
    
    # Get total count (without pagination)
    count_query = f"SELECT COUNT(*) FROM {table_name}"
    if filters and where_clauses:
        count_query += " WHERE " + " AND ".join(where_clauses)
    
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'data': result,
        'total': total_count
    }

def get_entry_details(termin, id2):
    """Get details for a specific entry"""
    conn = sqlite3.connect('bmi_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    table_name = f"BMI{termin}"
    query = f"SELECT * FROM {table_name} WHERE id2 = ?"
    
    cursor.execute(query, (id2,))
    row = cursor.fetchone()
    
    if row:
        # Convert to dictionary
        result = {key: row[key] for key in row.keys()}
    else:
        result = None
    
    conn.close()
    return result

def update_entry(termin, id2, comment, ok):
    """Update the comment and ok fields for an entry"""
    conn = sqlite3.connect('bmi_data.db')
    cursor = conn.cursor()
    
    table_name = f"BMI{termin}"
    query = f"UPDATE {table_name} SET comment = ?, ok = ? WHERE id2 = ?"
    
    cursor.execute(query, (comment, ok, id2))
    conn.commit()
    conn.close()
    
    return True

def get_termin_statistics(termin):
    """Get statistics for a termin independent of any filters"""
    conn = sqlite3.connect('bmi_data.db')
    cursor = conn.cursor()
    
    table_name = f"BMI{termin}"
    
    # Get total count
    count_query = f"SELECT COUNT(*) FROM {table_name}"
    cursor.execute(count_query)
    total_count = cursor.fetchone()[0]
    
    # Get missing files count
    missing_query = f"SELECT COUNT(*) FROM {table_name} WHERE (import_found IS NULL OR import_found = 0)"
    cursor.execute(missing_query)
    missing_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total_count,
        'missing_count': missing_count,
        'missing_percentage': round((missing_count / total_count * 100), 2) if total_count > 0 else 0
    }

@app.route('/')
def index():
    """Render the dashboard page"""
    termins = get_termins()
    return render_template('index.html', termins=termins)

@app.route('/api/termins', methods=['GET'])
def api_termins():
    """API endpoint to get all termins"""
    termins = get_termins()
    return jsonify(termins)

@app.route('/api/data/<termin>', methods=['GET'])
def api_data(termin):
    """API endpoint to get data for a specific termin"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    sort_by = request.args.get('sort_by', 'datei')
    sort_order = request.args.get('sort_order', 'asc')
    
    # Handle filters
    filters = {}
    for key in ['datei', 'timestamp', 'melder_id', 'typ']:
        if request.args.get(key):
            filters[key] = request.args.get(key)
    
    # Special filter for missing files
    if request.args.get('missing_files') == 'true':
        filters['import_found'] = 'false'
    
    # Special filter for OK status
    if request.args.get('ok') == 'true':
        filters['ok'] = 'true'
    
    data = get_data_for_termin(termin, page, page_size, sort_by, sort_order, filters)
    return jsonify(data)

@app.route('/api/entry/<termin>/<id2>', methods=['GET'])
def api_entry(termin, id2):
    """API endpoint to get details for a specific entry"""
    entry = get_entry_details(termin, id2)
    return jsonify(entry)

@app.route('/api/entry/<termin>/<id2>', methods=['PUT'])
def api_update_entry(termin, id2):
    """API endpoint to update an entry"""
    data = request.get_json()
    comment = data.get('comment', '')
    ok = data.get('ok', False)
    
    success = update_entry(termin, id2, comment, ok)
    return jsonify({'success': success})

@app.route('/api/update', methods=['POST'])
def api_update_data():
    """API endpoint to trigger data update"""
    termin = request.get_json().get('termin')
    if termin:
        # Validate termin format (YYYYMM)
        if not termin.isdigit() or len(termin) != 6:
            return jsonify({'success': False, 'error': 'Invalid termin format. Must be YYYYMM (e.g., 202405)'})
            
        try:
            # Get settings to pass to the process function
            settings = get_settings()
            process_bmi_data(termin, settings)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': False, 'error': 'No termin provided'})

@app.route('/api/statistics/<termin>', methods=['GET'])
def api_statistics(termin):
    """API endpoint to get statistics for a specific termin"""
    stats = get_termin_statistics(termin)
    return jsonify(stats)

@app.route('/settings')
def settings_page():
    """Render the settings page"""
    settings = get_settings()
    return render_template('settings.html', settings=settings)

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """API endpoint to get all settings"""
    settings = get_settings()
    return jsonify(settings)

@app.route('/api/settings', methods=['PUT'])
def api_update_settings():
    """API endpoint to update settings"""
    new_settings = request.get_json()
    success = update_settings(new_settings)
    return jsonify({'success': success})

if __name__ == '__main__':
    # Initialize settings when app starts
    initialize_settings()
    app.run(debug=True) 