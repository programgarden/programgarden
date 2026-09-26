"""Field-level diagnostics for the three REPLAY_FIXTURE_MISMATCH recording cases.

A recording that does not match the resolved request, the shared replay clock or
the actual iteration item still fails with the same code, but now carries a
deterministic, secret-free field-level diff so the host can tell the model WHAT
differed. The request identity holds only non-secret provider/product/paper mode
/broker node id/credential reference, which build guidance already exposes.
"""
import json

import pytest

from programgarden.replay_contracts import ContractViolation
from programgarden.replay_external import (
    external_record, mismatch_detail, recording, request_identity)
from programgarden.validation_replay import replay
from tests.test_replay_fixture_binding import AS_OF, http_case


class _Ctx:
    """Minimal replay context surface consumed by ``external_record``."""

    def __init__(self, iteration_total, iteration_item, validation_as_of):
        self._iteration_total = iteration_total
        self._iteration_item = iteration_item
        self.validation_as_of = validation_as_of


# ---- unit: the diff shape for each recording dimension --------------------

def test_connection_diff_names_the_injected_identity_fields():
    # The exact reported case: the recording bound only {broker_node_id} while
    # the resolved runtime request carried the full auto-injected identity.
    recorded = request_identity("OverseasStockAccountNode", {"connection": {"broker_node_id": "overseas_broker"}})
    resolved = request_identity("OverseasStockAccountNode", {"connection": {
        "provider": "ls-sec.co.kr", "product": "overseas_stock",
        "paper_trading": False, "broker_node_id": "overseas_broker"}})
    detail = mismatch_detail(recorded, resolved)
    assert detail["differing"] == ["connection.paper_trading", "connection.product", "connection.provider"]
    # broker_node_id matches on both sides, so it is not reported.
    assert detail["recorded"] == {"connection": {}}
    assert detail["resolved"] == {"connection": {
        "provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False}}


def test_item_diff_names_differing_and_one_side_only_keys():
    detail = mismatch_detail({"symbol": "AAPL", "exchange": "NASDAQ"},
                             {"symbol": "MSFT", "exchange": "NASDAQ", "board": "main"})
    assert detail["differing"] == ["board", "symbol"]
    assert detail["recorded"] == {"symbol": "AAPL"}
    assert detail["resolved"] == {"symbol": "MSFT", "board": "main"}


def test_top_level_only_keys_are_reported_whole():
    detail = mismatch_detail({"interval": "1d"}, {"interval": "1d", "start_date": "20260101"})
    assert detail["differing"] == ["start_date"]
    assert detail["recorded"] == {}
    assert detail["resolved"] == {"start_date": "20260101"}


def test_json_identity_difference_is_reported_not_merged():
    # 1 and 1.0 are equal to Python == but produce different recording hashes.
    detail = mismatch_detail({"config": {"qty": 1}}, {"config": {"qty": 1.0}})
    assert detail["differing"] == ["config.qty"]


# ---- integration: the detail reaches result.errors through replay ---------

@pytest.mark.asyncio
async def test_request_mismatch_flows_field_diff_through_replay():
    graph, fixture = http_case()
    graph["nodes"][1]["query_params"] = {"currency": "KRW"}  # recording bound USD
    result = await replay(graph, fixture)
    assert not result.passed and "calc" not in result.executed
    mismatch = next(e for e in result.errors if e["code"] == "REPLAY_FIXTURE_MISMATCH")
    assert mismatch["node_id"] == "source"
    assert mismatch["detail"]["differing"] == ["query_params.currency"]
    assert mismatch["detail"]["recorded"] == {"query_params": {"currency": "USD"}}
    assert mismatch["detail"]["resolved"] == {"query_params": {"currency": "KRW"}}
    assert "query_params.currency" in mismatch["message"]


@pytest.mark.asyncio
async def test_clock_mismatch_reports_both_clocks():
    graph, fixture = http_case()
    fixture["nodes"]["source"]["as_of"] = "2026-09-23T14:00:00Z"  # differs from the shared clock
    result = await replay(graph, fixture)
    assert not result.passed
    mismatch = next(e for e in result.errors if e["code"] == "REPLAY_FIXTURE_MISMATCH")
    assert mismatch["detail"] == {"recorded": {"as_of": "2026-09-23T14:00:00Z"},
                                  "resolved": {"as_of": AS_OF}, "differing": ["as_of"]}
    assert "as_of" in mismatch["message"]


def test_item_mismatch_reports_field_diff_via_external_record():
    node_type, config = "OverseasStockMarketDataNode", {"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]}
    rec = recording(node_type, config, {}, {"type": "object"}, as_of=AS_OF,
                    item={"symbol": "AAPL", "exchange": "NASDAQ"})
    fixture = {"nodes": {"market": {"items": {"NASDAQ:AAPL": rec}}}}
    # Request and clock match; only the actual iteration item carries an extra key.
    ctx = _Ctx(1, {"symbol": "AAPL", "exchange": "NASDAQ", "board": "main"}, AS_OF)
    with pytest.raises(ContractViolation) as exc:
        external_record(fixture, "market", node_type, config, ctx)
    assert exc.value.code == "REPLAY_FIXTURE_MISMATCH"
    assert exc.value.detail == {"recorded": {}, "resolved": {"board": "main"}, "differing": ["board"]}
    assert "actual iteration item" in str(exc.value) and "board" in str(exc.value)


@pytest.mark.asyncio
async def test_injected_broker_identity_mismatch_carries_detail_end_to_end():
    # Reproduce the reported failure through the real DAG: a broker injects the
    # full connection into a fixture node whose recording bound only broker_node_id.
    broker = {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "fixture-stock"}
    account = {"id": "account", "type": "OverseasStockAccountNode"}
    graph = {"id": "wf", "name": "wf", "nodes": [{"id": "start", "type": "StartNode"}, broker, account],
             "edges": [{"from": "start", "to": "broker"}, {"from": "broker", "to": "account"}],
             "credentials": [{"credential_id": "fixture-stock", "type": "broker_ls_overseas_stock"}]}
    connection = {"provider": "ls-sec.co.kr", "product": "overseas_stock", "credential_id": "fixture-stock",
                  "paper_trading": False, "broker_node_id": "broker"}
    fixture = {"as_of": AS_OF, "nodes": {
        "broker": recording("OverseasStockBrokerNode", broker, {"connection": connection}, {"type": "object"}, as_of=AS_OF),
        "account": recording("OverseasStockAccountNode", {"connection": connection}, {}, {"type": "object"}, as_of=AS_OF)}}
    fixture["nodes"]["account"]["request"]["connection"] = {"broker_node_id": "broker"}  # strip injected identity
    result = await replay(graph, fixture)
    assert not result.passed
    mismatch = next(e for e in result.errors if e["code"] == "REPLAY_FIXTURE_MISMATCH")
    assert mismatch["node_id"] == "account"
    assert mismatch["detail"]["differing"] == [
        "connection.credential_id", "connection.paper_trading", "connection.product", "connection.provider"]
    assert mismatch["detail"]["resolved"]["connection"] == {
        "provider": "ls-sec.co.kr", "product": "overseas_stock",
        "credential_id": "fixture-stock", "paper_trading": False}
    assert mismatch["detail"]["recorded"] == {"connection": {}}


# ---- guardrails: no secret leak, behavior unchanged -----------------------

def test_diff_excludes_credential_secrets():
    # A secret in the connection is rejected before any diff is computed, so it
    # can never reach the field-level diagnostic.
    with pytest.raises(ContractViolation, match="non-secret"):
        request_identity("OverseasStockAccountNode", {"connection": {"appkey": "SECRET-DO-NOT-LEAK"}})
    # The diff only ever operates on normalized identities: even if a secret is
    # threaded through the config, the resolved side is request_identity's output
    # (which excludes it), so the serialized detail never contains it.
    recorded = request_identity("OverseasStockAccountNode", {"connection": {"broker_node_id": "b"}})
    resolved = request_identity("OverseasStockAccountNode", {"connection": {
        "provider": "ls-sec.co.kr", "product": "overseas_stock", "credential_id": "acct-1",
        "paper_trading": False, "broker_node_id": "b"}})
    blob = json.dumps(mismatch_detail(recorded, resolved))
    for secret in ("SECRET-DO-NOT-LEAK", "appkey", "appsecret", "password"):
        assert secret not in blob


@pytest.mark.asyncio
async def test_mismatch_still_fails_with_the_same_code():
    # Detail is additive: a changed request is still a failure with the same code
    # and still blocks the dependent computation.
    graph, fixture = http_case()
    graph["nodes"][1]["url"] = "https://fixture.invalid/wrong"
    result = await replay(graph, fixture)
    assert not result.passed and "calc" not in result.executed
    assert any(e["code"] == "REPLAY_FIXTURE_MISMATCH" for e in result.errors)
