"""Shared pytest configuration for programgarden_finance tests."""

from __future__ import annotations


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "field_metadata: AI-chatbot-ready Field metadata coverage "
        "(InBlock / OutBlock / Real body) across every LS TR blocks.py.",
    )


# --- export-time (open-source build): platform-only tests ------------------------
# Whole modules skipped at collection (their recorded-traffic fixtures are not
# shipped, so importing them here would fail):
collect_ignore = [
    'test_futures_order_events_phase0.py',  # recorded LS paper-futures traffic (module-scope load) — platform-only,
]

# These exercise features that run only on the ProgramGarden platform (deep
# validation, CodeNode execution) or load a dropped recorded capture; they are
# skipped here with the reason shown.
_PLATFORM_ONLY_TESTS = {
    'tests/test_ns3_source_contract.py::test_source_example_preserves_clock_zero_and_quote_venue': 'recorded LS real quote (owner example) — platform-only',
}


def pytest_collection_modifyitems(config, items):
    import pytest as _pytest
    for item in items:
        base = item.nodeid.split("[", 1)[0]
        for test_id, reason in _PLATFORM_ONLY_TESTS.items():
            # an id with [params] skips only that case; a bare id skips every case
            target = item.nodeid if "[" in test_id else base
            if target.endswith(test_id):
                item.add_marker(_pytest.mark.skip(reason=f"platform-only: {reason}"))
