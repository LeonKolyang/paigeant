# Paigeant Features

A comprehensive overview of all functional features available in the Paigeant library.

## Core Workflow Features

### Agent Management
- **PaigeantAgent** ([`paigeant.agent.wrapper.PaigeantAgent`](paigeant/agent/wrapper.py)): Enhanced wrapper around `pydantic_ai.Agent` with workflow capabilities
- **Agent Discovery** ([`paigeant.agent.discovery.discover_agent`](paigeant/agent/discovery.py)): Dynamic discovery of agents by name from files or directories
- **Agent Registry** ([`paigeant.agent.wrapper.AGENT_REGISTRY`](paigeant/agent/wrapper.py)): Global registry for managing and locating agents
- **Generic Output Types** ([`paigeant.agent.wrapper.PaigeantOutput[T]`](paigeant/agent/wrapper.py)): Support for typed agent outputs with `PaigeantOutput[T]`

### Workflow Orchestration
- **WorkflowDispatcher** ([`paigeant.dispatch.WorkflowDispatcher`](paigeant/dispatch.py)): Central coordinator for creating and managing workflows
- **ActivitySpec** ([`paigeant.contracts.ActivitySpec`](paigeant/contracts.py)): Structured definition of workflow steps with prompts and dependencies
- **RoutingSlip** ([`paigeant.contracts.RoutingSlip`](paigeant/contracts.py)): Ordered execution plan with itinerary, executed steps, and compensations
- **Dynamic Itinerary Editing** ([`paigeant.tools._edit_itinerary`](paigeant/tools/default_tools.py)): Agents can add new steps to workflows at runtime
- **Sequential Execution** ([`paigeant.contracts.RoutingSlip.mark_complete`](paigeant/contracts.py)): Step-by-step workflow progression with state preservation

### Message Passing & Communication
- **PaigeantMessage** ([`paigeant.contracts.PaigeantMessage`](paigeant/contracts.py)): Comprehensive message envelope with metadata, routing, and payload
- **Async-First Architecture** ([`paigeant.transports.BaseTransport.publish`](paigeant/transports/base.py)): All inter-agent communication via message brokers
- **Correlation Tracking** ([`paigeant.contracts.PaigeantMessage.correlation_id`](paigeant/contracts.py)): UUID-based workflow and message correlation
- **Trace Context** ([`paigeant.contracts.PaigeantMessage.trace_id`](paigeant/contracts.py)): Built-in distributed tracing support

### Transport Layer
### Transport Layer
- **InMemory Transport** ([`paigeant.transports.InMemoryTransport`](paigeant/transports/inmemory.py)): Zero-setup development transport
- **Redis Transport** ([`paigeant.transports.RedisTransport`](paigeant/transports/redis.py)): Production-ready with pub/sub and streams
- **Custom Transports** ([`paigeant.transports.BaseTransport`](paigeant/transports/base.py)): Pluggable interface for any messaging system
- **Message Serialization** ([`paigeant.deps.serializer`](paigeant/deps/serializer.py)): JSON-based with extensible serialization layer
- **Auto-connection Management** ([`paigeant.transports`](paigeant/transports/__init__.py)): Automatic lifecycle and error handling

### Persistence & State Management
- **Workflow Repository** ([`paigeant.persistence.WorkflowRepository`](paigeant/persistence/repository.py)): Persistent workflow state storage
- **SQLite Backend** ([`paigeant.persistence.SQLiteWorkflowRepository`](paigeant/persistence/sqlite.py)): File-based persistence for development
- **PostgreSQL Backend** ([`paigeant.persistence.PostgresWorkflowRepository`](paigeant/persistence/postgres.py)): Production database support
- **InMemory Backend** ([`paigeant.persistence.InMemoryWorkflowRepository`](paigeant/persistence/inmemory.py)): Ephemeral storage for testing
- **Step Tracking** ([`paigeant.persistence.models.StepRecord`](paigeant/persistence/models.py)): Detailed execution history and status

### Dependency Management
- **WorkflowDependencies** ([`paigeant.contracts.WorkflowDependencies`](paigeant/contracts.py)): Container for shared workflow data
- **Dependency Serialization** ([`paigeant.deps.serializer.DependencySerializer`](paigeant/deps/serializer.py), [`paigeant.deps.deserializer.DependencyDeserializer`](paigeant/deps/deserializer.py)): Safe serialization/deserialization of complex objects
- **Previous Output Access** ([`paigeant.contracts.PreviousOutput`](paigeant/contracts.py)): Agents can access outputs from prior steps
- **Typed Dependencies** ([`paigeant.contracts.SerializedDeps`](paigeant/contracts.py)): Full type safety for dependency injection

## Built-in Tools & Capabilities

### Agent Tools
- **Previous Output Extraction** ([`paigeant.tools._extract_previous_output`](paigeant/tools/default_tools.py)): Tool for accessing prior results from workflow context
- **Dynamic System Prompts** ([`paigeant.tools._itinerary_editing_prompt`](paigeant/tools/default_tools.py)): Context-aware prompt generation for itinerary editing

### CLI Interface
- **Agent Execution** (`paigeant.cli.execute`): `paigeant execute <agent_name>` to run workers
- **Workflow Inspection** ([`paigeant.cli.workflows`](paigeant/cli.py), [`paigeant.cli.workflow`](paigeant/cli.py)): Commands to list and examine workflows
- **Activity Executor** ([`paigeant.execute.ActivityExecutor`](paigeant/execute.py)): Worker process for executing agent activities
### CLI & Configuration
- **Command-line Interface** ([`paigeant.cli`](paigeant/cli.py)): Full-featured CLI for workflow management
- **Environment Configuration** ([`paigeant.config.Config`](paigeant/config.py)): Environment-based configuration with validation
- **Multiple Backends** ([`paigeant.config`](paigeant/config.py)): Seamless switching between persistence and transport backends

## Security & Authentication

### Message Security
- **OAuth 2.0 Integration** ([`paigeant.contracts.PaigeantMessage.obo_token`](paigeant/contracts.py)): On-behalf-of token support
- **JSON Web Signatures** ([`paigeant.contracts.PaigeantMessage.signature`](paigeant/contracts.py)): Message authenticity and tamper protection
- **Multi-tenant Support**: Secure isolation between workflows via token-based authentication

## Developer Experience

### API Design
- **FastAPI-style**: Familiar, intuitive API patterns with dependency injection
- **Type Safety**: Full Pydantic-based type hints throughout all modules
- **Error Handling**: Comprehensive error handling with structured logging
- **Async/Await**: Native async support in all transport and execution layers

### Testing & Debugging
- **Comprehensive Test Suite** ([`tests/unit/`](tests/unit/), [`tests/integration/`](tests/integration/)): Unit and integration tests
- **Mock Agents** ([`tests/fixtures/test_agents.py`](tests/fixtures/test_agents.py)): Test fixtures for development
- **Structured Logging**: Correlation ID tracking throughout execution flow
- **Local Development Mode**: In-memory transports and repositories for quick iteration

### Examples & Guides
- **Single Agent Examples** ([`guides/single_agent_example.py`](guides/single_agent_example.py)): Basic workflow patterns
- **Multi-Agent Examples** ([`guides/multi_agent_example.py`](guides/multi_agent_example.py)): Complex coordination scenarios
- **Dynamic Agent Examples** ([`guides/dynamic_multi_agent_example.py`](guides/dynamic_multi_agent_example.py)): Runtime workflow modification
- **Integration Examples** ([`examples/`](misc/examples/), [`misc/examples/`](misc/examples/)): Real-world usage patterns

## Extensibility Features

### Plugin Architecture
- **Custom Transports** ([`paigeant.transports.BaseTransport`](paigeant/transports/base.py)): Implement `BaseTransport` for new brokers
- **Custom Persistence** ([`paigeant.persistence.WorkflowRepository`](paigeant/persistence/repository.py)): Implement `WorkflowRepository` for new databases
- **Custom Agents** ([`paigeant.agent.wrapper.PaigeantAgent`](paigeant/agent/wrapper.py)): Extend `PaigeantAgent` for specialized behavior

### Framework Integration
- **Pydantic AI** (`pydantic_ai.Agent`): Built on top of `pydantic-ai` framework
- **Pydantic Models** (`pydantic.BaseModel`): Full Pydantic model support for data validation
- **Async Ecosystem**: Compatible with FastAPI, aiohttp, and other async frameworks

## Feature Matrix

| Feature Category | Development | Production | Enterprise |
|------------------|-------------|------------|------------|
| **Transports** | ✅ InMemory | ✅ Redis | 🔜 RabbitMQ, Kafka |
| **Persistence** | ✅ InMemory, SQLite | ✅ PostgreSQL | 🔜 MongoDB, Cassandra |
| **Security** | ✅ Basic Auth | ✅ OAuth 2.0, JWS | 🔜 RBAC, Audit Logs |
| **Observability** | ✅ Logging | ✅ Tracing | 🔜 Metrics, Dashboards |
| **Execution** | ✅ Sequential | ✅ Durable | 🔜 Parallel, Compensation |
| **Discovery** | ✅ Static | 🔜 Dynamic | 🔜 Service Mesh |

## Planned Features

### Near Term (v0.3.x)
- **Parallel Execution**: Scatter-gather patterns for concurrent execution
- **Enhanced Retry Logic**: Exponential backoff and dead letter queues
- **Dynamic Service Discovery**: Central registry for agent capabilities
- **Compensation Patterns**: Saga-style rollback for failed workflows

### Medium Term (v0.4.x)
- **Additional Transports**: RabbitMQ, Apache Kafka, Azure Service Bus
- **Advanced Persistence**: MongoDB, Cassandra, and custom adapters
- **Workflow Visualization**: Web UI for monitoring and debugging
- **Performance Optimization**: Connection pooling, batch processing

### Long Term (v1.0+)
- **Cross-Language Support**: JSON Schema for TypeScript, .NET, Rust integration
- **Enterprise Security**: RBAC, audit logging, compliance features
- **Advanced Orchestration**: Conditional branches, loops, timeouts
- **Cloud Native**: Kubernetes operators, Helm charts, auto-scaling

---

*This feature list reflects the current state of Paigeant v0.2.0. Features marked with 🔜 are planned for future releases.*