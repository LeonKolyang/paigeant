"""Command line interface for running Paigeant workers."""

import asyncio
from pathlib import Path
from typing import Optional

import typer

from paigeant import ActivityExecutor, get_repository, get_transport
from paigeant.agent.discovery import discover_agent

app = typer.Typer(help="CLI for Paigeant workflows")


@app.callback()
def main() -> None:
    """Paigeant CLI entry point."""
    pass


@app.command()
def execute(
    agent_name: str,
    base_path: Optional[Path] = "",
    lifespan: Optional[float] = None,
) -> None:
    """Run an ActivityExecutor for the given agent."""
    transport = get_transport()
    repository = get_repository()
    executor = ActivityExecutor(
        transport, agent_name=agent_name, base_path=base_path, repository=repository
    )
    print("Starting agent:", agent_name)
    asyncio.run(executor.start(lifespan=lifespan))


@app.command()
def workflows() -> None:
    """List workflows in the repository."""
    repo = get_repository()
    workflows = asyncio.run(repo.list_workflows())
    if not workflows:
        typer.echo("No workflows found")
        return
    for wf in workflows:
        typer.echo(f"{wf.correlation_id}\t{wf.status}")


@app.command()
def workflow(correlation_id: str) -> None:
    """Show details for a workflow."""
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


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    app()
