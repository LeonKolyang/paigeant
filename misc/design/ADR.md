# Architecture Decision Records (ADR)

## ADR-001: Agent Output Passing Strategy

**Date**: 2025-07-31  
**Status**: Accepted  
**Context**: How to pass the output of one agent to the next in workflow execution.

### Decision
Use dependency injection at message reception rather than modifying the routing slip with serialized outputs.

### Rationale
- **Loose Coupling**: Agents remain unaware of workflow mechanics and can be tested independently
- **Separation of Concerns**: Execution engine handles orchestration, agents focus on business logic  
- **Transport Agnostic**: Works with any messaging system without protocol changes
- **Message Design**: Follows command/query separation - messages carry data, agents process it
- **Scalability**: Payload approach allows flexible storage strategies (memory, database, cache)

### Implementation
- Agent outputs stored in message payload (`Dict[str, Any]`)
- Previous outputs injected into `WorkflowDependencies` at reception time
- Agents access via `ctx.deps.previous_output.output` or extend `WorkflowDependencies`

### Alternatives Considered
- **Routing Slip Modification**: Update next agent's serialized deps with current output
  - Rejected: Creates tight coupling between agents and workflow engine
  - Rejected: Violates single responsibility principle
  - Rejected: Makes message routing dependent on business logic
## ADR-002: Persisting Workflow State with Repository Registry

**Date**: 2025-08-27
**Status**: Accepted
**Context**: Phase 4 of the persistence roadmap requires verifying durable workflow state and idempotent updates.

### Decision
- Use a workflow repository as a registry to persist routing slips, payloads and step history during integration tests.
- Enforce uniqueness on `(correlation_id, step_name, run_id)` and ignore duplicate `mark_step_started` calls for the same run to ensure idempotent step tracking while allowing retries.

### Rationale
- Guarantees crash recovery and auditing through persisted state.
- Prevents duplicate step records when messages are retried.
- Demonstrates repository usage in existing workflows without altering business logic.

### Implementation
- Added `run_id` column and `INSERT OR IGNORE` semantics to SQLite repository, with matching changes for PostgreSQL.
- Extended single and multi‑agent integration tests to use `SQLiteWorkflowRepository` and assert persisted workflow state and activity registry availability.
- Added repository unit tests covering duplicate updates and multiple step runs.

### Alternatives Considered
- Allowing duplicate step inserts and cleaning them later – rejected due to harder querying and audit noise.

