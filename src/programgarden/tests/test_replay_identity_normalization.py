"""Broker identity: null keys are absent, and identity defects name the key.

At replay the engine injects an unlinked broker's identity WITHOUT a
credential_id key (earlier passing suites recorded provider/product/paper_trading
/broker_node_id only), so a recorded `credential_id: null` is semantically the
same identity, not a mismatch. Invalid or unknown identity keys now name the key,
the expected type and the received value type so the designer can repair them.
"""
import pytest

from programgarden.replay_contracts import ContractViolation
from programgarden.replay_external import external_record, recording, request_identity

AS_OF = "2026-09-22T14:00:00Z"
ALLOWED = {"provider", "product", "paper_trading", "broker_node_id", "credential_id"}
# An unlinked broker's injected identity: no credential_id key at all.
INJECTED = {"provider": "ls-sec.co.kr", "product": "overseas_stock",
            "paper_trading": False, "broker_node_id": "broker"}


class _Ctx:
    def __init__(self, as_of=AS_OF):
        self._iteration_total = 0
        self._iteration_item = None
        self.validation_as_of = as_of


def test_null_credential_id_normalizes_to_absent():
    with_null = request_identity("OverseasStockAccountNode", {"connection": {**INJECTED, "credential_id": None}})
    without = request_identity("OverseasStockAccountNode", {"connection": INJECTED})
    assert with_null == without
    assert "credential_id" not in with_null["connection"]


def test_null_credential_id_matches_injected_identity_through_external_record():
    node_type = "OverseasStockAccountNode"
    # Recorded request bound credential_id: null (an unlinked broker's recording).
    rec = recording(node_type, {"connection": {**INJECTED, "credential_id": None}},
                    {}, {"type": "object"}, as_of=AS_OF)
    fixture = {"nodes": {"account": rec}}
    # Resolved/injected identity has no credential_id key at all — still a match.
    out = external_record(fixture, "account", node_type, {"connection": INJECTED}, _Ctx())
    assert out is rec


def test_null_valued_unknown_key_is_treated_as_absent():
    out = request_identity("OverseasStockAccountNode", {"connection": {**INJECTED, "region": None}})
    assert "region" not in out["connection"]


@pytest.mark.parametrize("bad,key,expected,received", [
    ({"provider": 7}, "provider", "nonempty string", "int"),
    ({"provider": ""}, "provider", "nonempty string", "str"),
    ({"broker_node_id": []}, "broker_node_id", "nonempty string", "list"),
    ({"paper_trading": "false"}, "paper_trading", "bool", "str"),
])
def test_invalid_identity_value_names_key_and_types(bad, key, expected, received):
    with pytest.raises(ContractViolation) as exc:
        request_identity("OverseasStockAccountNode", {"connection": {**INJECTED, **bad}})
    assert exc.value.code == "REPLAY_FIXTURE_INVALID"
    assert exc.value.path == f"request.connection.{key}"
    assert str(exc.value) == f"request.connection.{key}: expected {expected}, got {received}"
    detail = exc.value.detail
    assert detail["key"] == key and detail["expected"] == expected and detail["received_type"] == received
    assert set(detail["allowed_keys"]) == ALLOWED


def test_unknown_identity_key_is_named():
    with pytest.raises(ContractViolation) as exc:
        request_identity("OverseasStockAccountNode", {"connection": {**INJECTED, "region": "US"}})
    assert exc.value.code == "REPLAY_FIXTURE_INVALID"
    assert exc.value.path == "request.connection.region"
    assert "region" in str(exc.value)
    assert exc.value.detail["key"] == "region" and exc.value.detail["unknown_keys"] == ["region"]
    assert set(exc.value.detail["allowed_keys"]) == ALLOWED


def test_connection_secret_still_rejected_and_named():
    # A real secret is an unknown key; it is rejected and named, and the message
    # still identifies the non-secret allowlist. The secret value never appears.
    with pytest.raises(ContractViolation, match="non-secret") as exc:
        request_identity("OverseasStockAccountNode", {"connection": {"appkey": "do-not-store"}})
    assert exc.value.detail["key"] == "appkey"
    assert "do-not-store" not in str(exc.value)
