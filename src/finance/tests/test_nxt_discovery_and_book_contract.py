"""Offline NXT eligibility and NH1 subscription regressions."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from programgarden_finance.ls.korea_stock.market.t9945.blocks import T9945OutBlock
from programgarden_finance.ls.korea_stock.real.NH1.blocks import NH1RealRequestBody
from programgarden_finance.ls.korea_stock.real.NH1.client import RealNH1


def load_master_example():
    path = Path(__file__).resolve().parents[1] / "example/korea_stock/run_t9945.py"
    spec = importlib.util.spec_from_file_location("nxt_master_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("value,expected", [(None, "unknown"), ("", "unknown"),
                                            ("0", "not_provided"), ("1", "provided"), ("9", "unknown")])
def test_nxt_filter_requires_an_observed_source_value(value, expected):
    fields = {"hname": "Example", "shcode": "001500", "expcode": "example", "etfchk": "0"}
    if value is not None:
        fields["nxt_chk"] = value
    row = T9945OutBlock(**fields)
    assert load_master_example().nxt_status(row) == expected


@pytest.mark.parametrize("key", ["001500", "N001500", "N001500   "])
def test_nh1_keys_include_the_nxt_prefix(key):
    assert NH1RealRequestBody(tr_key=key).tr_key == "N001500   "


@pytest.mark.parametrize("key", ["A001500", "00150", "N001500  ", "N001500    ", "Nabcdef"])
def test_malformed_nh1_keys_are_rejected(key):
    with pytest.raises(ValidationError):
        NH1RealRequestBody(tr_key=key)


def test_add_remove_use_identical_keys_and_invalid_batch_cannot_mutate():
    parent = Mock()
    client = RealNH1(parent)
    client.add_nh1_symbols(["001500", "N001500"])
    parent._add_message_symbols.assert_called_once_with(symbols=["N001500   "], tr_cd="NH1")
    client.remove_nh1_symbols(["001500"])
    parent._remove_message_symbols.assert_called_once_with(symbols=["N001500   "], tr_cd="NH1")
    parent.reset_mock()
    with pytest.raises(ValidationError):
        client.add_nh1_symbols(["001500", "invalid"])
    parent._add_message_symbols.assert_not_called()
