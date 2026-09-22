"""Retired provider admission and the maintained LS replacement contract."""
from copy import deepcopy

import pytest
import programgarden_community  # noqa: F401
from programgarden import ProgramGarden
from programgarden_core import NodeTypeRegistry
from programgarden_core.models.credential import BUILTIN_CREDENTIAL_SCHEMAS
from programgarden_finance.ls.overseas_stock.market.g3104.blocks import G3104OutBlock


def test_removed_provider_is_not_discoverable_or_accepted():
    assert NodeTypeRegistry().get("FundamentalDataNode") is None
    assert "fmp_api" not in BUILTIN_CREDENTIAL_SCHEMAS
    assert NodeTypeRegistry().get("OverseasStockFundamentalNode") is not None
    graph = {"id": "old-import", "name": "Old import", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "old", "type": "FundamentalDataNode"}],
        "edges": [{"from": "start", "to": "old"}]}
    before = deepcopy(graph)
    result = ProgramGarden().validate(graph)
    assert not result.is_valid
    errors = [e for e in result.errors if e.code == "UNKNOWN_NODE_TYPE"]
    assert errors and "OverseasStockFundamentalNode" in str(errors[0])
    assert graph == before


def test_consumed_ls_fields_exist_in_the_actual_sdk_model():
    assert {"engname", "induname", "nation_name", "exchange_name", "pcls", "clos",
            "volume", "perv", "epsv", "shareprc", "share", "high52p", "low52p",
            "exrate"} <= G3104OutBlock.model_fields.keys()
