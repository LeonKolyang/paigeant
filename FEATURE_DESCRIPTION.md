- CLI tooling to manage workflow dispatch scripts
- Problem: Scripts to kick-off workflows are currently plain python and happen outside of the paigeant cli eco-system
- Solution: A cli command that finds workflows in the active directory or a given one, another command that executes a script
- Questions:
    -  what about the current workflows and workflow command? They are used to manage actively running workflows. More precise naming across these commands and the new ones is required.

## High-Level Implementation Plan

### CLI structure
#### current
- `paigeant execute <agent_name>` - Run ActivityExecutor worker for an agent
- `paigeant workflows` - List all workflows in repository 
- `paigeant workflow <correlation_id>` - Show details for specific workflow

#### extended design
- Commands managing agents:
    - `paigeant agent <command>`
- Commands managing workflows:
    - `paigeant workflow`
        - `paigeant workflow discover` -> workflow files with description - find workflows defined in the directory
        - `paigeant workflow dispatch <workflow_path>` -> correlation id - trigger a workflow
        - `paigeant workflow list` -> workflows with status - get workflows in the registry with status running, failing, done
        - `paigeant workflow show <correlation_id>` -> workflow run details - get details for a specific workflow run


### Solution Overview
- **Discovery**: `paigeant discover workflows` - AST-scan directories for WorkflowDispatcher patterns
- **Dispatch**: `paigeant dispatch run <script>` - Execute workflow scripts within CLI ecosystem  
- **Reorganization**: Rename existing commands (`workflows` → `status list`, `workflow` → `status show`)

### Architecture
- New CLI modules: `cli/discover.py`, `cli/dispatch.py`, `cli/status.py`
- Workflow scanner uses AST analysis to find dispatcher usage patterns
- Script executor handles safe execution with CLI configuration injection
- Leverage existing `agent/discovery.py` and configuration systems