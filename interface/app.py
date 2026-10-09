from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)
DB_FILE = 'database.json'

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return []

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.json
    data['timestamp'] = datetime.now().isoformat()
    
    db = load_db()
    db.append(data)
    save_db(db)
    
    return jsonify({"status": "success", "message": "Data saved locally."})

@app.route('/api/delete_user', methods=['POST'])
def delete_user():
    data = request.json
    uuid_to_delete = data.get('uuid')
    
    db = load_db()
    # Filter out any records belonging to this UUID
    db = [entry for entry in db if entry.get('user', {}).get('uuid') != uuid_to_delete]
    save_db(db)
    
    return jsonify({"status": "success", "message": f"Data for {uuid_to_delete} deleted."})

if __name__ == '__main__':
    # Run end-to-end locally on port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
