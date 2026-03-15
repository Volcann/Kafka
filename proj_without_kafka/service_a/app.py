from flask import Flask, request, jsonify
import requests
import socket
import json

app = Flask(__name__)

SERVICE_B_URL = "http://service_b:5002/analyze"
VALID_API_KEY = "super-secret-key"

def debug_event(src, dst, action, module=None):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = {"source": src, "target": dst, "action": action}
        if module:
            payload["module"] = module
        sock.sendto(json.dumps(payload).encode('utf-8'), ("host.docker.internal", 9999))
    except:
        pass

@app.route('/api/post', methods=['POST'])
def gateway_post():
    debug_event("USER", "Service_A", "REQ_OUT", module="Gateway")
    debug_event("USER", "Service_A", "REQ_IN", module="Gateway")
    
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or auth_header != f"Bearer {VALID_API_KEY}":
        debug_event("Service_A", "USER", "RESP_OUT", module="Auth Failed")
        debug_event("Service_A", "USER", "RESP_IN", module="Auth Failed")
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    
    if not data or 'text' not in data or 'user' not in data:
        debug_event("Service_A", "USER", "RESP_OUT", module="Validation Error")
        debug_event("Service_A", "USER", "RESP_IN", module="Validation Error")
        return jsonify({"error": "Invalid payload"}), 400
    
    # Forward to Service B synchronously
    try:
        debug_event("Service_A", "Service_B", "REQ_OUT", module="Forwarding")
        response = requests.post(SERVICE_B_URL, json=data, timeout=10)
        debug_event("Service_A", "Service_B", "RESP_IN", module="Forwarding")
        
        debug_event("Service_A", "USER", "RESP_OUT", module="Success")
        debug_event("Service_A", "USER", "RESP_IN", module="Success")
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        debug_event("Service_A", "USER", "RESP_OUT", module="Error")
        debug_event("Service_A", "USER", "RESP_IN", module="Error")
        return jsonify({"error": str(e), "message": "Failed to communicate with Service B"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
