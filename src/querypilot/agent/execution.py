"""Retain and drain synchronous workers before resource cleanup or cancellation exit."""

import asyncio
from collections.abc import Callable


async def run_tool[T](function: Callable[..., T], *args: object) -> T:
    worker = asyncio.create_task(asyncio.to_thread(function, *args))
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        # Python cannot terminate a thread. Keep ownership until it exits, including if
        # the caller is cancelled again during cleanup. Never launch another tool here.
        while not worker.done():
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                continue
            except Exception:
                break  # Retrieve/suppress worker failure; cancellation remains primary.
        if worker.done() and not worker.cancelled():
            worker.exception()
        raise
