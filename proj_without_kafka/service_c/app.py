from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
import socket
import json

import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

DEBUGGER_HOST = os.environ.get("DEBUGGER_HOST", "host.docker.internal")

counts = {
    "Happy": 0,
    "Sad": 0,
    "Angry": 0
}

def debug_event(src, dst, action, request_id="UNKNOWN", module=None):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = {"source": src, "target": dst, "action": action, "request_id": request_id}
        if module:
            payload["module"] = module
        sock.sendto(json.dumps(payload).encode('utf-8'), (DEBUGGER_HOST, 9999))
    except:
        pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/count', methods=['POST'])
def add_count():
    request_id = request.headers.get('X-Request-ID', 'REQ-UNKNOWN')
    print(f"{request_id} - Updating counters")

    debug_event("Service_B", "Service_C", "REQ_IN", request_id, module="Dashboard")
    data = request.json
    if not data or 'emotion' not in data:
        debug_event("Service_C", "Service_B", "RESP_OUT", request_id, module="Error")
        return jsonify({"error": "No emotion provided"}), 400

    emotion = data.get('emotion')
    
    if emotion in counts:
        counts[emotion] += 1
    else:
        counts[emotion] = 1
        
    print(f"{request_id} - Broadcasting WebSocket update")
    socketio.emit('update_counts', counts)
    
    debug_event("Service_C", "Service_B", "RESP_OUT", request_id, module="Success")
    return jsonify({"status": "success", "counts": counts}), 200

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5003, allow_unsafe_werkzeug=True)
