# proj_without_kafka

A multi-service microservices project built using Python (Flask) and synchronous HTTP REST communication, to demonstrate a tightly coupled sentiment pipeline (without Kafka).

## Architecture

* **Service A (Ingestion)**: Runs on port `5000`. Receives JSON containing text, forwards it to Service B, and returns the final result.
* **Service B (Emotion)**: Runs on port `5002`. Takes text, analyzes sentiment (Happy/Sad/Angry) using `TextBlob`, forwards the emotion to Service C, and finally returns 200 OK.
* **Service C (Analytics)**: Runs on port `5003`. Receives emotion counts, updates the global dictionary, and pushes updates to a real-time web UI using SocketIO.

Because this is a **synchronous** flow, failure or latency in Service C will strictly cascade to Service B and then to Service A. 

## How to Run

Requirements:
- Docker
- Docker Compose

1. Clone or navigate to this folder.
2. Build and run the containers using Docker Compose:
```bash
docker-compose up --build
```
This will start isolated containers for `service_a`, `service_b`, and `service_c`.

## How to use

1. Open your browser and go to the real-time analytics dashboard at:
   `http://localhost:5003`

2. Open another terminal and send POST requests to Service A to inject messages:
```bash
curl -X POST http://localhost:5000/api/post \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer super-secret-key" \
     -d '{"user": "alice", "text": "I absolutely love this new feature!"}'
```

3. Send varying sentiments to see the dashboard counts increment automatically:
```bash
# Sad
curl -X POST http://localhost:5000/api/post \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer super-secret-key" \
     -d '{"user": "bob", "text": "This is terrible and boring."}'

# Angry
curl -X POST http://localhost:5000/api/post \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer super-secret-key" \
     -d '{"user": "mallory", "text": "I hate you very much!"}'
```

## Differences from Kafka Version

Compared to `proj_with_kafka`, this version:
-   **Synchronous Coupling**: Service A waits for Service B, which waits for Service C. Any failure or latency cascades immediately.
-   **No Message Durability**: If a service is down, the request fails, and data may be lost if not retried by the client.
-   **Simpler Architecture**: No need for Zookeeper or Kafka brokers, making it easier to deploy for small-scale direct communication.
