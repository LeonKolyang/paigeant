from __future__ import annotations

import asyncio
import random


def compute_backoff(attempt: int, base: float = 1.5, jitter: float = 0.5) -> float:
    """Compute exponential backoff with jitter."""
    delay = base ** attempt
    return delay + random.uniform(0, jitter)


async def schedule_retry(attempt: int) -> None:
    """Sleep for computed backoff delay before retrying."""
    delay = compute_backoff(attempt)
    await asyncio.sleep(delay)
