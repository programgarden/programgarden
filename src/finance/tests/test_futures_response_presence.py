"""Absent detail arrays must not become observed empty account evidence."""

from types import SimpleNamespace

import pytest
from programgarden_finance import CIDBQ01500, CIDBQ02400, CIDBQ05300


@pytest.mark.parametrize(
    "module,tr",
    [
        (CIDBQ01500, "CIDBQ01500"),
        (CIDBQ02400, "CIDBQ02400"),
        (CIDBQ05300, "CIDBQ05300"),
    ],
)
@pytest.mark.parametrize("provided", [True, False])
@pytest.mark.parametrize("http_status", [200, 503])
def test_parser_preserves_detail_array_presence(module, tr, provided, http_status):
    body = {"rsp_cd": "00136", "rsp_msg": "Offline"}
    if provided:
        body[tr + "OutBlock2"] = []
    cls = getattr(module, "Tr" + tr)
    response = cls._build_response(
        None, SimpleNamespace(status_code=http_status), body, {}, None
    )
    assert response.block2 == []
    assert ("block2" in response.model_fields_set) is (provided and http_status == 200)
