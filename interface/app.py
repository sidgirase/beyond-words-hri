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

if __name__ == '__main__':
    # Run end-to-end locally on port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
