import json
import socket
import sqlite3
import os
import time
from textblob import TextBlob
from confluent_kafka import Consumer, Producer, KafkaError

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DEBUGGER_HOST = os.environ.get("DEBUGGER_HOST", "host.docker.internal")
DB_FILE = "/app/data/sentiments.db"

# Kafka Configuration
consumer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'sentiment-analysis-group',
    'auto.offset.reset': 'earliest'
}

producer_conf = {'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS}

def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
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

def process_message(msg, producer):
    try:
        val = json.loads(msg.value().decode('utf-8'))
        request_id = val.get('request_id', 'UNKNOWN')
        data = val.get('data', {})
        
        print(f"{request_id} - Received from Kafka")
        debug_event("Broker", "Service_B", "REQ_IN", request_id, module="Kafka Consume")

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
            time.sleep(1) # Reduced sleep for demo
                
        # Save to DB
        debug_event("Service_B", "Service_B", "PROCESSING", request_id, module="DB Storage")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO sentiments (user, text, emotion) VALUES (?, ?, ?)",
                  (data.get('user', 'Unknown'), data.get('text', ''), data['emotion']))
        conn.commit()
        conn.close()

        # Produce to analyzed-messages
        print(f"{request_id} - Producing to 'analyzed-messages'")
        debug_event("Service_B", "Broker", "REQ_OUT", request_id, module="Kafka Produce Result")
        
        result_msg = {
            "request_id": request_id,
            "emotion": emotion,
            "user": data.get('user', 'Unknown')
        }
        producer.produce('analyzed-messages', key=request_id, value=json.dumps(result_msg))
        producer.poll(0)

    except Exception as e:
        print(f"Error processing message: {e}")

def main():
    init_db()
    
    consumer = Consumer(consumer_conf)
    producer = Producer(producer_conf)
    
    consumer.subscribe(['raw-messages'])
    
    print("Service B started, consuming from 'raw-messages'...")
    
    try:
        while True:
            msg = consumer.poll(1.0)
            
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                elif msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                    print(f"Topic not ready yet: {msg.error()}")
                    time.sleep(2)
                    continue
                else:
                    print(f"Kafka error: {msg.error()}")
                    break
            
            process_message(msg, producer)
            
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()

if __name__ == '__main__':
    main()
