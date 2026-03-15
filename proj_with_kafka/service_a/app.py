from flask import Flask, request, jsonify
import socket
import json
import uuid
import os
from confluent_kafka import Producer

app = Flask(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DEBUGGER_HOST = os.environ.get("DEBUGGER_HOST", "host.docker.internal")
VALID_API_KEY = "super-secret-key"

# Kafka Producer Configuration
conf = {'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS}
producer = Producer(conf)

def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

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
    
    # Forward to Service B via Kafka
    try:
        print(f"{request_id} - Producing to Kafka topic 'raw-messages'")
        debug_event("Service_A", "Broker", "REQ_OUT", request_id, module="Kafka Produce")
        
        message = {
            "request_id": request_id,
            "data": data
        }
        
        producer.produce('raw-messages', key=request_id, value=json.dumps(message), callback=delivery_report)
        producer.poll(0) # Serve delivery reports
        
        # In an async flow, we might not wait for the response to return to the user immediately
        # but for this teaching tool, we'll return a 202 Accepted.
        
        debug_event("Service_A", "USER", "RESP_OUT", request_id, module="Accepted")
        debug_event("Service_A", "USER", "RESP_IN", request_id, module="Accepted")
        
        return jsonify({"status": "Accepted", "request_id": request_id}), 202
        
    except Exception as e:
        debug_event("Service_A", "USER", "RESP_OUT", request_id, module="Error")
        debug_event("Service_A", "USER", "RESP_IN", request_id, module="Error")
        return jsonify({"error": str(e), "message": "Failed to produce to Kafka"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
