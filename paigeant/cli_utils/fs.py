"""Filesystem helper utilities for CLI discovery commands."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Iterable, Set


def _load_gitignore_patterns(search_path: Path) -> Set[str]:
    """Load gitignore patterns from .gitignore files in the search path and its parents."""
    patterns: Set[str] = set()

    # Common patterns to always ignore
    default_patterns = {
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".Python",
        "build/",
        "develop-eggs/",
        "dist/",
        "downloads/",
        "eggs/",
        ".eggs/",
        "lib/",
        "lib64/",
        "parts/",
        "sdist/",
        "var/",
        "wheels/",
        "*.egg-info/",
        ".installed.cfg",
        "*.egg",
        ".git/",
        ".gitignore",
    }
    patterns.update(default_patterns)

    # Walk up the directory tree looking for .gitignore files
    current_path = search_path
    while current_path != current_path.parent:
        gitignore_file = current_path / ".gitignore"
        if gitignore_file.exists():
            try:
                with open(gitignore_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.add(line)
            except (OSError, UnicodeDecodeError):
                # Skip files we can't read
                pass
        current_path = current_path.parent

    return patterns


def _should_ignore_path(path: Path, patterns: Set[str], base_path: Path) -> bool:
    """Check if a path should be ignored based on gitignore patterns."""
    try:
        relative_path = path.relative_to(base_path)
    except ValueError:
        # Path is not relative to base_path, don't ignore
        return False

    # Check against all patterns
    path_str = str(relative_path)
    path_parts = relative_path.parts

    for pattern in patterns:
        # Handle directory patterns (ending with /)
        if pattern.endswith("/"):
            pattern_no_slash = pattern[:-1]
            # Check if any part of the path matches the directory pattern
            for part in path_parts:
                if fnmatch.fnmatch(part, pattern_no_slash):
                    return True
            # Also check the full relative path
            if fnmatch.fnmatch(path_str, pattern_no_slash):
                return True
        else:
            # Check filename patterns
            if fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(path_str, pattern):
                return True
            # Check if any parent directory matches
            for part in path_parts:
                if fnmatch.fnmatch(part, pattern):
                    return True

    return False


def _iter_python_files(
    search_path: Path, respect_gitignore: bool = True
) -> Iterable[Path]:
    """Yield Python files contained within ``search_path`` respecting ``.gitignore``."""

    if search_path.is_file():
        if search_path.suffix == ".py":
            yield search_path
        return

    gitignore_patterns: Set[str] = set()
    if respect_gitignore:
        gitignore_patterns = _load_gitignore_patterns(search_path)

    for py_file in sorted(search_path.rglob("*.py")):
        if respect_gitignore and _should_ignore_path(
            py_file, gitignore_patterns, search_path
        ):
            continue
        if py_file.is_file():
            yield py_file
