"""Command line interface for running Paigeant workers."""

import asyncio

import typer

from paigeant import ActivityExecutor, get_transport


app = typer.Typer(help="CLI for Paigeant workflows")


@app.command()
def execute(agent_name: str) -> None:
    """Run an ActivityExecutor for the given agent."""
    transport = get_transport()
    executor = ActivityExecutor(transport, agent_name=agent_name)
    asyncio.run(executor.start())


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    app()

