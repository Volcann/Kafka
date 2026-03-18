# Kafka vs synchronous HTTP Python Microservices

This repository contains two versions of a sentiment analysis microservices pipeline to demonstrate the differences between synchronous HTTP communication and asynchronous message-driven architecture using Apache Kafka.

## Project Structure

### 1. [proj_without_kafka](./proj_without_kafka)
A synchronous implementation where services communicate directly via HTTP REST.
- **Pros**: Simpler setup, lower overhead for low traffic.
- **Cons**: Tightly coupled, cascading failures, no built-in message queuing.

### 2. [proj_with_kafka](./proj_with_kafka)
An asynchronous implementation using Apache Kafka as a message broker.
- **Pros**: Loosely coupled, resilient to service downtime, highly scalable.
- **Cons**: More complex infrastructure (requires Zookeeper/Kafka).

---

## Getting Started

Each project has its own `docker-compose.yml` and detailed `README.md`.

- To try the **Synchronous** version:
  ```bash
  cd proj_without_kafka
  docker-compose up --build
  ```

- To try the **Asynchronous (Kafka)** version:
  ```bash
  cd proj_with_kafka
  docker-compose up --build
  ```

## Shared Architecture

Both projects consist of three main services:
- **Service A (Gateway)**: Receives user text via a POST API.
- **Service B (Processor)**: Analyzes sentiment (Happy/Sad/Angry) using TextBlob.
- **Service C (Dashboard)**: Displays real-time counts via a Web UI (WebSockets).
