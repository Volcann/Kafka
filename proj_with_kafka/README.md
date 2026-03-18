# proj_with_kafka

A multi-service microservices project demonstrating an **asynchronous** sentiment analysis pipeline using **Apache Kafka**.

## Architecture

1.  **Service A (Gateway)**: Flask App on port `5000`.
    -   Validates API requests (requires `Authorization: Bearer super-secret-key`).
    -   Produces raw messages to the Kafka topic `raw-messages`.
    -   Returns `202 Accepted` immediately.
2.  **Service B (Sentiment Processor)**: Python Consumer/Producer.
    -   Consumes from `raw-messages`.
    -   Performs sentiment analysis using `TextBlob`.
    -   Persists results to a SQLite database (`/app/data/sentiments.db`).
    -   Produces analyzed results to the Kafka topic `analyzed-messages`.
3.  **Service C (Analytics Dashboard)**: Flask App on port `5003`.
    -   Consumes from `analyzed-messages`.
    -   Updates real-time statistics.
    -   Broadcasts updates to the web UI via WebSockets (SocketIO).

## Prerequisites

-   [Docker](https://www.docker.com/)
-   [Docker Compose](https://docs.docker.com/compose/)

## How to Run

1.  Navigate to the `proj_with_kafka` directory.
2.  Start the entire stack (Zookeeper, Kafka, and the 3 services):
    ```bash
    docker-compose up --build
    ```
3.  Wait for the services to initialize. Kafka and Zookeeper may take a few moments to become fully ready.

## How to Use

### 1. Open the Dashboard
Visit the real-time analytics dashboard in your browser:
`http://localhost:5003`

### 2. Send a Message
Use `curl` to send a text message to Service A. Since this is an asynchronous flow, the processing happens in the background.

```bash
curl -X POST http://localhost:5000/api/post \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer super-secret-key" \
     -d '{"user": "alice", "text": "I love using Kafka for async processing!"}'
```

### 3. Observe the Results
-   **Dashboard**: The "Happy" count on the dashboard at `http://localhost:5003` will increment.
-   **Logs**: Check the `docker-compose` logs to see the message flow through the topics.
-   **Database**: Service B stores the sentiment in its local SQLite database.

## Differences from Non-Kafka Version

Compared to `proj_without_kafka`, this version:
-   **Decouples Services**: Service A doesn't wait for Service B or C to finish.
-   **Resilience**: If Service B is down, messages are queued in Kafka and processed once it's back up.
-   **Scalability**: Kafka allows for multiple consumers and partitions to handle high loads.
