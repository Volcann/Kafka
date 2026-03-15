from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
import socket
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

counts = {
    "Happy": 0,
    "Sad": 0,
    "Angry": 0
}

def debug_event(src, dst, action, module=None):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = {"source": src, "target": dst, "action": action}
        if module:
            payload["module"] = module
        sock.sendto(json.dumps(payload).encode('utf-8'), ("host.docker.internal", 9999))
    except:
        pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/count', methods=['POST'])
def add_count():
    debug_event("Service_B", "Service_C", "REQ_IN", module="Dashboard")
    data = request.json
    if not data or 'emotion' not in data:
        debug_event("Service_C", "Service_B", "RESP_OUT", module="Error")
        return jsonify({"error": "No emotion provided"}), 400

    emotion = data.get('emotion')
    
    if emotion in counts:
        counts[emotion] += 1
    else:
        counts[emotion] = 1
        
    socketio.emit('update_counts', counts)
    
    debug_event("Service_C", "Service_B", "RESP_OUT", module="Success")
    return jsonify({"status": "success", "counts": counts}), 200

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5003, allow_unsafe_werkzeug=True)
