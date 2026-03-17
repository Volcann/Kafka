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

## Slide 8 — Why Kafka Was Made

* LinkedIn had tons of user actions every second.
* They needed a way to track them in real time without slowing things down.
* Kafka stores messages safely and lets different systems work independently.
  * Clicking “Like” on a post
  * Sending a message to a connection
  * Updating your profile or work experience
  * Viewing someone’s profile
  * Searching for jobs or people

**In short:** Kafka = super fast, reliable event delivery.

---

## Slide 9 — Producers vs Consumers (simple)

* Producers: write messages to topics.
* Consumers: read from topics.
* Consumer groups: share partitions so work is balanced.
* Brokers: store the messages and manage partitions for topics. A broker is just a Kafka server. It can host many partitions for many topics.
* Leader: A leader is a role in the broker that currently handles reads/writes for a specific partition.

---

## Slide 10 — Topics and Partitions (with examples)

* **Topic** = the name of a stream of data.
  *Example:* `orders`, `user-signups`, `payments`.
* **Partition** = a slice of the topic for parallel processing.
  *Example:* `orders` topic → Partition 0, Partition 1, Partition 2.
* **Ordering guarantee** is per partition, not across partitions.
  *Example:* All messages for a single user go to Partition 1 → order preserved. Messages for other users may go to other partitions → order not guaranteed across partitions.

---

## Slide 11 — More About Partitions & Assignment

* **What a single partition does:**

  * Handles reads and writes for that slice of data.
  * Guarantees **message order only within itself**.

* **How many partitions can a topic have:**

  * You decide when creating the topic.
  * **1 partition** → simple, all messages ordered, no parallelism.
  * **Multiple partitions** → allows many consumers to read at the same time → faster processing.
  * Example: `orders` topic → 3 partitions → Partition 0, 1, 2.

* **Assigning messages to partitions:**

  1. **Without a key:** Kafka distributes messages in a **round-robin** way → evenly across partitions.
  2. **With a key:** Kafka always sends messages with the same key to the **same partition** → preserves order for that key.

* **Example:**

```text id="1k1uzv"
Orders topic → 3 partitions

Round-robin (no key):
Msg1 → Partition 0
Msg2 → Partition 1
Msg3 → Partition 2
Msg4 → Partition 0
...

With key (user_id):
User 2 → Partition 1
User 5 → Partition 1
User 8 → Partition 2
```

* **Throughput tip:**

  * A single partition can handle lots of messages, but splitting into multiple partitions **scales better** for high traffic.

---

## Slide 12 — How Kafka stays up (fault tolerance)

* Partitions have a leader and followers.
* Replication factor = how many copies exist (e.g., 3). Role of Followers: They replicate the data from the leader of their partition. They do not handle reads/writes from producers or consumers (unless promoted to leader). They stay in sync with the leader so that if the leader dies, one of them can take over immediately.
* If leader dies, a follower takes over.

How it works?
Partition 0:
  Leader -> Broker 1
  Followers -> Broker 2, Broker 3

Broker 1: receives all writes and reads (leader)
Broker 2 & Broker 3: copy every message Broker 1 gets (followers)
If Broker 1 fails → Broker 2 or 3 becomes new leader

---

## Slide 13 — Delivery guarantees (super short)

* **At most once:** maybe lost, but no duplicates. Fast.
* **At least once:** not lost, but may have duplicates. Safer.
* **Exactly once:** no duplicates, no loss. Best, needs extra setup.

---

## Slide 14 — Message storage rules
1. Retention (Time Window)
* Retention is a time window that allows the broker to continuously store events.

2. Log Compaction
* log compaction is like removing duplicates, but not blindly—it keeps only the latest message for each key.
* Kafka can **keep only the newest message for each key** in a topic.
* Instead of storing **all history**, it removes older messages with the same key.
* This is useful when you care about the **current state**, not every change over time.

**Example:**

* Topic: `user-profiles`
* Key = `user_id`
* Messages:

  1. `{user_id: 101, email: "a@mail.com"}`
  2. `{user_id: 101, email: "b@mail.com"}`
  3. `{user_id: 102, email: "x@mail.com"}`

After log compaction:

* Only the **latest message per user_id** remains:

  * `{user_id: 101, email: "b@mail.com"}`
  * `{user_id: 102, email: "x@mail.com"}`

So basically:
**Retention = time-based, Log Compaction = key-based.**

---

## Slide 15 — Example new workflow using Kafka (easy)

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
