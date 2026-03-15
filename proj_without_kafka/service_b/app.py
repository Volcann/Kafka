from flask import Flask, request, jsonify
import requests
from textblob import TextBlob
import socket
import json
import sqlite3
import os
import time

app = Flask(__name__)

SERVICE_C_URL = os.environ.get("SERVICE_C_URL", "http://service_c:5003/count")
DEBUGGER_HOST = os.environ.get("DEBUGGER_HOST", "host.docker.internal")
DB_FILE = "sentiments.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sentiments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, text TEXT, emotion TEXT)''')
    conn.commit()
    conn.close()

def debug_event(src, dst, action, request_id="UNKNOWN", module=None):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = {"source": src, "target": dst, "action": action, "request_id": request_id}
        if module:
            payload["module"] = module
        sock.sendto(json.dumps(payload).encode('utf-8'), (DEBUGGER_HOST, 9999))
    except:
        pass

@app.route('/analyze', methods=['POST'])
def analyze():
    request_id = request.headers.get('X-Request-ID', 'REQ-UNKNOWN')
    print(f"{request_id} - Running sentiment analysis")

    debug_event("Service_A", "Service_B", "REQ_IN", request_id, module="Sentiment Analysis")
    data = request.json
    if not data or 'text' not in data:
        debug_event("Service_B", "Service_A", "RESP_OUT", request_id, module="Error")
        return jsonify({"error": "No text provided"}), 400

    text = data.get('text', '')
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0.1:
        emotion = "Happy"
    elif polarity < -0.1:
        emotion = "Angry"
    else:
        emotion = "Sad" 
    
    data['emotion'] = emotion
    
    if emotion == "Angry":
        debug_event("Service_B", "Service_B", "PROCESSING", request_id, module="Alerting")
        print(f"ALERT! Received an angry message from {data.get('user', 'Unknown')}")
        time.sleep(3)
            
    try:
        print(f"{request_id} - Saving to database")
        debug_event("Service_B", "Service_B", "PROCESSING", request_id, module="DB Storage")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO sentiments (user, text, emotion) VALUES (?, ?, ?)",
                  (data.get('user', 'Unknown'), data.get('text', ''), data['emotion']))
        conn.commit()
        conn.close()
    except Exception as e:
        debug_event("Service_B", "Service_A", "RESP_OUT", request_id, module="DB Error")
        return jsonify({"error": str(e), "message": "Database error"}), 500

    try:
        print(f"{request_id} - Sending result to Service C")
        debug_event("Service_B", "Service_C", "REQ_OUT", request_id, module="Dashboard Update")
        headers = {'X-Request-ID': request_id}
        response = requests.post(SERVICE_C_URL, json={'emotion': emotion}, headers=headers, timeout=10)
        debug_event("Service_B", "Service_C", "RESP_IN", request_id, module="Dashboard Update")
        
        debug_event("Service_B", "Service_A", "RESP_OUT", request_id, module="Success")
        return jsonify(data), 200
    except requests.exceptions.RequestException as e:
        debug_event("Service_B", "Service_A", "RESP_OUT", request_id, module="Error")
        return jsonify({"error": str(e), "message": "Failed to communicate with Service C"}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5002)
