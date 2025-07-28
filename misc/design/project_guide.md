Excellent — here’s your **Paigeant Project Guide**: a feature-by-feature battle plan structured for you to feed directly into a code assistant like GitHub Copilot, GPT-4, or to use as a collaborative partner during refinement. It's scoped for one experienced ML engineer working solo but efficiently.

---

# 🛠️ Paigeant Project Guide

**Purpose**: A lightweight orchestration framework for `pydantic-ai` agent workflows
**Primary Goals**: Distributed messaging, workflow state durability, async execution, secure & observable coordination

---

## 🧩 Feature 1: Transport Layer (RabbitMQ / Redis Streams)

### 🎯 Goal

Abstract over messaging infrastructure to support async publish/subscribe/acknowledge for routing-slip-based messages.

### 🧪 Design Specs

* `Transport` interface with:

  * `async def publish(topic: str, message: PaigeantMessage):`
  * `async def subscribe(topic: str) -> AsyncIterator[PaigeantMessage]:`
  * `async def ack(message_id: str):`
* Support both:

  * `aio-pika` for RabbitMQ
  * `aioredis` or `aredis-py` for Redis Streams

### 🧱 Starter Tasks

* [ ] Define `PaigeantMessage` dataclass or Pydantic model (with headers, payload, routing slip, trace\_id)
* [ ] Implement `RabbitMQTransport` with `aio-pika`
* [ ] Implement `RedisStreamTransport` with `aioredis`
* [ ] Include config to switch between transports (via environment or YAML)

### 🤖 Prompt for Model Pairing

> "Create a Redis Stream transport class that implements async publish and subscribe methods for a JSON-encoded message with metadata headers."

---

## 📜 Feature 2: Routing Slip Execution

### 🎯 Goal

Define the journey of a message through sequential (or conditional) activity steps.

### 🧪 Design Specs

* Routing slip structure:

  ```json
  {
    "itinerary": ["step_one", "step_two", "step_three"],
    "executed": [],
    "compensations": []
  }
  ```
* Execution handler that:

  * Picks current step
  * Runs it via registered function
  * Appends result and re-publishes to next step
  * Optionally handles compensation if needed

### 🧱 Starter Tasks

* [ ] Build a routing slip manager class: `RoutingSlip.next_step()`, `RoutingSlip.mark_complete()`
* [ ] Decorators: `@activity.execute()`, `@activity.compensate()`
* [ ] Registry for step-to-function mapping

### 🤖 Prompt for Model Pairing

> "Define a routing slip execution handler that processes one step in an itinerary and republishes the updated message with modified execution history."

---

## 🗃️ Feature 3: Postgres State Store

### 🎯 Goal

Persist workflow runs, step executions, and shared variables to support durability and introspection.

### 🧪 Design Specs

Schema:

* `workflow_runs`: `id`, `status`, `started_at`, `completed_at`
* `step_executions`: `workflow_id`, `step`, `input`, `output`, `status`, `error`
* `workflow_variables`: `workflow_id`, `key`, `value` (JSONB)

### 🧱 Starter Tasks

* [ ] Define SQLAlchemy 2.0 async models + Alembic migrations
* [ ] Implement storage service interface:

  * `record_workflow_start()`
  * `record_step_result()`
  * `save_variable()`, `load_variable()`
* [ ] Add retry-safe upserts (for idempotency)

### 🤖 Prompt for Model Pairing

> "Create async SQLAlchemy models for workflow and step execution history, using PostgreSQL JSONB fields for flexible metadata storage."

---

## ⚙️ Feature 4: Async Worker Runtime

### 🎯 Goal

Run activity steps from the queue with retries, timeouts, and context hydration.

### 🧪 Design Specs

* Infinite loop per queue/topic:

  * Pull message
  * Deserialize
  * Match to registered activity
  * Run with timeout and error catching
* Retry settings from routing slip metadata or decorator args

### 🧱 Starter Tasks

* [ ] Define base `ActivityWorker` class
* [ ] Add support for max retries and exponential backoff (`tenacity`)
* [ ] Timeout with `asyncio.wait_for` or `async_timeout`
* [ ] Emit structured logs with trace ID, step ID

### 🤖 Prompt for Model Pairing

> "Write an async worker loop that fetches tasks from a queue and executes them with a configurable retry policy and timeout."

---

## 🔧 Feature 5: Developer CLI

### 🎯 Goal

Allow developers to run workers, dispatch workflows, and manage configurations.

### 🧪 Design Specs

* CLI commands:

  * `paigeant run path/to/handlers.py`
  * `paigeant dispatch workflow_id input.json`
  * `paigeant init` to scaffold config
* Use `typer` for CLI ergonomics

### 🧱 Starter Tasks

* [ ] Set up Typer CLI with commands scaffolded
* [ ] Implement worker loader via `importlib`
* [ ] Validate activity registration at runtime

### 🤖 Prompt for Model Pairing

> "Implement a Typer CLI that loads Python modules, starts async workers, and dispatches workflows from JSON input files."

---

## 🕵️ Feature 6: Observability & Logging

### 🎯 Goal

Support traceable execution across workflows, including debugging, alerting, and audit trails.

### 🧪 Design Specs

* Structured logs in JSON (with trace ID, step ID, and correlation ID)
* Emit to console or file
* Optional Postgres sink for querying later

### 🧱 Starter Tasks

* [ ] Use `loguru` or `structlog` for structured logging
* [ ] Generate unique trace ID per workflow
* [ ] Include logs per step execution with success/failure status

### 🤖 Prompt for Model Pairing

> "Create structured JSON logs for each step of a workflow execution, including trace\_id, workflow\_id, and status."

---

## 🔐 Feature 7: Message Security

### 🎯 Goal

Secure each message with identity and tamper-proofing, optionally supporting OAuth2 delegation and JWS integrity.

### 🧪 Design Specs

* Message headers:

  * `obo_token`: OAuth2 delegated identity
  * `jws_signature`: Detached JWS of the payload
* Validate signature before executing

### 🧱 Starter Tasks

* [ ] Add `SecurityContext` to message metadata
* [ ] Use `python-jose` to sign and verify messages
* [ ] Optional: support public key rotation

### 🤖 Prompt for Model Pairing

> "Sign and verify a JSON message payload using JWS (RS256) with detached signatures in Python."

---

## 🧱 Recommended Build Phases

| Phase                                   | Features                                                      |
| --------------------------------------- | ------------------------------------------------------------- |
| **Phase 1: Core Transport & Execution** | Transport, Routing Slip, CLI `run`, basic worker              |
| **Phase 2: State & Retry**              | Postgres state, retries, timeout handling                     |
| **Phase 3: Security & Logging**         | JWS, identity headers, structured logging                     |
| **Phase 4: Dev UX Polish**              | Workflow dispatch CLI, variable management, graceful shutdown |
| **Phase 5: Optional Tooling**           | Dashboard (optional), Prometheus metrics, OpenTelemetry hooks |

---

## 📎 Extras

Would you like:

* A `pyproject.toml` + initial project scaffolding?
* A `docker-compose.yml` template with Postgres + Redis?
* A stubbed-out codebase with test examples?
* A Notion-style roadmap or Kanban board?

Let me know how you want to manage this — I can generate any of those instantly.
