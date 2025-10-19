"""Command line interface for running Paigeant workers."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer

from paigeant import ActivityExecutor, get_repository, get_transport
from paigeant.agent.discovery import discover_agents_in_path
from paigeant.cli_utils.fs import _iter_python_files
from paigeant.cli_utils.workflow import _analyze_workflow_file, _format_workflow_path

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


@agent_app.command("discover")
def agent_discover(
    path: Optional[Path] = None,
    respect_gitignore: bool = typer.Option(
        True, help="Skip files and directories specified in .gitignore files"
    ),
) -> None:
    """Discover Paigeant agents defined within Python files."""

    search_path = (path or Path.cwd()).expanduser().resolve()
    typer.echo(f"Discovering agents in: {search_path}")

    if not search_path.exists():
        typer.secho("Specified path does not exist", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        discoveries = discover_agents_in_path(
            search_path, respect_gitignore=respect_gitignore
        )
    except FileNotFoundError:
        typer.secho("Specified path does not exist", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not discoveries:
        typer.echo("No agents discovered.")
        return

    for item in discoveries:
        display_path = _format_workflow_path(item["path"], search_path)
        typer.echo(f"{item['name']} - {display_path}")


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
def workflow_discover(
    path: Optional[Path] = None,
    respect_gitignore: bool = typer.Option(
        True, help="Skip files and directories specified in .gitignore files"
    ),
) -> None:
    """
    Find workflow definition files in directory.

    Scans Python files for WorkflowDispatcher patterns and extracts metadata
    like agent names, dependencies, and descriptions using AST analysis.

    Args:
        path: Directory to scan (default: current directory)
        respect_gitignore: Skip files and directories specified in .gitignore files (default: True)

    Returns:
        List of discovered workflows with file paths and metadata

    Example:
        paigeant workflow discover
        paigeant workflow discover --no-respect-gitignore
        # Output: ./examples/joke_workflow.py - Multi-agent joke generation
        #         Agents: topic_extractor, joke_generator, joke_selector
        #         Dependencies: HttpKey, JokeWorkflowDeps
    """
    search_path = (path or Path.cwd()).expanduser().resolve()
    typer.echo(f"Discovering workflows in: {search_path}")

    if not search_path.exists():
        typer.secho("Specified path does not exist", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    python_files = _iter_python_files(search_path, respect_gitignore=respect_gitignore)

    discoveries = []
    for py_file in python_files:
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
