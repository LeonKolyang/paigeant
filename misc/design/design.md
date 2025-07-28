# Paigeant: A Design for Resilient, Multi-Agent AI Workflows

## A Critical Re-evaluation: The Necessity of paigeant in a pydantic-ai World

The pydantic-ai ecosystem, particularly with the introduction of pydantic-graph, provides powerful tools for building complex, multi-step agentic workflows. A critical examination of these features is necessary to validate the core premise of paigeant. Does paigeant offer a distinct and necessary value proposition, or does it risk reinventing capabilities already present in its target ecosystem?

Our analysis of pydantic-ai's multi-agent examples reveals two primary patterns for complex workflows:

1. **Agent Delegation**: A synchronous, in-process pattern where one agent calls another via a tool. This is effective for tightly-coupled logic but mirrors the fragile RPC-style call chains that paigeant seeks to avoid in a distributed context.
    
2. **pydantic-graph**: A sophisticated, in-process state machine for orchestrating complex logic. With features like state persistence (FileStatePersistence), it offers a degree of durability for single-instance applications.
    

These tools are exceptionally well-suited for orchestrating complex tasks within a single, monolithic application process. However, they do not address the fundamentally different and more complex challenges of building systems composed of multiple, independently deployed, distributed services.

This is the critical gap that paigeant is designed to fill. paigeant is not an alternative to pydantic-graph; it is a complementary layer that operates at a different architectural level.

- **pydantic-ai and pydantic-graph** are for in-process orchestration.
- **paigeant** is for cross-process, distributed orchestration.
    

The core value proposition of paigeant is therefore not diminished but clarified: it provides the durable, secure, and resilient messaging fabric required to connect multiple, independent agent-based services into a cohesive and scalable "Agentic Mesh." A single paigeant worker might even run a complex pydantic-graph to execute its specific step in a larger, distributed workflow.

This re-evaluation confirms the feasibility and necessity of the paigeant design. It addresses a distinct and critical set of problems—distributed state management, inter-service security, and asynchronous communication—that are outside the scope of pydantic-ai's native capabilities. The following revised design document reflects this sharpened focus, positioning paigeant as the essential framework for taking pydantic-ai agents out of a single process and into a production-grade, distributed environment.

---

## Introduction: The Architectural Imperative for Agentic AI

The core value proposition of paigeant is therefore not diminished but clarified: it provides the durable, secure, and resilient messaging fabric required to connect multiple, independent agent-based services into a cohesive and scalable "Agentic Mesh." A single paigeant worker might even run a complex pydantic-graph to execute its specific step in a larger, distributed workflow.

This re-evaluation confirms the feasibility and necessity of the paigeant design. It addresses a distinct and critical set of problems—distributed state management, inter-service security, and asynchronous communication—that are outside the scope of pydantic-ai's native capabilities. The following revised design document reflects this sharpened focus, positioning paigeant as the essential framework for taking pydantic-ai agents out of a single process and into a production-grade, distributed environment.

---

## Introduction: The Architectural Imperative for Agentic AI

The emergence of collaborating Artificial Intelligence (AI) agents, capable of autonomously solving complex, multi-step business problems, represents a fundamental inflection point in enterprise architecture. However, the promise of these agentic systems cannot be realized by simply extending existing architectural patterns. The attempt to build these sophisticated workflows by chaining together individual agent calls creates what is known as a "distributed monolith"—a system that is brittle, difficult to scale, and prone to catastrophic failure when deployed in modern cloud environments.

The core of the issue lies in a deep architectural mismatch. The execution model of many contemporary AI frameworks is logically synchronous, a descendant of the request-response paradigm that has long dominated web services. This model is fundamentally at odds with the nature of agentic work, which is frequently characterized by its non-determinism and extended duration. An agentic task may involve a multi-step reasoning process, calls to several external tools, or waiting for human input, turning a single logical operation into a process that can last for minutes, hours, or even days. This extended duration directly conflicts with the assumptions of synchronous protocols like Remote Procedure Call (RPC) and HTTP, which presume a relatively quick and predictable turnaround.

This architectural mismatch is dangerously amplified by the ephemeral nature of modern cloud-native infrastructure, such as Kubernetes and serverless platforms. These environments are designed for resilience through disposability; components are expected to be volatile, and network connections can be terminated without warning to manage load or rebalance workloads. A long-running synchronous call, which relies on a stable, persistent connection, is therefore architecturally incompatible with an environment where its underlying connection can be terminated at any moment. The failure of any single agent in a synchronous chain causes the entire workflow to fail catastrophically, creating a system that has the distributed complexity of microservices but the tight coupling and fragility of a monolith.

This document outlines the design for paigeant, a lightweight Python library conceived to solve this problem. paigeant is not an agent framework; it is a durable messaging and workflow framework for agents. It is designed to orchestrate interactions between multiple, independent agents (such as those built with pydantic-ai), transforming fragile call chains into a resilient, secure, and observable agentic mesh for truly distributed systems. Its design is predicated on a set of non-negotiable architectural principles derived from decades of experience building production-grade distributed systems, providing the robust foundation required for the next generation of enterprise AI.

## Part 1: Foundational Architectural Principles

The design of paigeant is guided by three foundational principles that are not merely features but fundamental constraints shaping every subsequent architectural decision. These principles—asynchronous-first communication, durable execution, and zero-trust messaging—are not independent pillars but a deeply interconnected, mutually reinforcing system. The adoption of one necessitates the others, forming a holistic solution to the challenges of building distributed agentic systems.

### 1.1 The Asynchronous-First Imperative

The first and most critical principle is that all non-trivial inter-agent communication must be asynchronous by default. This is the only viable architectural path to achieve the necessary decoupling, resilience, and scalability required for complex workflows that span multiple services and unpredictable timeframes.

Synchronous, request-response calls create a tight temporal coupling, where every service in a call chain must be available simultaneously. This leads to severe performance bottlenecks as threads are blocked waiting for responses and creates cascading failures when any single component becomes unavailable. In modern cloud environments where components are disposable and network reliability is not guaranteed, this model is untenable.

The paigeant library addresses this by being architected around a message-driven model. Instead of agents calling each other directly, they send messages representing tasks to a durable message broker, such as a queue or stream. This decouples the agents in time and space. If a receiving agent is temporarily unavailable due to a crash, an upgrade, or a network partition, the message waits safely in the queue until the agent is ready, ensuring no work is lost and the system as a whole remains resilient. This approach fundamentally changes the developer's mental model from calling a function on an agent to sending a message that represents a task to be performed.

### 1.2 The Durable Execution Mandate

The second principle is that agentic workflows must be "crash-proof." Given that these workflows can span minutes, hours, or even days, tying the state of the process to the memory of the machine it is running on presents an existential threat. A server crash, network partition, or pod restart can wipe out the entire state of a running workflow, leading to inconsistent data, incomplete transactions, and a catastrophic failure of the business process.

To overcome this, paigeant is designed for Durable Execution, a paradigm where the execution of a workflow can survive the inevitable failures of distributed components. This is achieved by externalizing the program's state, scheduling, and error handling. The entire state of the workflow—its progress, its shared variables, and its context—is moved out of the ephemeral memory of a single process and into a durable store. paigeant implements this by encapsulating the complete workflow state within the message itself, using the Routing Slip pattern, and relying on a durable message broker to persist this state between each processing step. This allows a workflow to be paused and resumed exactly where it left off, even if the resuming process is running on an entirely different machine, making it a first-class, non-negotiable requirement of the library's design.

### 1.3 The Zero-Trust Messaging Framework

The shift to an asynchronous, message-driven architecture necessitates the third principle: a Zero-Trust Messaging security model. In a distributed system where messages are queued, stored, and forwarded by intermediary brokers, traditional security models focused on securing the communication channel (e.g., via TLS) become dangerously insufficient. The trust boundary of a TLS connection is broken the moment a message is persisted to a queue. Therefore, security must become an intrinsic, verifiable property of the message itself, treating every message as if it has traversed an untrusted network.

This framework is built upon two critical pillars. The first is verifiable delegated authority. It is essential that an agent, and any subsequent agents it invokes, cannot exceed the permissions of the human user who initiated the request. This requires a secure mechanism to propagate the user's identity and permissions throughout the entire chain of command.

paigeant is designed to support this by carrying OAuth 2.0 On-Behalf-Of (OBO) tokens within its message structure, the industry-standard solution for secure delegation.

The second pillar is message-level integrity and authenticity. The message payload itself must be protected from tampering and eavesdropping by any component with access to the message bus.1 To achieve this,

paigeant's message contract is designed to support cryptographic signatures using standards from the JSON Object Signing and Encryption (JOSE) framework, specifically JSON Web Signature (JWS). A JWS signature ensures that a message has not been altered (integrity) and verifiably comes from a trusted source (authenticity).[1, 1] For confidentiality, messages can be further protected with JSON Web Encryption (JWE).

The core message contract of paigeant will have dedicated, structured fields for carrying this security context, such as obo_token and jws_signature. This makes security an integral, non-optional part of the library's fundamental design, ensuring that every message carries its own proof of identity, authorization, and tamper-resistance.[1, 1]

  

## Part 2: The Federated Workflow Architecture

  

The core architectural model of paigeant is designed to cleanly separate the concerns of task execution from workflow management. This federated approach leverages the strengths of specialized agent frameworks while providing a robust, overarching structure for their collaboration.
The second pillar is message-level integrity and authenticity. The message payload itself must be protected from tampering and eavesdropping by any component with access to the message bus. To achieve this, paigeant's message contract is designed to support cryptographic signatures using standards from the JSON Object Signing and Encryption (JOSE) framework, specifically JSON Web Signature (JWS). A JWS signature ensures that a message has not been altered (integrity) and verifiably comes from a trusted source (authenticity). For confidentiality, messages can be further protected with JSON Web Encryption (JWE).

The core message contract of paigeant will have dedicated, structured fields for carrying this security context, such as `obo_token` and `jws_signature`. This makes security an integral, non-optional part of the library's fundamental design, ensuring that every message carries its own proof of identity, authorization, and tamper-resistance.

## Part 2: The Federated Workflow Architecture

The core architectural model of paigeant is designed to cleanly separate the concerns of task execution from workflow management. This federated approach leverages the strengths of specialized agent frameworks while providing a robust, overarching structure for their collaboration.

### 2.1 The Workflow Layer vs. The Task Layer: A Federated Model

The central architectural insight of paigeant is the clean separation between the Workflow Layer (cross-service orchestration) and the Task Layer (in-service execution). paigeant does not seek to replace existing agent frameworks; it orchestrates them across distributed service boundaries.

- **The Task Layer (pydantic-ai / pydantic-graph)**: This layer is responsible for the execution of a single, self-contained task within a single service. This is "Agent-to-World" communication. A service at this layer can use a simple pydantic-ai agent or even a complex pydantic-graph to handle its internal logic, leveraging tools and protocols like MCP to interact with its resources (APIs, databases, etc.).
    
- **The Workflow Layer (paigeant)**: This layer is responsible for the durable, secure, and reliable sequencing of tasks across multiple, distributed services. This is "Service-to-Service" communication, orchestrated via messages. paigeant manages the Routing Slip that connects these independent services into a cohesive and resilient business process.
    

This federated model allows developers to use the most appropriate tool for the job. They can leverage the power of pydantic-ai and pydantic-graph for complex in-process logic, while relying on paigeant to handle the cross-cutting concerns of distributed workflow orchestration.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                User Request (e.g., "Fulfill Order #123")               │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Workflow Layer (paigeant)                         │
│  • Manages Distributed Routing Slip                                    │
│  • Handles durability, security, compensation across services          │
│  • "Service-to-Service" Communication via Message Broker               │
└─────────────────────────────────────────────────────────────────────────┘
        │                     │                     │
    (Task 1)              (Task 2)              (Task 3)
        ▼                     ▼                     ▼
┌─────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  Service A  │     │     Service B       │     │     Service C       │
├─────────────┤     ├─────────────────────┤     ├─────────────────────┤
│    Task     │     │    Task Layer       │     │    Task Layer       │
│   Layer     │     │  (pydantic-graph)   │     │   (pydantic-ai)     │
│ (pydantic-  │     │   • Node 1          │     │ Agent: "Notifier"   │
│    ai)      │     │   • Node 2          │     │                     │
│ Agent:      │     │   • State Mgmt      │     │                     │
│ "Payments"  │     └─────────────────────┘     └─────────────────────┘
└─────────────┘              │                           │
        │                    ▼                           ▼
        ▼             ┌─────────────────────┐     ┌─────────────────────┐
┌─────────────┐       │      World:         │     │      World:         │
│   World:    │       │  Inventory DB, etc. │     │    Slack API        │
│ Stripe API  │       └─────────────────────┘     └─────────────────────┘
└─────────────┘
```

**Figure 2.1: The Federated Architecture Model, Clarified**

  

### 2.2 The Routing Slip Pattern: The Chosen Model for the Workflow Layer

To coordinate the sequence of tasks in the workflow layer, paigeant implements the Routing Slip pattern. A rigorous comparative analysis of workflow management patterns reveals that this approach offers a superior alternative to the traditional dichotomy of centralized orchestration versus decentralized choreography, particularly for the dynamic nature of AI agent workflows.

Orchestration involves a central mediator that dictates the workflow, creating a single point of failure and a potential development bottleneck. Choreography is a decentralized, event-driven model that promotes loose coupling but suffers from a significant loss of end-to-end visibility, making workflows difficult to monitor and debug.

The Routing Slip pattern provides a "third way" that synthesizes the best of both worlds. In this pattern, the sequence of processing steps—the "itinerary"—is attached to the message itself, typically within a message header. Each agent that receives the message performs three actions: it inspects the routing slip to identify its task, it executes that task, and then it forwards the message to the next destination listed in the slip. Crucially, there is no central component coordinating the flow; the workflow logic travels with the message.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            PaigeantMessage                                │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │                              Headers                                  │ │
│ │ ┌────────────────────────────────────────────────────────────────────┐ │ │
│ │ │                           RoutingSlip                             │ │ │
│ │ │ Itinerary: [ "update-inventory", "notify-customer" ]              │ │ │
│ │ │ ActivityLog: [ { name: "charge-card", result: {...} } ]           │ │ │
│ │ └────────────────────────────────────────────────────────────────────┘ │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│ │ Payload: { item_id: "abc",... }                                        │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                         ┌──────────────────────┐
                         │      Worker:         │  1. Executes "update-inventory" task
                         │  Update Inventory    │  2. Updates RoutingSlip (moves step from itinerary to log)
                         └──────────────────────┘  3. Forwards message to "notify-customer" queue
                                      │
                                      ▼
                         ┌──────────────────────┐
                         │      Worker:         │
                         │   Notify Customer    │
                         └──────────────────────┘
```

**Figure 2.2: The Routing Slip Message Flow**

This approach directly solves the primary drawback of choreography—the lack of visibility—by making the workflow explicit and auditable. At any point, an observer can inspect the message's routing slip to see which steps have been completed and which are next, providing the clear operational insight of orchestration while retaining the decentralized execution and resilience of choreography. This pattern is exceptionally well-suited for AI, as a "planner" agent can use an LLM to dynamically generate the itinerary at runtime based on a user's initial, high-level request, enabling highly flexible and context-aware workflows.

| Dimension | Orchestration | Choreography | Routing Slip |
|-----------|---------------|--------------|--------------|
| Control Model | Centralized, command-driven. A single orchestrator dictates the workflow. | Decentralized, event-driven. Agents react to events published by others. | Decentralized, message-driven. Workflow is defined in the message header. |
| Coupling | Tighter. Orchestrator is coupled to all participating agents. | Loosest. Agents are only aware of the event bus, not each other. | Loose. Agents are decoupled from each other but coupled to the message format. |
| Visibility & Debugging | High. Centralized logic provides a clear view of the entire workflow state. | Low. The end-to-end workflow is an "emergent" property, making it hard to trace. | High. The workflow itinerary is explicit and travels with the message, making it auditable. |
| Resilience | Lower. The orchestrator is a single point of failure. | High. No single point of failure; failure of one agent does not stop others. | High. No central controller; relies on durable messaging for resilience. |
| Suitability for Non-Deterministic AI | Moderate. Good for predictable sub-tasks but can be rigid for dynamic, multi-step reasoning. | High. Excellent for reactive, event-driven agent behaviors. | Very High. Itinerary can be dynamically generated, providing explicit control for dynamic workflows. |

**Table 2.1: Comparison of Workflow Management Patterns for AI Agents**

  

### 2.3 The Saga Pattern: Managing Distributed Transactions with Compensation

In a distributed system composed of independent services, maintaining data consistency across a multi-step business process is a critical challenge. Traditional, locking-based distributed transactions (like two-phase commit) are not feasible due to their tight coupling and performance implications in a large-scale architecture.

To solve this, paigeant will implement the Saga pattern for managing long-running, distributed transactions. A saga is a sequence of local transactions where each transaction updates a single service and triggers the next step. If a local transaction fails at any point in the sequence, the saga executes a series of compensating transactions that programmatically undo the work of the preceding, successfully completed transactions.

paigeant integrates this pattern directly into its Routing Slip model, inspired by mature messaging frameworks. An activity can define not only its primary execute logic but also a corresponding compensate method. The RoutingSlip maintains a compensation_log of all successfully completed steps that have a compensator defined. If a downstream activity in the itinerary fails (e.g., by raising an exception), the paigeant runtime catches the fault and initiates a compensation flow. It iterates through the compensation_log in reverse order, invoking the compensate method for each entry. This provides developers with a clear, built-in, and robust mechanism for handling business failures gracefully and maintaining data consistency across services without requiring distributed locks.

## Part 3: Core Data Contracts and API Design

The foundation of paigeant's developer experience and robustness is a set of well-defined data contracts and a clean, intuitive API. By mandating the use of Pydantic for all data structures, the library ensures that every message is type-safe, self-documenting, validated, and easily serializable for transport over a message bus.

### 3.1 Universal Data Contracts: The PaigeantMessage Model

The use of `pydantic.BaseModel` is required for defining all data structures that cross service boundaries. This provides compile-time benefits through IDE support and static analysis, and crucial runtime robustness through automatic validation and clear, structured error handling. The universal message envelope is the `PaigeantMessage`.

- **PaigeantMessage(BaseModel)**: The top-level object that is passed through the message broker for every step of a workflow.
    - `payload: dict | BaseModel`: The specific data or arguments required for the current activity. This is the "what to do" part of the message.
    - `headers: MessageHeaders`: A nested Pydantic model containing all workflow metadata and context.

- **MessageHeaders(BaseModel)**: This model encapsulates all the metadata required to route, secure, and trace the message.
    - `message_id: UUID`: A unique identifier for this specific message instance, critical for idempotency checks and logging.
    - `correlation_id: UUID`: A unique identifier for the entire end-to-end workflow. All messages within a single workflow share the same correlation_id.
    - `routing_slip: RoutingSlip`: The embedded routing slip object, which contains the full state of the workflow.
    - `security_context: SecurityContext`: A dedicated model for carrying all security-related information.
    - `trace_context: dict[str, str]`: A dictionary to carry distributed tracing context, such as W3C Trace Context headers (traceparent, tracestate).

- **RoutingSlip(BaseModel)**: The Pydantic implementation of the Routing Slip pattern.
    - `itinerary: list[Activity]`: An ordered list of the remaining processing steps to be executed.
    - `activity_log: list[ActivityLog]`: A log of activities that have been successfully executed, providing an audit trail.
    - `compensation_log: list[ActivityLog]`: A log of completed activities that have a corresponding compensation action defined, used to orchestrate rollbacks.
    - `variables: dict[str, Any]`: A key-value store for data that needs to be passed between activities in the workflow.

- **SecurityContext(BaseModel)**: This model encapsulates the security information for the Zero-Trust Messaging framework.
    - `obo_token: str | None`: The OAuth 2.0 On-Behalf-Of token, carrying the delegated authority of the original user.
    - `jws_signature: str | None`: The JWS signature of the message content, ensuring integrity and authenticity.

| Field Name | Pydantic Type | Description | Example |
|------------|---------------|-------------|---------|
| payload | `dict \| BaseModel` | The data specific to the current task. For a charge-card activity, this would contain the amount and currency. | `{"amount": 100, "currency": "USD"}` |
| headers | MessageHeaders | A nested object containing all metadata for the message. | (see below) |
| headers.message_id | UUID | A unique ID for this specific message hop. | UUID('7a7c...') |
| headers.correlation_id | UUID | A unique ID for the entire workflow instance. | UUID('f4a2...') |
| headers.routing_slip | RoutingSlip | The object containing the workflow state. | RoutingSlip(itinerary=[...],...) |
| headers.security_context | SecurityContext | The object containing security tokens and signatures. | SecurityContext(obo_token="ey...") |
| headers.trace_context | dict[str, str] | W3C Trace Context headers for observability. | {"traceparent": "00-...", "tracestate": "..."} |

**Table 3.1: PaigeantMessage Pydantic Model Specification**

  

### 3.2 The Developer API: Activities, Context, and the RoutingSlipBuilder

The library's usability hinges on an API that feels like a natural extension of the Pydantic ecosystem. This is achieved through an explicit registry, intuitive decorators, and context objects.

- **activities = paigeant.Registry()**: To ensure robust discovery, the library will provide a central Registry object. Developers will import this singleton instance and use it to define all their workflow activities.

- **activity = activities.activity(name="...")** Decorator: This is the primary developer interface for registering a standard Python async function as a workflow step. It will support a chained API for defining the core logic and its corresponding compensation logic.
    - `@activity.execute`: A decorator for the function containing the main business logic of the step.
    - `@activity.compensate`: A decorator for the function that defines how to undo the work of the execute step.

- **ActivityContext Object**: This object is automatically passed as the first argument to every activity function. It serves as a type-safe gateway to the wider workflow context, providing methods like `ctx.get_variable("key")`, `ctx.set_variable("key", "value")`, and access to properties like `ctx.correlation_id`.

- **RoutingSlipBuilder Class**: This is a fluent API for programmatically constructing and dispatching a new workflow. It simplifies the creation of the initial PaigeantMessage by providing methods to `add_activity()`, `add_variable()`, and attach security context with `with_obo_token()` and `sign_with_private_key()`.

### 3.3 The Pluggable Transport Layer

To ensure the library is flexible and not tied to a single messaging technology, it will feature a pluggable transport layer. This design ensures that the core workflow logic defined in activities remains completely decoupled from the underlying messaging infrastructure.

An abstract base class, `Transport`, will define the essential methods required for message-driven communication: `connect`, `disconnect`, `publish`, and `subscribe`. The library will ship with a few key concrete implementations to support a range of use cases from testing to production:

- **RabbitMQTransport**: For production-grade, reliable messaging using the AMQP protocol.
- **RedisTransport**: Leveraging Redis Streams for a lightweight but persistent messaging option suitable for many cloud-native deployments.
- **InMemoryTransport**: An in-memory queue designed for simple use cases and, crucially, for fast and dependency-free unit and integration testing.

Developers will configure the desired transport during the initialization of the paigeant runtime, allowing them to switch backends with minimal code changes.

## Part 4: Advanced Design Refinements

To elevate the developer experience and operational robustness beyond the core features, paigeant will incorporate sophisticated patterns inspired by best-in-class frameworks, adapted specifically for its unique architectural context.

### 4.1 Workflow-Scoped Dependency Injection

FastAPI's Depends system is a masterclass in developer experience, offering a declarative, intuitive pattern for managing dependencies that significantly improves code modularity and testability. However, its dependency lifecycle is fundamentally coupled to the ephemeral nature of an HTTP request, making a direct implementation unsuitable for paigeant's long-running workflows.

To harness these benefits, paigeant will implement its own declarative dependency injection (DI) system, tailored to its execution model. A paigeant activity would be defined as a standard Python function, and its dependencies (e.g., a database session, an external service client) would be declared as parameters annotated with a `paigeant.Depends` marker. The implementation will explicitly adopt the generator/yield pattern for dependency providers to ensure robust resource management.

```python
# file: my_app/db.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session():
    session = DBSession()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

# file: activities.py
from paigeant.dependencies import Depends
from my_app.db import DBSession, get_db_session

@activity.execute
async def process_order_task(
    ctx: ActivityContext,
    order_id: int,
    db: DBSession = Depends(get_db_session)
):
    # Business logic using the injected db session
    ...
```

The paigeant Worker runtime would be responsible for managing the dependency's lifecycle. Before executing the activity function, the runtime would enter the `get_db_session` context manager to acquire the resource. After the task completes or fails, the runtime would ensure the finally block is executed to guarantee proper cleanup. This approach scopes the dependency lifecycle to the execution of a single workflow task, bringing the exceptional usability and testability of FastAPI's DI to paigeant's core business logic without introducing an architectural mismatch.

  

### 4.2 Observability and Unified Tracing

A major drawback of decentralized, asynchronous systems is the loss of visibility, which makes monitoring and debugging exceptionally difficult. paigeant addresses this head-on by making observability a first-class concern, designed for seamless integration with modern observability platforms like Pydantic Logfire.

The solution is built around the automatic propagation of distributed tracing context. The PaigeantMessage header includes a `trace_context` field specifically for carrying W3C Trace Context headers (traceparent, tracestate). The system works as follows:

1. **Context Propagation**: When a workflow is initiated (e.g., from an incoming web request that is already part of a trace), the RoutingSlipBuilder will automatically capture the current trace context and embed it in the outgoing PaigeantMessage's trace_context header.
    
2. **Context Resumption**: When a paigeant worker receives a message, its first action before executing any business logic is to read the trace_context header and resume the trace.
    

The result is a single, unified trace in an observability platform that visualizes the entire end-to-end workflow. This trace will show the initial event that triggered the workflow, followed by spans for each message being published and consumed from the message broker, and finally the spans for the execution of each individual activity, even if those activities are running in different services, on different machines, and at different times. This built-in integration solves one of the most critical operational challenges of distributed systems, providing the high level of visibility characteristic of orchestration while retaining the resilience and decoupling of a message-driven architecture.

## Part 5: The Execution Environment and Runtime

A robust library requires a well-defined execution model. This section details the complete, concrete plan for running paigeant activities, from local development to production in the cloud. The proposed architecture follows a standard Control Plane / Data Plane model. A lightweight web application serves as the Control Plane, responsible for managing the lifecycle of the workers, while the workers themselves constitute the Data Plane, executing the actual workflow tasks.

To ensure clarity, the following terminology will be used:

- **Activity**: A single, decorated Python function representing one step in a workflow.
- **Worker**: The generic, long-lived OS process whose job is to listen to a single message queue and execute a specific Activity when a message arrives.
- **Process Manager**: The paigeant runner CLI tool, which serves as the control plane. It is responsible for discovering Activities and launching and managing the lifecycle of the Worker processes.

```
┌─────────────────────────────────────────────────┐
│    Process Manager (paigeant runner CLI)       │
│  • Discovers Activities from Registry           │
│  • Spawns and manages Worker processes          │
│  • Handles graceful shutdown signals (SIGTERM)  │
└─────────────────────────────────────────────────┘
        │                │                │
    (Spawns)          (Spawns)          (Spawns)
        ▼                ▼                ▼
┌─────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Worker P1   │  │   Worker P2     │  │   Worker P3     │
│    (Q1)     │  │     (Q2)        │  │     (Q3)        │
├─────────────┤  ├─────────────────┤  ├─────────────────┤
│  Executes   │  │   Executes      │  │   Executes      │
│ "charge-    │  │ "update-inv"    │  │ "notify-cust"   │
│  card"      │  │                 │  │                 │
└─────────────┘  └─────────────────┘  └─────────────────┘
        ▲                ▲                ▲
        │                │                │
   (Consumes)       (Consumes)       (Consumes)
        │                │                │
┌───────────────────────────────────────────────────────┐
│       Message Broker (e.g., RabbitMQ)                │
│      [Queue 1] [Queue 2] [Queue 3]                   │
└───────────────────────────────────────────────────────┘
```

**Figure 5.1: The paigeant Execution Environment**

### 5.1 The paigeant Runner CLI

To maintain a minimal and clean developer experience, the framework will be built around a command-line interface (CLI) tool, the paigeant runner, which acts as the Process Manager. The developer's responsibility is to define their activities in a Python script. The runner's responsibility is to discover those activities and launch them in isolated, long-lived Worker processes. The CLI will provide two primary commands:

- `paigeant run agents.py`: For starting the Worker processes in a local development environment.
- `paigeant deploy kubernetes`: For generating the necessary configuration to deploy the Worker processes to a Kubernetes cluster.

This approach encapsulates the complexity of process and container management. The runner discovers activities not by parsing files, but by importing the specified module (e.g., agents.py) and consulting the explicit activities registry object, which contains a definitive list of all defined workflow steps.

#### 5.1.1 Activity-to-Queue Mapping

The mapping of an activity's logical name to a physical queue name on the message broker will be handled by a simple, predictable naming convention. By default, the queue name for an activity will be derived directly from its registered name (e.g., the activity named "charge-card" will listen on a queue named `paigeant.charge-card`). This convention simplifies configuration, but the `activities.activity` decorator will accept an optional `queue_name` argument to allow developers to specify a custom name for advanced use cases.

  

### 5.2 Local Deployment: A multiprocessing-based Approach

For local development, the goal is speed and simplicity. The `paigeant run agents.py` command will use Python's native multiprocessing module to launch and manage the Worker processes.

For each discovered Activity, the Process Manager will spawn a new, separate OS process using `multiprocessing.Process`. It is critical to use Process directly, as it is designed for creating single, independent, long-lived processes, which perfectly matches the requirement for persistent Worker listeners. `multiprocessing.Pool`, in contrast, is designed for batch processing of short-lived tasks and is unsuitable for this use case. Each process gets its own memory space and Python interpreter, providing the necessary isolation for fail-safety; a crash in one Worker's process will not affect any others.

A crucial implementation detail for ensuring safety and portability is the process "start method." The paigeant framework will explicitly set the start method to spawn using `multiprocessing.set_start_method('spawn')`. The fork method, while faster, is fundamentally unsafe in multi-threaded applications (as many common libraries are) and can lead to deadlocks. spawn starts a brand new, clean Python interpreter process, providing the strongest isolation and avoiding subtle bugs related to inherited state. It is also the only method that is compatible across all major platforms (Linux, macOS, Windows), which is essential for a general-purpose library.

### 5.3 Production Deployment: The Docker and Kubernetes Pattern

For production, the environment must be scalable, resilient, and manageable by modern cloud orchestration tools like Kubernetes. The recommended deployment strategy is the "one image, multiple deployments" pattern.

1. **Containerization**: The developer creates a single Dockerfile that packages the application code (containing all activities) and its dependencies into one Docker image.
    
2. **Deployment Configuration**: While only one Docker image is built, a separate Kubernetes Deployment manifest is created for each Worker type (i.e., for each Activity). Each Deployment manifest will reference the same Docker image but will override the container's startup command or arguments to specify which single Activity it should run. For example:

   - Payment Worker Deployment: `command: ["paigeant", "run", "agents.py", "--activity-name=charge-payment"]`
   - Inventory Worker Deployment: `command: ["paigeant", "run", "agents.py", "--activity-name=update-inventory"]`

3. **Scalability and Resilience**: This pattern allows Kubernetes to treat each Worker type as an independent, scalable unit. The payment worker can be scaled to five replicas while the inventory worker remains at two, all managed by Kubernetes' native load balancing and self-healing capabilities.
    

To maintain a minimal developer experience, the paigeant deploy kubernetes command will automate this process by discovering the activities and programmatically generating the necessary Kubernetes Deployment YAML files before applying them to the cluster.1

  

### 5.4 Graceful Shutdown and Process Lifecycle Management

  

### 5.4 Graceful Shutdown and Signal Handling

A critical aspect of durable execution is ensuring that when the system is shut down for maintenance or deployment, workers are terminated gracefully, allowing them to complete their current in-flight tasks before exiting. An abrupt termination can lead to lost work and inconsistent state.

paigeant will implement a robust graceful shutdown procedure using a combination of Python's multiprocessing and signal libraries, orchestrated by the Process Manager.

1. **Shared Event**: The main Process Manager creates a `multiprocessing.Event` object called `shutdown_event`. This event object is passed as an argument to each child Worker process when it is created.
    
2. **Signal Handling**: The main process registers signal handlers for SIGINT (from Ctrl+C) and SIGTERM (the standard shutdown signal from orchestrators like Kubernetes). When a signal is received, the handler's only job is to call `shutdown_event.set()`.
    
3. **Cooperative Worker Loop**: Inside its main listening loop, each Worker process periodically checks if `shutdown_event.is_set()`. If it is, the Worker knows it is time to shut down. It will stop accepting new messages from its queue, finish processing its current message, and then exit cleanly.
    
4. **Joining Processes**: After setting the event, the main process, within its shutdown logic, iterates through all child processes and calls `process.join()` on each one. This call blocks the main process, making it wait until all children have finished their work and exited cleanly before it terminates itself.
    

This pattern ensures that a shutdown request is handled in an orderly, cooperative fashion, preventing data loss and fulfilling the core design principle of durable execution.

  

## Part 6: Reference Implementation: E-Commerce Workflow

  

To demonstrate how all the library's features work in concert, this section provides a concrete, end-to-end code example of a realistic e-commerce order fulfillment workflow. The workflow involves three steps: charging a credit card, updating the inventory, and notifying the customer.

### 6.1 Defining the Activities with Compensation

Each step is defined as a separate, decorated activity. The charge-card and update-inventory steps also define compensation methods to handle potential failures.

```python
# file: activities.py
import paigeant
from paigeant.dependencies import Depends
from .dependencies import (
    PaymentGateway, InventoryDB, NotificationService,
    get_db, get_payments, get_notifications
)

# 1. Create a central registry for all activities
activities = paigeant.Registry()

# 2. Define the 'charge card' activity with execute and compensate methods
charge_card = activities.activity(name="charge-card")

@charge_card.execute
async def execute_charge(
    ctx: paigeant.ActivityContext,
    amount: float,
    card_token: str,
    payments: PaymentGateway = Depends(get_payments)
) -> dict:
    print(f"[{ctx.correlation_id}] Charging card for {amount}...")
    transaction_id = await payments.charge(amount=amount, token=card_token)
    # The returned dict is logged and used for compensation
    return {"transaction_id": transaction_id, "charged_amount": amount}

@charge_card.compensate
async def compensate_charge(
    ctx: paigeant.ActivityContext,
    transaction_id: str,
    charged_amount: float,
    payments: PaymentGateway = Depends(get_payments)
):
    print(f"[{ctx.correlation_id}] Refunding payment {transaction_id}...")
    await payments.refund(transaction_id=transaction_id, amount=charged_amount)

# 3. Define the 'update inventory' activity with compensation
update_inventory = activities.activity(name="update-inventory")

@update_inventory.execute
async def execute_update_inventory(
    ctx: paigeant.ActivityContext,
    item_id: str,
    quantity: int,
    db: InventoryDB = Depends(get_db)
) -> dict:
    print(f"[{ctx.correlation_id}] Decrementing inventory for {item_id} by {quantity}...")
    # This would raise an exception if stock is insufficient, triggering compensation
    await db.decrement_stock(item_id=item_id, count=quantity)
    return {"item_id": item_id, "decremented_by": quantity}

@update_inventory.compensate
async def compensate_update_inventory(
    ctx: paigeant.ActivityContext,
    item_id: str,
    decremented_by: int,
    db: InventoryDB = Depends(get_db)
):
    print(f"[{ctx.correlation_id}] Restoring inventory for {item_id}...")
    await db.increment_stock(item_id=item_id, count=decremented_by)

# 4. Define the 'notify customer' activity (no compensation needed)
notify_customer = activities.activity(name="notify-customer")

@notify_customer.execute
async def execute_notify(
    ctx: paigeant.ActivityContext,
    message: str,
    notifications: NotificationService = Depends(get_notifications)
):
    # Use a variable set by a previous step
    customer_id = await ctx.get_variable("customer_id")
    print(f"[{ctx.correlation_id}] Notifying customer {customer_id}...")
    await notifications.send(user_id=customer_id, text=message)
```
  

  

### 6.2 Building and Dispatching the Routing Slip

The workflow is initiated by another part of the application, such as an API endpoint. This component uses the RoutingSlipBuilder to dynamically construct the workflow and dispatch it for execution.

```python
# file: api.py
import uuid
import paigeant
from fastapi import FastAPI, Request
from .schemas import OrderRequest

app = FastAPI()

@app.post("/orders")
async def create_order(order_request: OrderRequest, http_request: Request):
    # Dynamically build the routing slip based on the request
    builder = paigeant.RoutingSlipBuilder(correlation_id=uuid.uuid4())

    # Add the activities in the desired sequence
    builder.add_activity(
        name="charge-card",
        arguments={
            "amount": order_request.amount,
            "card_token": order_request.card_token,
        },
    )
    builder.add_activity(
        name="update-inventory",
        arguments={
            "item_id": order_request.item_id,
            "quantity": order_request.quantity,
        },
    )
    builder.add_activity(
        name="notify-customer",
        arguments={
            "message": "Your order has been confirmed!",
        },
    )

    # Set initial variables that can be used by any activity
    builder.add_variable("customer_id", order_request.customer_id)

    # Attach security context (token would come from request auth)
    # user_obo_token = http_request.headers.get("Authorization")
    # builder.with_obo_token(user_obo_token)

    # Dispatch the workflow for execution
    await paigeant.execute(builder.build())

    return {"status": "processing", "workflow_id": str(builder.correlation_id)}
```
  

This example illustrates the core developer experience: defining modular, testable activities with clear failure-handling logic, and then composing them into a resilient workflow using a simple builder API.

## Part 7: Conclusion and Future Roadmap

This document has presented a comprehensive design for paigeant, a lightweight Python library conceived to provide the critical missing layer for building production-grade, distributed agentic systems. The design is explicitly grounded in the architectural principles of asynchronous-first communication, durable execution, and zero-trust messaging. By adopting the Routing Slip pattern as its core workflow model and providing a clean, Pydantic-based API, paigeant strikes an optimal balance between decentralized resilience and explicit visibility, offering a solution that is both robust and idiomatic to the modern Python ecosystem.

### 7.1 Summary of Value Proposition

The core value of the paigeant library lies in its ability to bridge the gap between single-agent, request-response AI applications and complex, multi-agent business processes. It achieves this by delivering on several key promises:

- **Seamless Integration**: By mirroring the developer experience of frameworks like FastAPI and Pydantic through decorators (`@activity`), context objects (`ActivityContext`), and dependency injection (`paigeant.Depends`), the library feels like a natural extension, not a foreign framework.
    
- **Resilience and Durability by Design**: Through the implementation of the Routing Slip and Saga patterns on top of a durable message broker, workflows become inherently "crash-proof." This provides developers with a clear and manageable pattern for handling distributed transactions and business failures.
    
- **Production-Grade Security**: The library moves beyond transport-level security by implementing a Zero-Trust Messaging model. By embedding verifiable delegated authority (OAuth 2.0 OBO) and message integrity (JWS) directly into the message headers, it provides a robust security posture suitable for enterprise environments.
    
- **Observable Workflows**: By making distributed tracing a first-class feature with automatic context propagation, paigeant solves one of the most significant operational challenges of decentralized systems: visibility. Its design provides clear, end-to-end traceability for complex, asynchronous processes.

### 7.2 Future Roadmap

The proposed design provides a strong foundation, but it also opens the door to several powerful extensions that could further enhance the library's capabilities. The following areas represent a strategic roadmap for future development:

- **Advanced State Management and Querying**: While the Routing Slip carries its state with it, this makes querying the status of in-flight workflows difficult. A future version could introduce an optional SagaRepository that subscribes to workflow events (e.g., ActivityCompleted, WorkflowFaulted) and persists the state of the routing slip to a database. This would enable a monitoring UI or API to query the real-time status of any workflow by its correlation_id.
    
- **Parallel Execution (Scatter-Gather)**: The current design focuses on sequential workflows. Many business processes, however, can benefit from parallel execution. The Routing Slip model could be extended to support the Scatter-Gather pattern. A special scatter step would break the workflow into multiple parallel branches, and a corresponding gather (or Aggregator) step would wait for all branches to complete before continuing the main workflow.
    
- **Dynamic Agent and Activity Discovery**: The current design assumes that the available activities are known when the routing slip is built. To create a truly dynamic agentic mesh, the system needs a mechanism for runtime discovery. Future work could focus on integrating with emerging standards for agent description, such as the W3C Web of Things (WoT) Thing Description format. A paigeant worker could publish a WoT description of its available activities, and a "planner" agent could then query a central registry to discover and compose workflows with activities it did not know about at design time.
    
- **Cross-Language Interoperability**: While paigeant is a Python library, the agentic systems it helps build may include components written in other languages. The PaigeantMessage and RoutingSlip Pydantic models can have their schemas exported to the language-agnostic JSON Schema format. This schema can be published to a central registry, allowing teams using other languages (e.g., TypeScript, .NET, Rust) to build agents that can participate in the same workflows by consuming and producing messages that conform to the same, well-defined contract, paving the way for a truly polyglot agentic mesh.

---

*This design document represents a comprehensive architectural foundation for building resilient, distributed AI agent workflows. The paigeant library aims to bridge the gap between single-process AI applications and production-scale, multi-service agentic systems.*