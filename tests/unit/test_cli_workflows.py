import asyncio
import uuid

from typer.testing import CliRunner

import paigeant.persistence as persistence
from paigeant.cli import app
from paigeant.persistence import InMemoryWorkflowRepository


def _setup_repo() -> InMemoryWorkflowRepository:
    repo = InMemoryWorkflowRepository()
    persistence._repository_instance = repo
    return repo


def test_workflows_command_lists_workflows():
    repo = _setup_repo()
    corr1 = str(uuid.uuid4())
    corr2 = str(uuid.uuid4())
    asyncio.run(repo.create_workflow(corr1, {"itinerary": []}, {}))
    asyncio.run(repo.mark_workflow_completed(corr1))
    asyncio.run(repo.create_workflow(corr2, {"itinerary": []}, {}))

    runner = CliRunner()
    result = runner.invoke(app, ["workflow", "list"])
    assert (
        result.exit_code == 0
    ), f"Command failed with exit code {result.exit_code}. Output: {result.stderr}"
    output = result.stdout
    assert corr1 in output, f"Correlation ID {corr1} not found in output: {output}"
    assert corr2 in output, f"Correlation ID {corr2} not found in output: {output}"


def test_workflow_command_shows_details_and_missing():
    repo = _setup_repo()
    corr = str(uuid.uuid4())
    asyncio.run(repo.create_workflow(corr, {"itinerary": ["step1"]}, {"foo": "bar"}))
    asyncio.run(repo.mark_step_started(corr, "step1"))
    asyncio.run(repo.mark_step_completed(corr, "step1", status="completed"))

    runner = CliRunner()
    result = runner.invoke(app, ["workflow", "show", corr])
    assert (
        result.exit_code == 0
    ), f"Command failed with exit code {result.exit_code}. Output: {result.stderr}"
    output = result.stdout
    assert corr in output, f"Correlation ID {corr} not found in output: {output}"
    assert "step1" in output, f"Step 'step1' not found in output: {output}"
    assert "completed" in output, f"Status 'completed' not found in output: {output}"

    result_missing = runner.invoke(app, ["workflow", "show", "missing-id"])
    assert (
        result_missing.exit_code == 1
    ), f"Expected exit code 1 for missing workflow, got {result_missing.exit_code}. Output: {result_missing.stdout}"
    assert (
        "Workflow not found" in result_missing.stdout
    ), f"Expected 'Workflow not found' message, got: {result_missing.stderr}"
