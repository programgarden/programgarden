"""Regression guards for the t8452 / t8453 chart occurs (continuation) updaters.

Background — the bug these guards lock down:
    The t8452 / t8453 ``occurs_req`` continuation updaters were previously
    broken in two ways:
      1. ``OutBlock``'s previous-day close field was mis-named ``jiclosev``
         (LS spec is ``jiclose``).
      2. The updater tried to copy *every* OutBlock metadata field (jisiga,
         jiclose, ...) onto the InBlock. Those fields do not exist on the
         InBlock, so the updater raised ``AttributeError`` the moment a live
         continuation page (``tr_cont == 'Y'``) was reached.

    The fix narrows the updater to a **cts-only** cursor copy: only
    ``cts_date`` / ``cts_time`` (plus the header ``tr_cont`` / ``tr_cont_key``)
    are carried into the next request — the t1514 / t8408 pattern.

These tests assert the cts-only contract end-to-end and pin the corrected
field names so a copy-paste of the old broken pattern fails CI.

The updater is a closure (``_updater``) defined inside ``occurs_req``; it is
not directly importable. Following the t1514 test pattern, we monkeypatch
``tr._generic.occurs_req`` to capture the ``_updater`` callback that the public
``occurs_req`` passes in, then drive it directly against a fake response built
through the real ``_build_response`` path.
"""

from __future__ import annotations

import pytest

from programgarden_finance.ls.korea_stock.chart.t8452 import TrT8452
from programgarden_finance.ls.korea_stock.chart.t8452.blocks import (
    T8452InBlock,
    T8452OutBlock,
    T8452Request,
)
from programgarden_finance.ls.korea_stock.chart.t8453 import TrT8453
from programgarden_finance.ls.korea_stock.chart.t8453.blocks import (
    T8453InBlock,
    T8453OutBlock,
    T8453Request,
)


def _resp(status_code: int):
    return type("R", (), {"status_code": status_code})()


def _cont_headers(tr_cd: str) -> dict:
    return {
        "Content-Type": "application/json; charset=utf-8",
        "tr_cd": tr_cd, "tr_cont": "Y", "tr_cont_key": "KEY123",
    }


# t8452 (N-minute) — continuation page with the cts cursor set on OutBlock.
T8452_SAMPLE = {
    "t8452OutBlock": {"shcode": "005930", "cts_date": "20260228", "cts_time": "093001"},
    "rsp_cd": "00000",
    "t8452OutBlock1": [],
}
# t8453 (tick / N-tick) — continuation page with the cts cursor set on OutBlock.
T8453_SAMPLE = {
    "t8453OutBlock": {"shcode": "005930", "cts_date": "20260228", "cts_time": "093001"},
    "rsp_cd": "00000",
    "t8453OutBlock1": [],
}


def _capture_updater(tr):
    """Capture the ``_updater`` closure that ``occurs_req`` hands to
    ``self._generic.occurs_req``, without running the real request loop."""
    holder = {}

    def fake_occurs(updater, callback=None, delay=1):
        holder["updater"] = updater
        return []

    tr._generic.occurs_req = fake_occurs  # type: ignore[assignment]
    tr.occurs_req()
    return holder["updater"]


# ===========================================================================
# t8452 — cts-only continuation updater
# ===========================================================================


def test_t8452_inblock_excludes_outblock_only_fields():
    """The InBlock must NOT carry OutBlock-only metadata fields — copying them
    is exactly what raised AttributeError in the old broken updater."""
    in_fields = set(T8452InBlock.model_fields)
    assert "cts_date" in in_fields and "cts_time" in in_fields
    for outblock_only in ("jisiga", "jihigh", "jilow", "jiclose", "jivolume"):
        assert outblock_only not in in_fields, (
            f"{outblock_only} is an OutBlock-only field and must not be on the InBlock"
        )


def test_t8452_outblock_field_name_jiclose_not_jiclosev():
    fields = set(T8452OutBlock.model_fields)
    assert "jiclose" in fields
    assert "jiclosev" not in fields  # the old typo must stay gone


def test_t8452_occurs_updater_copies_only_cts_cursor():
    """End-to-end: the updater must run without AttributeError and copy ONLY
    cts_date / cts_time (plus header tr_cont / tr_cont_key) into the next
    request's InBlock."""
    req = T8452Request(body={"t8452InBlock": T8452InBlock(shcode="005930")})
    tr = TrT8452(req)
    resp = tr._build_response(_resp(200), T8452_SAMPLE, _cont_headers("t8452"), None)

    updater = _capture_updater(tr)
    updater(req, resp)  # must NOT raise AttributeError

    ib = req.body["t8452InBlock"]
    assert ib.cts_date == "20260228"
    assert ib.cts_time == "093001"
    assert req.header.tr_cont == "Y"
    assert req.header.tr_cont_key == "KEY123"


def test_t8452_occurs_updater_raises_on_missing_continuation():
    """No silent paging stop: missing header/cont_block must RAISE."""
    req = T8452Request(body={"t8452InBlock": T8452InBlock(shcode="005930")})
    tr = TrT8452(req)
    err_resp = tr._build_response(None, None, None, RuntimeError("boom"))

    updater = _capture_updater(tr)
    with pytest.raises(ValueError, match="missing continuation"):
        updater(req, err_resp)


# ===========================================================================
# t8453 — cts-only continuation updater
# ===========================================================================


def test_t8453_inblock_excludes_outblock_only_fields():
    in_fields = set(T8453InBlock.model_fields)
    assert "cts_date" in in_fields and "cts_time" in in_fields
    for outblock_only in ("jisiga", "jihigh", "jilow", "jiclose", "jivolume"):
        assert outblock_only not in in_fields, (
            f"{outblock_only} is an OutBlock-only field and must not be on the InBlock"
        )


def test_t8453_outblock_field_name_jiclose_not_jiclosev():
    fields = set(T8453OutBlock.model_fields)
    assert "jiclose" in fields
    assert "jiclosev" not in fields  # the old typo must stay gone


def test_t8453_occurs_updater_copies_only_cts_cursor():
    req = T8453Request(body={"t8453InBlock": T8453InBlock(shcode="005930")})
    tr = TrT8453(req)
    resp = tr._build_response(_resp(200), T8453_SAMPLE, _cont_headers("t8453"), None)

    updater = _capture_updater(tr)
    updater(req, resp)  # must NOT raise AttributeError

    ib = req.body["t8453InBlock"]
    assert ib.cts_date == "20260228"
    assert ib.cts_time == "093001"
    assert req.header.tr_cont == "Y"
    assert req.header.tr_cont_key == "KEY123"


def test_t8453_occurs_updater_raises_on_missing_continuation():
    req = T8453Request(body={"t8453InBlock": T8453InBlock(shcode="005930")})
    tr = TrT8453(req)
    err_resp = tr._build_response(None, None, None, RuntimeError("boom"))

    updater = _capture_updater(tr)
    with pytest.raises(ValueError, match="missing continuation"):
        updater(req, err_resp)
