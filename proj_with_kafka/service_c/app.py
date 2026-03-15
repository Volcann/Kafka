from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import socket
import json
import os
import threading
from confluent_kafka import Consumer, KafkaError

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
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

def kafka_consumer_thread():
    consumer_conf = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'dashboard-group',
        'auto.offset.reset': 'earliest'
    }
    
    consumer = Consumer(consumer_conf)
    consumer.subscribe(['analyzed-messages'])
    
    print("Service C Kafka thread started, consuming from 'analyzed-messages'...")
    
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"Kafka error: {msg.error()}")
                    break
            
            val = json.loads(msg.value().decode('utf-8'))
            request_id = val.get('request_id', 'UNKNOWN')
            emotion = val.get('emotion')
            
            print(f"{request_id} - Received analyzed message")
            debug_event("Broker", "Service_C", "REQ_IN", request_id, module="Kafka Consume Result")
            
            if emotion in counts:
                counts[emotion] += 1
            else:
                counts[emotion] = 1
                
            print(f"{request_id} - Broadcasting WebSocket update")
            socketio.emit('update_counts', counts)
            
            debug_event("Service_C", "Broker", "RESP_OUT", request_id, module="Dashboard Update")

    except Exception as e:
        print(f"Error in Kafka consumer thread: {e}")
    finally:
        consumer.close()

if __name__ == '__main__':
    # Start Kafka consumer in a background thread
    threading.Thread(target=kafka_consumer_thread, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5003, allow_unsafe_werkzeug=True)
