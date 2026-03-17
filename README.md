# Apache Kafka
---

## Slide 1 — Title

**Intro to Apache Kafka**
Presenter: (your name) | 45–60 min

---

## Slide 2 — What you’ll learn (easy)

* What Kafka is and why people use it.
* How messages move: producer → broker → consumer.
* A tiny practice task you can try.

---

## Slide 3 — Easy words you should know

* **Monolith** — one big app that does everything. Simple at first, hard to change later.
* **Microservices** — many small apps, each does one job. Easier to change.
* **Event-driven** — things happen (events), and other parts react. Like a button press starting a task.
* **Streaming** — data that keeps flowing, like live sensor readings.
* **Decoupling** — parts don’t block each other. They work alone.
* **Scalability** — the system can grow without breaking.
* **Fault tolerance** — system keeps working even when some parts fail.

---

## Slide 4 — Short system idea (one-liners)

* **Monolith:** one big app. Easy start, hard to grow.
* **Microservices:** break app into small pieces. Each piece can be updated alone.
* **Decoupling:** producer sends data, consumer reads later — they don’t wait for each other.
* **Streaming:** think of data as water flowing in a pipe. Kafka stores that water so others can drink later.

---

## Slide 5 — Before Kafka: the slow chain

* Service A → Service B → Service C (synchronous).
* If B is slow, A waits. User waits.
* One failure can stop everything.
* Hard to scale just one piece.

---

## Slide 6 — Example old workflow (simple)

**Service A (Gateway)**

* Gets user request.
* Checks user.
* Waits for downstream work to finish before replying.

**Service B (Analysis & Storage)**

* Does heavy work (like AI analysis).
* Stores results.
* Sends data to next service.

**Service C (Dashboard)**

* Shows results in real time.
* Must be online for B to finish successfully.

*Key point:* everything is linked. If one part stops, others can get stuck.

---

## Slide 7 — Core Kafka concepts (plain)

* **Message / Event:** one piece of data (a single line).
* **Broker:** a Kafka server that holds messages.
* **Topic:** like a mailbox for a certain kind of message (e.g., `orders`).
* **Partition:** slices inside a topic (like several mailboxes for that topic).
* **Offset:** the message’s number in the partition (its address).
* **Producer:** the sender.
* **Consumer:** the reader.
* **Consumer group:** a team of readers that split the work.
* **Replication:** copies of data so it’s safe if one server dies.

*Analogy:* topic = mailbox, producer = person dropping mail, consumer = person reading mail.

---

## Slide 8 — Why Kafka was made (short story)

Linked to big-scale needs at LinkedIn:

* LinkedIn had millions of user events.
* They needed real-time tracking without slowing users down.
* Kafka lets systems work independently and keeps messages safe until consumers are ready.

*Short take:* Kafka = a fast, reliable pipeline for lots of events.

---

## Slide 9 — Topics and partitions (visual idea)

* Topic = stream name (e.g., `orders`).
* Partition = split for parallel work (e.g., partition 0, 1, 2).
* Ordering is kept inside each partition only.

---

## Slide 10 — Producers vs Consumers (simple)

* Producers write messages to topics.
* Consumers read from topics.
* Consumer groups share partitions so work is balanced.

---

## Slide 11 — Delivery guarantees (super short)

* **At most once:** maybe lost, but no duplicates. Fast.
* **At least once:** not lost, but may have duplicates. Safer.
* **Exactly once:** no duplicates, no loss. Best, needs extra setup.

---

## Slide 12 — How Kafka stays up (fault tolerance)

* Partitions have a leader and followers.
* Replication factor = how many copies exist (e.g., 3).
* If leader dies, a follower takes over.

---

## Slide 13 — Message storage rules

* Kafka keeps messages for a time window (retention).
* Log compaction keeps only the latest message per key (good for current state).

---

## Slide 14 — Example new workflow using Kafka (easy)

**Service A — Gateway**

* Receives request.
* Sends data to Kafka topic `raw-messages`.
* Replies quickly with `202 Accepted` so user doesn’t wait.

**Service B — Analysis**

* Reads `raw-messages` when ready.
* Does sentiment/AI work.
* Stores results and writes to `analyzed-messages`.

**Service C — Dashboard**

* Reads `analyzed-messages`.
* Updates dashboard when it wants.
* If it’s offline, it will catch up later — no data lost.

*Key point:* Services don’t block each other. Kafka buffers messages.

---

## Slide 15 — Short tips & gotchas

* Choose partitions carefully (affects order + speed).
* Use enough replication for safety.
* Watch consumer lag — it shows unread messages.
* Use keys when order per key matters.
* Be ready to handle duplicates with at-least-once.

---

## Slide 16 — When Kafka is too much

* Small apps that only need simple HTTP calls.
* Systems that must keep strict DB transactions only (Kafka complements DBs, not replace).
* When you need infinite history without planning — that’s expensive.

---

## Slide 17 — Tiny hands-on ideas (beginner)

1. Make a topic `orders` with 3 partitions. Send messages and see which partition they go to.
2. Run two consumers in the same group and watch how partitions are split between them.
3. Build a tiny app: Producer sends JSON orders → Kafka → Consumer prints them.

---

## Slide 18 — Quick glossary (one-line each)

* **Topic:** name of message stream.
* **Partition:** parallel piece of topic.
* **Offset:** message number.
* **Broker:** Kafka server.
* **Producer:** sender.
* **Consumer:** reader.

---

## Slide 19 — Resources

* Example project: Volcann/Kafka

---
