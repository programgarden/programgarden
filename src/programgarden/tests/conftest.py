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


@pytest.fixture(autouse=True)
def _no_futures_exchange_read_spacing(monkeypatch):
    """Skip the 2 s gap between live o3105 exchange reads.

    Futures account/pending nodes space their o3105 reads for the shared app
    key. Offline tests do not wait for it; test_futures_position_exchange.py
    restores and records the gap where the spacing itself is under test.
    """
    from programgarden import futures_exchange

    monkeypatch.setattr(futures_exchange, "READ_SPACING_SECONDS", 0.0)


# --- export-time (open-source build): platform-only tests ------------------------
# Whole modules skipped at collection (their recorded-traffic fixtures are not
# shipped, so importing them here would fail):
collect_ignore = [
    'test_futures_fill_price_sync.py',  # recorded LS paper-futures traffic (module-scope load) — platform-only,
    'test_futures_tc2_confirmation.py',  # recorded LS paper-futures traffic (module-scope load) — platform-only,
]

# These exercise features that run only on the ProgramGarden platform (deep
# validation, CodeNode execution) or load a dropped recorded capture; they are
# skipped here with the reason shown.
_PLATFORM_ONLY_TESTS = {
    'tests/test_node_runner.py::TestNodeRunnerBasic::test_run_simple_node': 'CodeNode execution',
    'tests/test_node_runner.py::TestNodeRunnerBasic::test_run_with_custom_node_id': 'CodeNode execution',
    'tests/test_node_runner.py::TestNodeRunnerConvenience::test_async_context_manager': 'CodeNode execution',
    'tests/test_futures_contract_node.py::test_deep_fixture_needs_no_network_and_matches_port_shape': 'deep validation',
    'tests/test_futures_contract_node.py::test_deep_fixture_normalizes_sibling_enum_exchange': 'deep validation',
    'tests/test_futures_contract_node.py::test_deep_fixture_rolls_over_at_month_end': 'deep validation',
    'tests/test_futures_contract_node.py::test_deep_fixture_rolls_over_year_boundary': 'deep validation',
    'tests/test_futures_contract_node.py::test_deep_validate_does_not_touch_ls': 'deep validation',
    'tests/test_futures_orderable_evidence.py::test_deep_fixture_never_logs_in_or_queries': 'deep validation',
    'tests/test_dry_run_sampling_and_job_state.py::test_running_node_exposes_status_started_at_elapsed': 'CodeNode execution',
    'tests/test_get_state_diagnostics.py::test_normal_workflow_no_errors': 'CodeNode execution',
    'tests/test_get_state_diagnostics.py::test_if_node_inactive_branch_skipped': 'CodeNode execution',
    'tests/test_get_state_diagnostics.py::test_existing_caller_compat': 'CodeNode execution',
    'tests/test_runtime_values_are_data.py::test_codenode_receives_runtime_text_byte_identical': 'CodeNode execution',
    'tests/test_runtime_values_are_data.py::test_ifnode_operands_are_not_reevaluated': 'CodeNode execution',
    'tests/test_runtime_values_are_data.py::test_telegram_template_and_credentials_are_data': 'CodeNode execution',
    'tests/test_runtime_values_are_data.py::test_workflow_input_value_is_data': 'CodeNode execution',
    'tests/test_runtime_values_are_data.py::test_auto_iterated_item_value_is_data': 'CodeNode execution',
    'tests/test_runtime_values_are_data.py::test_codenode_source_with_braces_is_not_evaluated': 'CodeNode execution',
    'tests/test_runtime_values_are_data.py::test_deep_validate_does_not_flag_runtime_text': 'deep validation',
    'tests/test_single_broker_policy.py::test_deep_validation_blocks_before_broker_login': 'deep validation',
    'tests/test_stock_history_interval_contract.py::test_deep_validation_minute_fixture_has_minute_stamps': 'deep validation',
    'tests/test_stock_history_interval_contract.py::test_legacy_futures_intraday_remains_available[overseas_futureoption-True]': 'deep validation',
    'tests/test_stock_history_interval_contract.py::test_legacy_futures_intraday_remains_available[overseas_futures-True]': 'deep validation',
    'tests/test_futures_contract_node.py::test_deep_fixture_honors_contract_selection': 'curated deep-validation fixture content',
    'tests/test_futures_contract_node.py::test_deep_fixture_month_is_live_not_anchor_frozen': 'curated deep-validation fixture content',
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
