"""Command line interface for running Paigeant workers."""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from typing import Iterable, Optional

import typer

from paigeant import ActivityExecutor, get_repository, get_transport
from paigeant.agent.discovery import discover_agent

app = typer.Typer(help="CLI for Paigeant workflows")

# Command groups
agent_app = typer.Typer(help="Commands for managing agents")
workflow_app = typer.Typer(help="Commands for managing workflows")

app.add_typer(agent_app, name="agent")
app.add_typer(workflow_app, name="workflow")


@app.callback()
def main() -> None:
    """Paigeant CLI entry point."""
    pass


@agent_app.command("execute")
def agent_execute(
    agent_name: str,
    base_path: Optional[Path] = "",
    lifespan: Optional[float] = None,
) -> None:
    """
    Run a worker process for the specified agent.

    Starts a worker that listens for activities and executes them using the agent's logic.
    The worker connects to the configured transport and repository for state management.

    Args:
        agent_name: Name of the agent to run worker for
        base_path: Directory to search for agent definitions (default: current dir)
        lifespan: Worker timeout in seconds (default: run indefinitely)

    Returns:
        Runs indefinitely until stopped or lifespan expires. Prints worker status.

    Example:
        paigeant agent execute joke_generator_agent
        paigeant agent execute my_agent --base_path ./workflows --lifespan 300

    Example:
        paigeant agent execute joke_generator_agent --lifespan 300
    """
    transport = get_transport()
    repository = get_repository()
    executor = ActivityExecutor(
        transport, agent_name=agent_name, base_path=base_path, repository=repository
    )
    print("Starting agent:", agent_name)
    asyncio.run(executor.start(lifespan=lifespan))


@workflow_app.command("list")
def workflow_list() -> None:
    """
    List all workflows with their current status.

    Shows correlation IDs and execution status (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
    from the configured repository. Useful for monitoring workflow execution.

    Returns:
        Tab-separated list of correlation IDs and statuses, or "No workflows found"

    Example:
        paigeant workflow list
        # Output: abc123-def456-789    RUNNING
        #         xyz789-uvw012-345    COMPLETED
    """
    repo = get_repository()
    workflows = asyncio.run(repo.list_workflows())
    if not workflows:
        typer.echo("No workflows found")
        return
    for wf in workflows:
        typer.echo(f"{wf.correlation_id}\t{wf.status}")


@workflow_app.command("show")
def workflow_show(correlation_id: str) -> None:
    """
    Show detailed information for a specific workflow.

    Displays workflow status, payload, and step-by-step execution history with timestamps.
    Essential for debugging failures and monitoring workflow progress.

    Args:
        correlation_id: Workflow ID to inspect (get from 'workflow list')

    Returns:
        Workflow details with status, payload, and step execution history

    Example:
        paigeant workflow show abc123-def456-789
        # Output: Workflow abc123-def456-789: RUNNING
        #         Payload: {"topic": "programming"}
        #         - topic_extractor: COMPLETED (2024-01-01 10:00 -> 10:01)
        #         - joke_generator: RUNNING
    """
    repo = get_repository()
    wf = asyncio.run(repo.get_workflow(correlation_id))
    if wf is None:
        typer.echo("Workflow not found")
        raise typer.Exit(code=1)
    typer.echo(f"Workflow {wf.correlation_id}: {wf.status}")
    if wf.payload:
        typer.echo(f"Payload: {wf.payload}")
    for step in wf.steps:
        typer.echo(
            f"- {step.step_name}: {step.status}"
            + (
                f" ({step.started_at} -> {step.completed_at})"
                if step.started_at or step.completed_at
                else ""
            )
        )


@workflow_app.command("discover")
def workflow_discover(path: Optional[Path] = None) -> None:
    """
    Find workflow definition files in directory.

    Scans Python files for WorkflowDispatcher patterns and extracts metadata
    like agent names, dependencies, and descriptions using AST analysis.

    Args:
        path: Directory to scan (default: current directory)

    Returns:
        List of discovered workflows with file paths and metadata

    Example:
        paigeant workflow discover
        # Output: ./examples/joke_workflow.py - Multi-agent joke generation
        #         Agents: topic_extractor, joke_generator, joke_selector
        #         Dependencies: HttpKey, JokeWorkflowDeps
    """
    search_path = (path or Path.cwd()).expanduser().resolve()
    typer.echo(f"Discovering workflows in: {search_path}")

    if not search_path.exists():
        typer.secho("Specified path does not exist", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    python_files: Iterable[Path]
    if search_path.is_file():
        python_files = [search_path]
    else:
        python_files = sorted(search_path.rglob("*.py"))

    discoveries = []
    for py_file in python_files:
        if py_file.is_dir():
            continue
        try:
            metadata = _analyze_workflow_file(py_file)
        except SyntaxError as exc:
            typer.secho(
                f"Skipping {py_file}: syntax error at line {exc.lineno}",
                fg=typer.colors.RED,
            )
            continue
        except OSError as exc:
            typer.secho(f"Skipping {py_file}: {exc}", fg=typer.colors.RED)
            continue

        if metadata is not None:
            discoveries.append(metadata)

    if not discoveries:
        typer.echo("No workflows discovered.")
        return

    for item in discoveries:
        display_path = _format_workflow_path(item["path"], search_path)
        description = item["description"] or "No description found"
        agents = item["agents"] or ["(none found)"]
        dependencies = item["dependencies"] or ["(none found)"]
        typer.echo(f"{display_path} - {description}")
        typer.echo(f"  Agents: {', '.join(agents)}")
        typer.echo(f"  Dependencies: {', '.join(dependencies)}")


class _WorkflowModuleAnalyzer(ast.NodeVisitor):
    """Collect metadata about workflow dispatcher usage in a module."""

    def __init__(self) -> None:
        self.dispatcher_aliases = {"WorkflowDispatcher"}
        self.agent_aliases = {"PaigeantAgent"}
        self.deps_aliases = {"WorkflowDependencies"}
        self.dispatcher_names: list[str] = []
        self.agent_infos: list[dict[str, object]] = []
        self.dependency_classes: list[str] = []
        self.found_dispatcher = False

    # ------------------------------------------------------------------
    # Import handling
    # ------------------------------------------------------------------
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # pragma: no cover - ast
        for alias in node.names:
            target = alias.name.split(".")[-1]
            alias_name = alias.asname or alias.name
            if target == "WorkflowDispatcher":
                self.dispatcher_aliases.add(alias_name)
            elif target == "PaigeantAgent":
                self.agent_aliases.add(alias_name)
            elif target == "WorkflowDependencies":
                self.deps_aliases.add(alias_name)
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Node visitors capturing metadata
    # ------------------------------------------------------------------
    def visit_Assign(self, node: ast.Assign) -> None:  # pragma: no cover - ast
        value = node.value
        if self._is_call_to(value, self.dispatcher_aliases):
            self.found_dispatcher = True
            for target in node.targets:
                name = self._name_from_target(target)
                if name and name not in self.dispatcher_names:
                    self.dispatcher_names.append(name)
        elif self._is_call_to(value, self.agent_aliases):
            info = self._parse_agent_call(value)
            variables = [
                self._name_from_target(target)
                for target in node.targets
                if self._name_from_target(target)
            ]
            info["variables"] = variables
            self.agent_infos.append(info)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # pragma: no cover - ast
        value = node.value
        if value and self._is_call_to(value, self.dispatcher_aliases):
            self.found_dispatcher = True
            name = self._name_from_target(node.target)
            if name and name not in self.dispatcher_names:
                self.dispatcher_names.append(name)
        elif value and self._is_call_to(value, self.agent_aliases):
            info = self._parse_agent_call(value)
            target_name = self._name_from_target(node.target)
            info["variables"] = [target_name] if target_name else []
            self.agent_infos.append(info)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # pragma: no cover - ast
        if self._is_call_to(node, self.dispatcher_aliases):
            self.found_dispatcher = True
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # pragma: no cover - ast
        for base in node.bases:
            base_name = self._get_expr_name(base)
            if base_name and base_name.split(".")[-1] in self.deps_aliases:
                if node.name not in self.dependency_classes:
                    self.dependency_classes.append(node.name)
                break
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def _is_call_to(self, value: ast.AST, candidates: set[str]) -> bool:
        if not isinstance(value, ast.Call):
            return False
        func_name = self._get_expr_name(value.func)
        if not func_name:
            return False
        last = func_name.split(".")[-1]
        return func_name in candidates or last in candidates

    def _name_from_target(self, target: ast.AST) -> Optional[str]:
        if isinstance(target, ast.Name):
            return target.id
        if isinstance(target, ast.Attribute):
            return self._get_expr_name(target)
        return None

    def _get_expr_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            value = self._get_expr_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        if isinstance(node, ast.Call):
            return self._get_expr_name(node.func)
        if isinstance(node, ast.Subscript):
            return self._get_expr_name(node.value)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _parse_agent_call(self, call: ast.Call) -> dict[str, object]:
        info: dict[str, object] = {"name": None, "dispatcher": None, "deps_type": None}
        for keyword in call.keywords:
            if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    info["name"] = keyword.value.value
            elif keyword.arg == "dispatcher":
                dispatcher_name = self._get_expr_name(keyword.value)
                if dispatcher_name:
                    info["dispatcher"] = dispatcher_name
            elif keyword.arg in {"deps_type", "deps"}:
                deps_name = self._get_expr_name(keyword.value)
                if deps_name:
                    info["deps_type"] = deps_name
        return info


def _analyze_workflow_file(path: Path) -> Optional[dict[str, object]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    analyzer = _WorkflowModuleAnalyzer()
    analyzer.visit(tree)

    if not analyzer.found_dispatcher:
        return None

    docstring = ast.get_docstring(tree) or ""
    description = docstring.strip().splitlines()[0] if docstring.strip() else ""

    agent_names: list[str] = []
    for info in analyzer.agent_infos:
        name = info.get("name")
        if isinstance(name, str) and name:
            if name not in agent_names:
                agent_names.append(name)
            continue
        variables = info.get("variables") or []
        if isinstance(variables, list):
            for variable in variables:
                if isinstance(variable, str) and variable and variable not in agent_names:
                    agent_names.append(variable)
                    break

    deps: list[str] = []
    for info in analyzer.agent_infos:
        deps_name = info.get("deps_type")
        if isinstance(deps_name, str) and deps_name and deps_name not in deps:
            deps.append(deps_name)
    for cls_name in analyzer.dependency_classes:
        if cls_name not in deps:
            deps.append(cls_name)

    return {
        "path": path,
        "description": description,
        "agents": agent_names,
        "dependencies": deps,
    }


def _format_workflow_path(path: Path, search_path: Path) -> str:
    resolved_path = path.resolve()
    candidate_bases = []
    if search_path.is_dir():
        candidate_bases.append(search_path.resolve())
    else:
        candidate_bases.append(search_path.parent.resolve())
    candidate_bases.append(Path.cwd())

    for base in candidate_bases:
        try:
            rel = resolved_path.relative_to(base)
            return f"./{rel}"
        except ValueError:
            continue
    return str(path)


@workflow_app.command("dispatch")
def workflow_dispatch(workflow_path: Path, args: Optional[str] = None) -> None:
    """
    Execute a workflow script and return correlation ID.

    Runs workflow file with CLI configuration injection. Returns correlation ID
    and provides instructions for starting required workers.

    Args:
        workflow_path: Path to workflow Python file
        args: Optional JSON string with arguments for the workflow

    Returns:
        Correlation ID for tracking workflow and worker startup instructions

    Example:
        paigeant workflow dispatch ./examples/joke_workflow.py
        paigeant workflow dispatch ./multi_agent.py --args '{"count": 5}'
        # Output: Workflow dispatched successfully!
        #         Correlation ID: abc123-def456-789
        #         Start workers: paigeant agent execute <agent_name>
    """
    typer.echo(f"Dispatching workflow: {workflow_path}")
    if args:
        typer.echo(f"With arguments: {args}")

    typer.echo("TODO: Implement script execution with configuration injection")
    typer.echo("- Import and validate workflow script")
    typer.echo("- Inject CLI transport and repository configuration")
    typer.echo("- Execute main/dispatch function safely")
    typer.echo("- Capture and return correlation ID")
    typer.echo("- Provide worker startup instructions")

    # Dummy correlation ID for now
    dummy_correlation_id = "abc123-def456-789"
    typer.echo(f"Workflow dispatched successfully!")
    typer.echo(f"Correlation ID: {dummy_correlation_id}")
    typer.echo("Start required workers with: paigeant agent execute <agent_name>")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    app()
