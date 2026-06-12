"""Test-isolation safeguards shared across the programgarden test suite."""
import asyncio

import pytest


@pytest.fixture(autouse=True)
def _ensure_main_thread_event_loop():
    """Guarantee the main thread always has a usable current event loop.

    pytest-asyncio (>=1.0) closes its per-test event loop and leaves the main
    thread with *no* current loop. Legacy tests (and any sync code) that call the
    deprecated ``asyncio.get_event_loop()`` then crash with "There is no current
    event loop", and that null-loop state leaks across test boundaries as a
    spurious, order-dependent failure. After each test, re-install a fresh open
    loop on the main thread if the previous one was closed or cleared, restoring
    the lenient pre-1.0 behaviour without touching individual tests.
    """
    yield
    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
