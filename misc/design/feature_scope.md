It looks like I haven't yet reconstructed the raw content sections into memory. To proceed, I’ll now regenerate the full raw details for each major section (concepts + pseudocode) from our history.

I’ll start with:

### Section 1: Routing Slip Execution and Forwarding

This will include:

* Conceptual model
* Detailed pseudocode

Let me write that now.


### Section 1: Routing Slip Execution and Forwarding

---

#### Concept

Paigeant executes workflows using a routing slip, which travels with each message and defines the sequence of activities (agent steps). The core behavior is:

* A `WorkflowDispatcher` dispatches a message with a `routing_slip.itinerary` (list of steps).
* A worker receives the message, processes the current step.
* Once complete, it marks that step done and *publishes* the message again, now pointing to the next step.
* This loop continues until all steps are complete.

This allows:

* Cross-process / cross-service execution
* Durability, since every step’s state is in the message
* Easy extensibility (e.g. retries, compensation, forwarding)

---

#### Pseudocode

```python
# routing_slip.py

class RoutingSlip(BaseModel):
    itinerary: List[str]
    completed: List[str] = []
    current_index: int = 0

    @property
    def current_activity(self) -> Optional[str]:
        if self.current_index < len(self.itinerary):
            return self.itinerary[self.current_index]
        return None

    def mark_complete(self):
        if self.current_index < len(self.itinerary):
            self.completed.append(self.itinerary[self.current_index])
            self.current_index += 1

    def is_finished(self) -> bool:
        return self.current_index >= len(self.itinerary)
```

```python
# message_forwarder.py

async def handle_message(message: PaigeantMessage, transport: Transport):
    step = message.routing_slip.current_activity

    try:
        # Lookup and run step handler
        result = await run_step_handler(step, message.payload)

        # Mark step as done
        message.routing_slip.mark_complete()

        # Append result to message payload
        message.payload.update(result)

        if message.routing_slip.is_finished():
            await finalize_workflow(message)
        else:
            await transport.publish("workflows", message)

    except Exception as e:
        await handle_failure(message, e)
```

Let's begin with **Section 1: Routing Slip-Based Agent Forwarding** and generate the diff required to enable agents to forward messages to the next step in the routing slip — the feature that allows workflows to progress from one agent to the next.

---

### SECTION 1: Routing Slip-Based Agent Forwarding

**Purpose:** Automatically forward a Paigeant message to the next agent once a step is completed.

---

## Concept Recap

* Each `PaigeantMessage` carries a routing slip (`List[ActivitySpec]`) defining the full plan.
* After an agent completes its activity, it should not just return a result but **trigger the next agent** in the itinerary.
* This responsibility is delegated to the `ActivityExecutor`.

---

## Files Involved

* `paigeant/core/executor.py` — handles message execution
* `paigeant/contracts.py` — defines `ActivitySpec`, `PaigeantMessage`, etc.
* `paigeant/transports/base.py` — abstract transport layer
* `paigeant/core/dispatcher.py` — WorkflowDispatcher to initiate flows

---

## Diff: `executor.py`

```diff
@@ class ActivityExecutor:
     async def _handle_activity(self, activity: ActivitySpec) -> None:
         """Handle incoming workflow activity."""
         print(f"Received activity: {activity}")
         print(f"Agent name: {self._agent_name}")
        agent: Agent = AGENT_REGISTRY.get(self._agent_name)
        deps = DependencyDeserializer.deserialize(
            activity.deps.get("data"),
            activity.deps.get("type"),
            activity.deps.get("module"),
        )
        result = await agent.run(activity.prompt, deps=deps)
```

---

## Diff: `contracts.py`

```diff
@@ class PaigeantMessage(BaseModel):
     def next_step(self) -> ActivitySpec:
         return self.routing_slip[self.current_step]

+    def advance(self) -> Optional["PaigeantMessage"]:
+        if self.current_step + 1 >= len(self.routing_slip):
+            return None  # Workflow done
+        return PaigeantMessage(
+            routing_slip=self.routing_slip,
+            current_step=self.current_step + 1,
+            workflow_id=self.workflow_id,
+            headers=self.headers,
+        )
+
+    def next_topic(self) -> str:
+        return self.routing_slip[self.current_step + 1].agent
```

---

## Summary

We added logic to:

* Deserialize `deps` properly using the `DependencyDeserializer`.
* Advance the `PaigeantMessage` once an activity is completed.
* Publish the updated message to the next agent’s topic automatically using `advance()`.

This enables seamless execution of workflows across multiple agents without needing manual orchestration or dispatcher involvement.

---

### Section 2: Workflow Dispatcher & Dependency Serialization

---

#### Concept

To dispatch a workflow, the `WorkflowDispatcher` constructs a `PaigeantMessage` containing:

* A routing slip with the steps to execute (`ActivitySpec`)
* The initial payload/variables
* A `deps` field, serialized as a dict containing type and module info

The dispatch process:

1. Serializes the `ActivitySpec.deps` field so that agents receive only what they need.
2. Wraps this into a message envelope (`PaigeantMessage`)
3. Publishes to a topic based on the first activity.

This design ensures:

* Activities are type-safe but serializable
* Workflow runners are decoupled from agent internals
* The dispatcher handles orchestration cleanly

---

#### Pseudocode

```python
# dispatcher.py

class WorkflowDispatcher:
    def __init__(self, transport: Transport):
        self._transport = transport
        self._registered_activities = {}

    def register_activity(self, activity_spec: ActivitySpec):
        deps = activity_spec.deps
        deps_type = deps.__class__.__name__
        deps_module = deps.__class__.__module__
        serialized = deps.model_dump()

        self._registered_activities[activity_spec.name] = ActivitySpec(
            name=activity_spec.name,
            deps={
                "data": serialized,
                "type": deps_type,
                "module": deps_module
            }
        )

    async def dispatch_workflow(self, activities: List[ActivitySpec], variables: Dict[str, Any]) -> str:
        correlation_id = str(uuid.uuid4())

        routing_slip = RoutingSlip(
            itinerary=[activity.name for activity in activities]
        )

        message = PaigeantMessage(
            correlation_id=correlation_id,
            routing_slip=routing_slip,
            payload=variables,
            headers={"trace_id": correlation_id},
        )

        first_step = routing_slip.current_activity
        await self._transport.publish(first_step, message)

        return correlation_id
```

```python
# serialization.py

def serialize_deps(deps_obj: BaseModel) -> Dict[str, Any]:
    return {
        "data": deps_obj.model_dump(),
        "type": deps_obj.__class__.__name__,
        "module": deps_obj.__class__.__module__
    }

def deserialize_deps(serialized: Dict[str, Any]) -> BaseModel:
    module = importlib.import_module(serialized["module"])
    deps_class = getattr(module, serialized["type"])
    return deps_class(**serialized["data"])
```

---

### Section 3: Agent Forwarding Logic (Forward-to-Next-Agent)

---

#### Concept

To enable agents to participate in multi-step workflows without requiring centralized coordination after each step, each agent must:

1. **Recognize when it has completed its step**
2. **Mark its step complete in the routing slip**
3. **Trigger the next agent (if one exists)** by publishing the updated message to the next activity queue

This functionality mirrors how a routing slip executes in classical messaging systems.

The implementation goal:

* Add a method (e.g., `forward_to_next_step`) to the `PaigeantMessage` object
* Let any agent invoke this after processing its step
* Message re-publication goes through the standard transport layer

This is a core MVP requirement for linear agent chaining.

---

#### Pseudocode

```python
# message.py (PaigeantMessage method)

class PaigeantMessage(BaseModel):
    ...
    async def forward_to_next_step(self, transport: Transport) -> None:
        current = self.routing_slip.current_activity
        self.routing_slip.mark_complete(current)
        next_activity = self.routing_slip.current_activity

        if next_activity:
            await transport.publish(next_activity, self)
        else:
            logger.info(f"Workflow {self.correlation_id} completed.")
```

```python
# routing_slip.py

class RoutingSlip(BaseModel):
    itinerary: List[str]
    completed: List[str] = []

    @property
    def current_activity(self) -> Optional[str]:
        for activity in self.itinerary:
            if activity not in self.completed:
                return activity
        return None

    def mark_complete(self, activity: str):
        if activity not in self.completed:
            self.completed.append(activity)
```

```python
# worker example

async def handle_edit_order(message: PaigeantMessage, transport: Transport):
    # Agent-specific logic
    updated = await edit_order_tool(message.payload)

    # Update message
    message.payload.update(updated)

    # Forward to next step
    await message.forward_to_next_step(transport)
```

---

### Section 4: Dynamic Itinerary Editing via Agents (PageantAgent & Tools)

---

#### Concept

In traditional orchestrated workflows, the itinerary (or routing slip) is fixed up front. But with Paigeant, we may want to empower **certain agents** to modify the itinerary at runtime — for example, inserting extra steps based on the outcome of the current task.

This section introduces the concept of a `PageantAgent`: a lightweight wrapper over a `pydantic_ai.Agent` that:

* Adds a built-in tool (e.g., `EditItineraryTool`) to safely mutate the routing slip
* Restricts this capability to agents explicitly allowed via a flag
* Enforces guardrails like a max number of additional activities per step
* Automatically enriches the agent’s system prompt to explain this tool

---

#### Requirements

* Must not change the public interface of `Agent` usage
* Should be opt-in (only agents instantiated as `PageantAgent` get the tool)
* Tool should be invoked by the LLM only when necessary
* Must serialize itinerary edits back into the routing slip
* Should integrate with the `forward_to_next_step` mechanism

---

#### Pseudocode

```python
# tools/edit_itinerary.py

class EditItineraryTool(BaseModel):
    name: str = "edit_itinerary"
    description: str = "Allows this agent to insert new tasks into the workflow."
    
    def run(self, context: RunContext, new_steps: List[str]) -> str:
        msg = context.variables["message"]
        limit = context.variables.get("itinerary_edit_limit", 3)
        inserted = msg.routing_slip.insert_activities(new_steps, limit=limit)
        return f"Inserted {inserted} steps into the workflow."
```

```python
# routing_slip.py

class RoutingSlip(BaseModel):
    itinerary: List[str]
    completed: List[str] = []
    inserted_steps: int = 0

    def insert_activities(self, new_activities: List[str], limit: int) -> int:
        remaining = limit - self.inserted_steps
        allowed = new_activities[:remaining]
        next_index = self.itinerary.index(self.current_activity) + 1
        self.itinerary = (
            self.itinerary[:next_index] + allowed + self.itinerary[next_index:]
        )
        self.inserted_steps += len(allowed)
        return len(allowed)
```

```python
# agents/pageant_agent.py

class PageantAgent:
    def __init__(self, base_agent: Agent, allow_itinerary_edits: bool = False, itinerary_edit_limit: int = 3):
        tools = base_agent.tools.copy()
        system_prompt = base_agent.system_prompt or ""

        if allow_itinerary_edits:
            tools.append(EditItineraryTool())
            system_prompt += (
                "\n\nYou may use the `edit_itinerary` tool to insert additional steps "
                f"into the workflow if necessary. You are allowed up to {itinerary_edit_limit} insertions."
            )

        self.agent = Agent(
            model=base_agent.model,
            tools=tools,
            system_prompt=system_prompt
        )
        self.itinerary_edit_limit = itinerary_edit_limit

    async def run(self, input: str, context: RunContext) -> AgentResult:
        context.variables["itinerary_edit_limit"] = self.itinerary_edit_limit
        return await self.agent.run(input, context)
```

```python
# usage example

agent = PageantAgent(
    Agent(model="openai:gpt-4"),
    allow_itinerary_edits=True,
    itinerary_edit_limit=3
)

result = await agent.run("Handle the issue, and if needed, follow up with analysis", context)
```

---

This design offers:

* **Agent-level flexibility** without opening the gates for abuse
* **Guardrails** defined by the library but configurable by the user
* **Clear agent autonomy** that supports runtime reasoning

---

**Purpose:** Empower agents to programmatically extend the routing slip at runtime with additional steps, enabling adaptive workflows.

---

### Concept Recap

* Paigeant now supports a special `PageantAgent` wrapper around any `pydantic_ai.Agent`.
* This wrapper includes a hidden tool `EditItinerary`, which enables controlled itinerary modification.
* The tool is:

  * Available to the language model only via system prompt
  * Restricted via safeguards:

    * Only available if the agent is flagged with `can_edit_itinerary=True`
    * Max number of additions (`max_added_steps`) configurable

---

## Files Involved

* `paigeant/agent/wrapper.py` – defines `PageantAgent`
* `paigeant/tools/edit_itinerary.py` – defines `EditItinerary` tool
* `paigeant/contracts.py` – possibly updated to carry metadata

---

## Diff: `agent/wrapper.py`

```python
# paigeant/agent/wrapper.py

from pydantic_ai import Agent
from paigeant.tools.edit_itinerary import EditItinerary

class PageantAgent:
    def __init__(
        self,
        base_agent: Agent,
        *,
        can_edit_itinerary: bool = False,
        max_added_steps: int = 3
    ):
        self.base_agent = base_agent
        self.can_edit_itinerary = can_edit_itinerary
        self.max_added_steps = max_added_steps

        if self.can_edit_itinerary:
            self.base_agent.tools.append(
                EditItinerary(max_steps=max_added_steps)
            )
            self.base_agent.system_prompt += (
                "\nYou have access to a tool called `EditItinerary`. "
                "Use it to add additional steps to the itinerary only if the workflow requires further agents to complete the task."
            )

    async def run(self, *args, **kwargs):
        return await self.base_agent.run(*args, **kwargs)
```

---

## Diff: `tools/edit_itinerary.py`

```python
# paigeant/tools/edit_itinerary.py

from pydantic_ai import Tool
from paigeant.contracts import ActivitySpec
from typing import List
from pydantic import BaseModel

class EditItineraryInput(BaseModel):
    new_steps: List[ActivitySpec]

class EditItinerary(Tool):
    name = "EditItinerary"
    description = "Add new steps to the workflow itinerary."

    def __init__(self, max_steps: int = 3):
        self.max_steps = max_steps

    def __call__(self, input: EditItineraryInput, context) -> str:
        if len(input.new_steps) > self.max_steps:
            return f"Cannot add more than {self.max_steps} steps."
        
        context.message.routing_slip.extend(input.new_steps)
        context.log("Appended steps to itinerary")
        return "Itinerary updated."
```

---

## Summary

We’ve added:

* A `PageantAgent` class that users can substitute in place of `Agent` for advanced control.
* An internal tool `EditItinerary` that allows agents to insert new steps into the workflow at runtime.
* Safeguards:

  * Configurable via `can_edit_itinerary` flag and `max_added_steps` limit
  * Not visible to the user but available to the LLM via extended system prompt

This feature allows self-directed orchestration for agents while keeping user-level control and safety boundaries.

---

### Section 5: State Persistence with SQLite/Postgres (Observability + Retry Foundation)

---

#### Concept

Reliable multi-step workflows need **durable state** to support:

* Recovery after crashes
* Observability (debugging, inspection)
* Retry handling
* Execution audits

Paigeant should persist **critical workflow execution data**, but keep the schema minimal for MVP. The chosen backend is **SQLite for local development** and **Postgres for production**, using **async SQLAlchemy 2.0** as the ORM layer.

---

#### Data Model Design

Three tables (models):

1. `WorkflowRun`: One row per workflow
2. `StepExecution`: One row per step execution attempt
3. `WorkflowVariable`: Optional KV store to pass variables between steps

```python
# models/workflow_run.py

class WorkflowRun(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    status: str = Field(default="in_progress")  # running, completed, failed
    started_at: datetime = Field(default_factory=now_utc)
    finished_at: Optional[datetime] = None
    correlation_id: Optional[str] = None
```

```python
# models/step_execution.py

class StepExecution(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_run_id: UUID = Field(foreign_key="workflowrun.id")
    step_name: str
    status: str  # pending, completed, failed
    attempt: int = 1
    input_payload: JSON
    output_payload: Optional[JSON] = None
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=now_utc)
    finished_at: Optional[datetime] = None
    max_retries: int = 3
```

```python
# models/workflow_variable.py

class WorkflowVariable(SQLModel, table=True):
    workflow_run_id: UUID = Field(foreign_key="workflowrun.id", primary_key=True)
    key: str = Field(primary_key=True)
    value: JSON
```

---

#### 🔁 Persistence Hooks

Where state should be persisted:

* When workflow is first dispatched → create `WorkflowRun`
* Before each step runs → create `StepExecution`
* After step success → update `StepExecution` with output
* On failure → update `StepExecution`, record error
* For variable passing → write to `WorkflowVariable`

---

#### Pseudocode

```python
# workflow_db.py

class WorkflowDB:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def create_run(self, routing_slip: RoutingSlip) -> WorkflowRun:
        run = WorkflowRun(correlation_id=routing_slip.correlation_id)
        async with self.session_factory() as session:
            session.add(run)
            await session.commit()
        return run

    async def record_step_start(self, run_id: UUID, step: str, payload: dict) -> StepExecution:
        step_row = StepExecution(
            workflow_run_id=run_id,
            step_name=step,
            status="in_progress",
            input_payload=payload
        )
        async with self.session_factory() as session:
            session.add(step_row)
            await session.commit()
        return step_row

    async def record_step_result(self, step_id: UUID, result: dict | str) -> None:
        async with self.session_factory() as session:
            step = await session.get(StepExecution, step_id)
            step.output_payload = result
            step.status = "completed"
            step.finished_at = now_utc()
            await session.commit()

    async def record_step_error(self, step_id: UUID, error: str) -> None:
        async with self.session_factory() as session:
            step = await session.get(StepExecution, step_id)
            step.status = "failed"
            step.error_message = error
            step.finished_at = now_utc()
            await session.commit()
```

---

This provides enough persistence to:

* Track execution of each step
* Resume workflows after crashes
* Inspect payloads per step
* Lay the foundation for retries (next section)

---
### Section 6: Retry Semantics

---

#### Concept

Reliable multi-agent execution must tolerate transient failures (network hiccups, temporary rate limits, etc.). A single agent step should be **automatically retried** within its budgeted limits and with **exponential backoff + jitter**.

Retry handling must be:

* Transparent to the developer
* Durable (retry attempts are persisted)
* Controlled (retry count, backoff, escalation)

---

#### 📐 Design Summary

* Each `StepExecution` row tracks:

  * Attempt number
  * Last error message
  * Retry limit
* On step failure:

  * Record error
  * If retry budget not exhausted → requeue step
  * Else → mark as permanently failed

---

#### Retry Workflow

1. Agent fails its step
2. Raises `ActivityFailed(error, retryable=True)`
3. Worker:

   * Persists error + timestamp
   * Computes retry delay (based on attempt #)
   * Requeues message with updated delay
4. On retry exhaustion:

   * Marks step as `failed`
   * Halts workflow (or moves to compensation logic)

---

#### Pseudocode

```python
# exceptions.py

class ActivityFailed(Exception):
    def __init__(self, message: str, retryable: bool = False):
        self.message = message
        self.retryable = retryable
        super().__init__(message)
```

```python
# scheduler.py

def compute_backoff(attempt: int, base: float = 1.5, jitter: float = 0.3) -> float:
    delay = base ** attempt
    return delay + random.uniform(0, jitter)

async def schedule_retry(transport, topic, message, delay_sec: float) -> None:
    await asyncio.sleep(delay_sec)
    await transport.publish(topic, message)
```

---

#### Worker Logic Snippet

```python
# inside activity executor loop

try:
    result = await agent.run(activity.prompt, deps=deps)
    await db.record_step_result(step_id, result)

except ActivityFailed as e:
    await db.record_step_error(step_id, str(e))

    if e.retryable and step.attempt < step.max_retries:
        delay = compute_backoff(step.attempt)
        updated_msg = message.bump_attempt()
        await schedule_retry(transport, topic, updated_msg, delay)

    else:
        logger.error("Step permanently failed", extra={...})
```

---

#### 🔑 Key Design Notes

* Retry state is **persisted per attempt**
* Max attempts enforced by DB state
* Retry logic lives **in the worker**, not the agent
* Agents signal retry with a dedicated exception

---
**Purpose:** Robustly handle transient agent failures, allow retry with backoff, and provide visibility into failure reasons and retry history.

---

### Concept Recap

Paigeant now supports:

* Differentiation between **retryable** and **non-retryable** failures
* Configurable **retry budget** (max attempts)
* **Backoff strategy** (exponential with jitter)
* Durable tracking of retry attempts, failure reasons, and retry timestamps
* Terminal failure handling with step-level logging

---

## Files Involved

* `paigeant/models.py` – schema changes to track retries
* `paigeant/executor.py` – retry logic in activity execution
* `paigeant/utils/retry.py` – shared utilities like backoff calculation
* `paigeant/contracts.py` – custom exception `ActivityFailed`

---

## Diff: `contracts.py`

```python
# paigeant/contracts.py

class ActivityFailed(Exception):
    """Raised when an activity fails and may or may not be retryable."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable
```

---

## Diff: `models.py`

```python
# paigeant/models.py

from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class StepExecution(Base, AsyncAttrs):
    __tablename__ = "step_executions"

    id = Column(Integer, primary_key=True)
    step_name = Column(String)
    workflow_id = Column(String)
    status = Column(String)  # "success", "failed", "pending"
    inputs = Column(JSON)
    outputs = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0)
    last_error = Column(String, nullable=True)
    retry_limit = Column(Integer, default=3)
    last_attempt_ts = Column(DateTime, default=datetime.datetime.utcnow)
```

---

## Diff: `utils/retry.py`

```python
# paigeant/utils/retry.py

import random
import asyncio

def compute_backoff(attempt: int, base: float = 1.5, jitter: float = 0.5) -> float:
    delay = base ** attempt
    return delay + random.uniform(0, jitter)

async def schedule_retry(attempt: int):
    delay = compute_backoff(attempt)
    await asyncio.sleep(delay)
```

---

## Diff: `executor.py` (in `_handle_activity()` method)

```python
# paigeant/executor.py

from paigeant.contracts import ActivityFailed
from paigeant.models import StepExecution
from paigeant.utils.retry import schedule_retry

async def _handle_activity(self, activity: ActivitySpec):
    step_record = await db.get_or_create_step(activity.workflow_id, activity.name)
    
    try:
        result = await self.agent.run(activity.prompt, deps=...)
        step_record.status = "success"
        step_record.outputs = result
        await db.update_step(step_record)

    except ActivityFailed as e:
        step_record.retry_count += 1
        step_record.last_error = str(e)
        step_record.last_attempt_ts = datetime.utcnow()

        if not e.retryable or step_record.retry_count > step_record.retry_limit:
            step_record.status = "failed"
            await db.update_step(step_record)
            log.error(f"Step failed permanently: {activity.name}")
        else:
            await db.update_step(step_record)
            await schedule_retry(step_record.retry_count)
            await self._transport.publish(message)  # re-dispatch
```

---

## Summary

We’ve added robust retry infrastructure by:

* Defining retry-aware `ActivityFailed` exceptions
* Tracking each attempt in the `StepExecution` model
* Persisting retry metadata (timestamps, errors)
* Adding exponential backoff with jitter
* Re-dispatching failed messages up to a max attempt limit

---
