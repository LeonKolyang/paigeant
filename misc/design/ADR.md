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
