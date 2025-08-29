"""Command line interface for running Paigeant workers."""

import asyncio
from pathlib import Path
from typing import Optional

import typer

from paigeant import ActivityExecutor, get_transport
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
    executor = ActivityExecutor(transport, agent_name=agent_name, base_path=base_path)
    print("Starting agent:", agent_name)
    asyncio.run(executor.start(lifespan=lifespan))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    app()
