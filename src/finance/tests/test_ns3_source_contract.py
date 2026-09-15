"""NS3 source, actual string-shaped ticks and shared socket request contracts."""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from programgarden_finance.ls.korea_stock.real import Real
from programgarden_finance.ls.korea_stock.real.NS3 import RealNS3
from programgarden_finance.ls.korea_stock.real.NS3.blocks import NS3RealRequestBody, NS3RealResponseBody
from programgarden_finance.ls.token_manager import TokenManager


@pytest.mark.parametrize("key", ["N010950", "N010950   "])
def test_exact_source_key_and_prefixed_short_form(key):
    assert NS3RealRequestBody(tr_key=key).model_dump() == {"tr_cd": "NS3", "tr_key": "N010950   "}


@pytest.mark.parametrize("key", ["010950", "A010950", "N01095", "n010950", "N010950  ", "N010950    ", "N010950\n", None])
def test_unknown_symbol_formats_are_not_guessed(key):
    with pytest.raises(ValidationError):
        NS3RealRequestBody(tr_key=key)


def test_source_example_preserves_clock_zero_and_quote_venue():
    raw = json.loads((Path(__file__).parent / "fixtures/ns3_owner_example.json").read_text())["body"]
    parsed = NS3RealResponseBody.model_validate(raw)
    assert parsed.model_dump(exclude_unset=True) == raw
    assert parsed.hightime == "080908"
    assert parsed.high == "62700"
    assert parsed.exchname == "NXT"
    assert parsed.model_fields_set == set(raw)
    assert len(parsed.model_fields_set) == 28


def test_missing_values_never_become_measured_zeros_and_extra_fields_survive():
    tick = NS3RealResponseBody.model_validate({"price": "0", "new_source_field": "observed"})
    assert tick.price == "0"
    assert tick.volume is None
    assert "volume" not in tick.model_fields_set
    assert tick.model_dump(exclude_unset=True) == {"price": "0", "new_source_field": "observed"}


def test_invalid_batch_does_not_subscribe_a_valid_prefix():
    parent = MagicMock()
    with pytest.raises(ValidationError):
        RealNS3(parent).add_ns3_symbols(["N010950", "005930"])
    parent._add_message_symbols.assert_not_called()


@pytest.mark.asyncio
async def test_shared_socket_emits_exact_subscribe_and_remove_envelopes():
    real = Real(token_manager=TokenManager())
    real._token_manager = MagicMock(access_token="synthetic-token")
    real._ws = MagicMock(send=AsyncMock())
    real._connected_event.set()
    client = real.NS3()
    client.add_ns3_symbols(["N010950", "N010950   "])
    await asyncio.sleep(0)
    assert real._subscribed_symbols["NS3"] == ["N010950   "]
    client.remove_ns3_symbols(["N010950"])
    await asyncio.sleep(0)
    calls = [json.loads(call.args[0]) for call in real._ws.send.call_args_list]
    assert len(calls) == 2
    for payload, operation in zip(calls, ["3", "4"]):
        assert payload["header"]["tr_type"] == operation
        assert payload["header"]["token"] == "synthetic-token"
        assert payload["body"] == {"tr_cd": "NS3", "tr_key": "N010950   "}
    assert "NS3" not in real._subscribed_symbols
