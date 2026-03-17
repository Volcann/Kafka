# Slide 1 — Title

**Introduction to Apache Kafka**
Presenter: (your name) | Duration: 45–60 min

---

# Slide 2 — Learning objectives

* Learn core Kafka concepts and terminology
* See a minimal producer → broker → consumer flow
* Run a tiny hands-on demo.

---

# Slide 3 — Terminology to understand first

Before we dive into Kafka, here are some terms you should know:
* **Monolith — everything** - in one big app. Easy to start, but hard to scale or change.
* **Microservices** — app split into smaller independent services. Each does one thing (like “Orders,”
* **Event-Driven Systems** — system reacts to things as they happen (like a new order triggers invoice generation).
* **Streaming** — continuous flow of data (like live sensor data or stock prices).
* **Decoupling** — services work independently, easier to maintain and upgrade.
* **Scalability** — system can grow for more users or data without breaking.
* **Fault Tolerance** — system keeps running even if part of it fails.

> These will help you follow the concepts without confusion.

---

# Slide 4 — System Architecture Concepts (For Everyone)

### **1️⃣ Application Architecture**

* **Monolith** — everything in one big app. Easy to start, but hard to scale or change.
* **Microservices** — app split into smaller independent services. Each does one thing (like “Orders,” “Payments,” “Chat”).

### **2️⃣ System Behavior & Reliability**

* **Decoupling** — services work independently, easier to maintain and upgrade.
* **Scalability** — system can grow for more users or data without breaking.
* **Fault Tolerance** — system keeps running even if part of it fails.

###  **2️⃣ Data Flow Concepts (For Everyone)

* **Event-Driven Systems** — system reacts to things as they happen (like a new order triggers invoice generation).
* **Streaming** — continuous flow of data (like live sensor data or stock prices).
* **Producer / Consumer** — who sends and who reads the data.

---

# Slide 4 — Why use Kafka? (short)

---

