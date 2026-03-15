from flask import Flask, request, jsonify
import requests
import socket
import json
import uuid

import os

app = Flask(__name__)

SERVICE_B_URL = os.environ.get("SERVICE_B_URL", "http://service_b:5002/analyze")
DEBUGGER_HOST = os.environ.get("DEBUGGER_HOST", "host.docker.internal")
VALID_API_KEY = "super-secret-key"

def debug_event(src, dst, action, request_id="UNKNOWN", module=None):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = {"source": src, "target": dst, "action": action, "request_id": request_id}
        if module:
            payload["module"] = module
        sock.sendto(json.dumps(payload).encode('utf-8'), (DEBUGGER_HOST, 9999))
    except:
        pass

@app.route('/api/post', methods=['POST'])
def gateway_post():
    request_id = request.headers.get('X-Request-ID')
    if not request_id:
        request_id = f"REQ-{uuid.uuid4().hex[:6]}"
        
    print(f"{request_id} - Received request")
    print(f"{request_id} - Validating header")

    debug_event("USER", "Service_A", "REQ_OUT", request_id, module="Gateway")
    debug_event("USER", "Service_A", "REQ_IN", request_id, module="Gateway")

    auth_header = request.headers.get('Authorization')
    
    if not auth_header or auth_header != f"Bearer {VALID_API_KEY}":
        debug_event("Service_A", "USER", "RESP_OUT", request_id, module="Auth Failed")
        debug_event("Service_A", "USER", "RESP_IN", request_id, module="Auth Failed")
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    
    if not data or 'text' not in data or 'user' not in data:
        debug_event("Service_A", "USER", "RESP_OUT", request_id, module="Validation Error")
        debug_event("Service_A", "USER", "RESP_IN", request_id, module="Validation Error")
        return jsonify({"error": "Invalid payload"}), 400
    
    # Forward to Service B synchronously
    try:
        print(f"{request_id} - Forwarding to Service B")
        debug_event("Service_A", "Service_B", "REQ_OUT", request_id, module="Forwarding")
        headers = {'X-Request-ID': request_id}
        response = requests.post(SERVICE_B_URL, json=data, headers=headers, timeout=10)
        debug_event("Service_A", "Service_B", "RESP_IN", request_id, module="Forwarding")
        
        debug_event("Service_A", "USER", "RESP_OUT", request_id, module="Success")
        debug_event("Service_A", "USER", "RESP_IN", request_id, module="Success")
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        debug_event("Service_A", "USER", "RESP_OUT", module="Error")
        debug_event("Service_A", "USER", "RESP_IN", module="Error")
        return jsonify({"error": str(e), "message": "Failed to communicate with Service B"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
