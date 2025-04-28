import os
import sqlite3
import json
from flask import Flask, render_template, request, jsonify
from process_data import process_bmi_data, get_config_from_db
import datetime

app = Flask(__name__)

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
        try:
            process_bmi_data(termin)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': False, 'error': 'No termin provided'})

@app.route('/api/statistics/<termin>', methods=['GET'])
def api_statistics(termin):
    """API endpoint to get statistics for a specific termin"""
    stats = get_termin_statistics(termin)
    return jsonify(stats)

@app.route('/api/config', methods=['GET'])
def api_get_config():
    """API endpoint to get configuration values"""
    config = get_config_from_db()
    return jsonify(config)

@app.route('/api/config/<key>', methods=['PUT'])
def api_update_config(key):
    """API endpoint to update a configuration value"""
    try:
        data = request.get_json()
        value = data.get('value')
        
        if not value:
            return jsonify({'success': False, 'error': 'No value provided'})
        
        conn = sqlite3.connect('bmi_data.db')
        cursor = conn.cursor()
        
        # Check if key exists
        cursor.execute("SELECT key FROM config WHERE key = ?", (key,))
        if cursor.fetchone() is None:
            return jsonify({'success': False, 'error': f'Configuration key {key} not found'})
        
        # Update the value
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("UPDATE config SET value = ?, last_updated = ? WHERE key = ?", 
                      (value, now, key))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True) 