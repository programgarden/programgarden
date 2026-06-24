"""Unit tests for t1514 업종기간별추이 (Korea Stock Sector Period Trend).

t1514 returns a per-period time series for one market sector / index, with
``cts_date`` continuation (same envelope shape as the t8451 chart TR:
``block`` = continuation cursor, ``block1`` = period rows).

Guard coverage:
  Guard 1 — InBlock / OutBlock / OutBlock1 field SETS match the LS source
            (drift guard against silent rename/add/remove).
  Guard 2 — every field carries >=1 example and every example round-trips
            through ``TypeAdapter`` (chatbot-ready metadata contract; also
            enforced repo-wide by test_field_metadata_coverage).
  Guard 3 — chatbot-disambiguation: market-breadth fields (상승/보합/하락/
            상한/하한/종목수) are ``int`` counts and their descriptions say
            "NOT a price"; index OHLC fields (jisu/openjisu/highjisu/lowjisu)
            are ``float``.
  Guard 4 — Request envelope: tr_cd='t1514', routes to KOREA_STOCK_INDTP_URL.
  Guard 5 — _build_response parses the official LS sample response (success),
            and surfaces a clear ``error_msg`` on HTTP>=400 and on exception
            (no silent failure — chatbot must see the reason).
  Guard 6 — occurs_req cts_date continuation feeds the next request.
"""

from __future__ import annotations

from typing import Type

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock.sector.t1514 import TrT1514
from programgarden_finance.ls.korea_stock.sector.t1514.blocks import (
    T1514InBlock,
    T1514OutBlock,
    T1514OutBlock1,
    T1514Request,
    T1514Response,
)


# ---------------------------------------------------------------------------
# LS source field sets (verbatim from the t1514 spec)
# ---------------------------------------------------------------------------

INBLOCK_FIELDS = {"upcode", "gubun1", "gubun2", "cts_date", "cnt", "rate_gbn"}
OUTBLOCK_FIELDS = {"cts_date"}
OUTBLOCK1_FIELDS = {
    "date", "jisu", "sign", "change", "diff", "volume", "diff_vol", "value1",
    "high", "unchg", "low", "uprate", "frgsvolume", "openjisu", "highjisu",
    "lowjisu", "value2", "up", "down", "totjo", "orgsvolume", "upcode",
    "rate", "divrate",
}

# Market-breadth counts — Korean labels look price-like but are ISSUE COUNTS.
BREADTH_COUNT_FIELDS = {"high", "unchg", "low", "up", "down", "totjo"}
# Sector index OHLC — the real index levels.
INDEX_OHLC_FIELDS = {"jisu", "openjisu", "highjisu", "lowjisu"}


# Official LS REST sample response (upcode '001', 20230605)
LS_SAMPLE = {
    "t1514OutBlock": {"cts_date": "20230605"},
    "rsp_cd": "00000",
    "t1514OutBlock1": [{
        "date": "20230605", "divrate": "0.00", "value2": 3884240,
        "diff_vol": "46.20", "value1": 3884240, "change": "9.26", "sign": "2",
        "totjo": 950, "diff": "0.36", "orgsvolume": 1210, "unchg": 91,
        "down": 0, "jisu": "2610.62", "volume": 263165, "high": 606,
        "highjisu": "2617.58", "low": 253, "rate": "0.00", "upcode": "001",
        "up": 0, "lowjisu": "2610.40", "uprate": "63.79", "openjisu": "2617.43",
        "frgsvolume": 351,
    }],
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
}

RESP_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "tr_cd": "t1514", "tr_cont": "N", "tr_cont_key": "",
}


def _resp(status_code: int):
    return type("R", (), {"status_code": status_code})()


# ===========================================================================
# Guard 1 — field-set drift guard
# ===========================================================================


def test_inblock_field_set():
    assert set(T1514InBlock.model_fields) == INBLOCK_FIELDS


def test_outblock_field_set():
    assert set(T1514OutBlock.model_fields) == OUTBLOCK_FIELDS


def test_outblock1_field_set():
    assert set(T1514OutBlock1.model_fields) == OUTBLOCK1_FIELDS
    assert len(OUTBLOCK1_FIELDS) == 24  # LS source declares exactly 24


# ===========================================================================
# Guard 2 — examples coverage + TypeAdapter round-trip
# ===========================================================================


@pytest.mark.parametrize(
    "model_cls",
    [T1514InBlock, T1514OutBlock, T1514OutBlock1],
    ids=["InBlock", "OutBlock", "OutBlock1"],
)
def test_every_field_has_example(model_cls: Type[BaseModel]):
    missing = [n for n, i in model_cls.model_fields.items() if not (i.examples or [])]
    assert not missing, f"{model_cls.__name__} fields without examples: {missing}"


@pytest.mark.parametrize(
    "model_cls",
    [T1514InBlock, T1514OutBlock, T1514OutBlock1],
    ids=["InBlock", "OutBlock", "OutBlock1"],
)
def test_field_examples_type_valid(model_cls: Type[BaseModel]):
    failures: list[str] = []
    for name, info in model_cls.model_fields.items():
        for ex in (info.examples or []):
            try:
                TypeAdapter(info.annotation).validate_python(ex)
            except (ValidationError, Exception) as exc:  # noqa: BLE001
                failures.append(f"{model_cls.__name__}.{name} example {ex!r}: {exc}")
    assert not failures, "Invalid Field examples:\n" + "\n".join(failures)


# ===========================================================================
# Guard 3 — chatbot disambiguation: breadth counts vs index OHLC
# ===========================================================================


@pytest.mark.parametrize("field_name", sorted(BREADTH_COUNT_FIELDS))
def test_breadth_fields_are_int(field_name):
    assert T1514OutBlock1.model_fields[field_name].annotation is int


@pytest.mark.parametrize("field_name", sorted(BREADTH_COUNT_FIELDS))
def test_breadth_fields_described_as_not_price(field_name):
    desc = (T1514OutBlock1.model_fields[field_name].description or "").lower()
    assert "not a price" in desc, (
        f"{field_name} must declare it is a breadth count, NOT a price"
    )


@pytest.mark.parametrize("field_name", sorted(INDEX_OHLC_FIELDS))
def test_index_ohlc_fields_are_float(field_name):
    assert T1514OutBlock1.model_fields[field_name].annotation is float


def test_high_low_are_counts_not_jisu():
    """Regression: ``high``/``low`` are advancing/declining COUNTS, while the
    sector index high/low live in ``highjisu``/``lowjisu``."""
    assert T1514OutBlock1.model_fields["high"].annotation is int
    assert T1514OutBlock1.model_fields["low"].annotation is int
    assert T1514OutBlock1.model_fields["highjisu"].annotation is float
    assert T1514OutBlock1.model_fields["lowjisu"].annotation is float


# ===========================================================================
# Guard 4 — Request envelope + URL routing
# ===========================================================================


def test_request_envelope():
    req = T1514Request(body={"t1514InBlock": T1514InBlock(upcode="001")})
    assert req.header.tr_cd == "t1514"
    assert req.body["t1514InBlock"].upcode == "001"
    # defaults LS-source-declared
    ib = req.body["t1514InBlock"]
    assert ib.gubun1 == " " and ib.gubun2 == "1" and ib.rate_gbn == "1"


def test_routes_to_indtp_url():
    tr = TrT1514(T1514Request(body={"t1514InBlock": T1514InBlock(upcode="001")}))
    url = getattr(tr._generic, "_url", getattr(tr._generic, "url", None))
    assert url == URLS.KOREA_STOCK_INDTP_URL
    assert url.endswith("/indtp/market-data")


def test_rate_gbn_rejects_invalid():
    with pytest.raises(ValidationError):
        T1514InBlock(upcode="001", rate_gbn="9")


# ===========================================================================
# Guard 5 — _build_response success / error clarity
# ===========================================================================


def test_build_response_success_parses_sample():
    tr = TrT1514(T1514Request(body={"t1514InBlock": T1514InBlock(upcode="001")}))
    resp = tr._build_response(_resp(200), LS_SAMPLE, RESP_HEADERS, None)
    assert resp.error_msg is None
    assert resp.rsp_cd == "00000"
    assert resp.block is not None and resp.block.cts_date == "20230605"
    assert len(resp.block1) == 1
    row = resp.block1[0]
    # index level vs breadth counts correctly typed/valued
    assert row.jisu == pytest.approx(2610.62)
    assert row.highjisu == pytest.approx(2617.58)
    assert (row.high, row.unchg, row.low, row.totjo) == (606, 91, 253, 950)
    assert row.frgsvolume == 351 and row.orgsvolume == 1210
    # string→float coercion: LS delivers these Number fields as JSON strings
    # ("9.26", "0.36", ...). Pin both type and value so a mis-typed or
    # mis-mapped (e.g. openjisu↔lowjisu) float regression is caught.
    assert isinstance(row.change, float) and row.change == pytest.approx(9.26)
    assert isinstance(row.diff, float) and row.diff == pytest.approx(0.36)
    assert row.diff_vol == pytest.approx(46.20)
    assert row.openjisu == pytest.approx(2617.43)
    assert row.lowjisu == pytest.approx(2610.40)
    assert row.uprate == pytest.approx(63.79)
    assert row.rate == pytest.approx(0.00) and row.divrate == pytest.approx(0.00)
    # int fields stay int (value1/value2 arrive as JSON ints)
    assert isinstance(row.value1, int) and row.value1 == 3884240
    assert isinstance(row.value2, int) and row.value2 == 3884240


def test_build_response_http_error_has_error_msg():
    tr = TrT1514(T1514Request(body={"t1514InBlock": T1514InBlock(upcode="001")}))
    resp = tr._build_response(
        _resp(500), {"rsp_cd": "IGW00001", "rsp_msg": "권한이 없습니다"}, RESP_HEADERS, None
    )
    assert resp.error_msg == "HTTP 500: 권한이 없습니다"
    assert resp.status_code == 500
    assert resp.block1 == []  # no rows parsed on error
    assert resp.header is None


def test_build_response_exception_has_error_msg():
    tr = TrT1514(T1514Request(body={"t1514InBlock": T1514InBlock(upcode="001")}))
    resp = tr._build_response(None, None, None, RuntimeError("Connection refused"))
    assert resp.error_msg == "Connection refused"
    assert resp.block is None and resp.block1 == []


def test_build_response_terminal_page_block_is_none():
    """Terminal page: LS omits ``t1514OutBlock`` entirely when there is no more
    data → ``block`` must be None (the contract the example relies on via
    ``if response.block and response.block.cts_date``). Guards against a
    regression that defaulted block to an empty ``T1514OutBlock()``."""
    tr = TrT1514(T1514Request(body={"t1514InBlock": T1514InBlock(upcode="001")}))
    sample = {k: v for k, v in LS_SAMPLE.items() if k != "t1514OutBlock"}
    resp = tr._build_response(_resp(200), sample, RESP_HEADERS, None)
    assert resp.block is None
    assert resp.error_msg is None
    assert len(resp.block1) == 1  # rows still parsed on the final page


# ===========================================================================
# Guard 6 — occurs_req cts_date continuation
# ===========================================================================


def test_occurs_continuation_feeds_cts_date():
    """The occurs updater must copy the response ``cts_date`` into the next
    request's InBlock so paging actually advances."""
    req = T1514Request(body={"t1514InBlock": T1514InBlock(upcode="001")})
    tr = TrT1514(req)
    resp = tr._build_response(_resp(200), LS_SAMPLE, RESP_HEADERS, None)

    captured = {}

    def fake_occurs(updater, callback=None, delay=1):
        updater(req, resp)
        captured["cts_date"] = req.body["t1514InBlock"].cts_date
        captured["tr_cont"] = req.header.tr_cont
        return [resp]

    tr._generic.occurs_req = fake_occurs  # type: ignore[assignment]
    out = tr.occurs_req()
    assert out == [resp]
    assert captured["cts_date"] == "20230605"
    assert captured["tr_cont"] == "N"


def test_occurs_updater_raises_on_missing_continuation():
    """No silent paging stop: the occurs updater must RAISE (not return) when
    the response lacks header/block (e.g. an error page), so a broken page
    surfaces instead of silently ending continuation."""
    req = T1514Request(body={"t1514InBlock": T1514InBlock(upcode="001")})
    tr = TrT1514(req)
    # error response → header is None and block is None
    err_resp = tr._build_response(None, None, None, RuntimeError("boom"))

    def fake_occurs(updater, callback=None, delay=1):
        updater(req, err_resp)  # must raise before returning
        return []

    tr._generic.occurs_req = fake_occurs  # type: ignore[assignment]
    with pytest.raises(ValueError, match="missing continuation"):
        tr.occurs_req()


def test_response_envelope_signature():
    for f in ("header", "block", "block1", "status_code", "rsp_cd", "rsp_msg", "error_msg"):
        assert f in T1514Response.model_fields
