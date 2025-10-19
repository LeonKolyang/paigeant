from __future__ import annotations

from pathlib import Path

from paigeant.agent.discovery import discover_agents_in_path


def test_discover_agents_in_path_handles_reexports(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "pkg"
    sub_dir = pkg_dir / "sub"
    sub_dir.mkdir(parents=True)

    primary_source = """
from paigeant import PaigeantAgent, WorkflowDispatcher

dispatcher = WorkflowDispatcher()

__all__ = ["primary_agent"]

primary_agent = PaigeantAgent(
    "model",
    dispatcher=dispatcher,
    name="primary",
)
"""

    sub_init_source = """
from ..primary import primary_agent

__all__ = ["primary_agent"]
"""

    pkg_init_source = """
from .sub import primary_agent

__all__ = ["primary_agent"]
"""

    primary_path = pkg_dir / "primary.py"
    primary_path.write_text(primary_source, encoding="utf-8")

    sub_init_path = sub_dir / "__init__.py"
    sub_init_path.write_text(sub_init_source, encoding="utf-8")

    pkg_init_path = pkg_dir / "__init__.py"
    pkg_init_path.write_text(pkg_init_source, encoding="utf-8")

    discoveries = discover_agents_in_path(pkg_dir)

    results = {(item["name"], item["path"]) for item in discoveries}

    assert ("primary", primary_path) in results
    assert ("primary_agent", primary_path) in results
    assert ("primary_agent", sub_init_path) in results
    assert ("primary_agent", pkg_init_path) in results


def test_discover_agents_in_path_includes_imported_agents_from_file(
    tmp_path: Path,
) -> None:
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir(parents=True)

    primary_source = """
from paigeant import PaigeantAgent, WorkflowDispatcher

dispatcher = WorkflowDispatcher()

primary_agent = PaigeantAgent(
    "model",
    dispatcher=dispatcher,
    name="primary_agent",
)
"""

    consumer_source = """
from paigeant import PaigeantAgent, WorkflowDispatcher
from pkg.primary import primary_agent

dispatcher = WorkflowDispatcher()

secondary_agent = PaigeantAgent(
    "model",
    dispatcher=dispatcher,
    name="secondary",
)
"""

    pkg_init = pkg_dir / "__init__.py"
    pkg_init.write_text("", encoding="utf-8")

    primary_path = pkg_dir / "primary.py"
    primary_path.write_text(primary_source, encoding="utf-8")

    consumer_path = pkg_dir / "consumer.py"
    consumer_path.write_text(consumer_source, encoding="utf-8")

    import sys

    sys.path.insert(0, str(tmp_path))
    try:
        discoveries = discover_agents_in_path(consumer_path)
    finally:
        sys.path.remove(str(tmp_path))

    results = {(item["name"], item["path"]) for item in discoveries}

    assert ("secondary", consumer_path) in results
    assert ("primary_agent", consumer_path) in results
    assert ("primary_agent", primary_path) in results
