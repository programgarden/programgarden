"""Unit tests for t8409 업종차트(N분) (Korea Stock Sector N-minute Chart).

t8409 returns an N-minute chart for one market sector / index (bar interval
selected via ``ncnt``: '0' = 30 seconds, '1' = 1-minute, 'n' = n-minute). The
response is a two-block chart envelope (t8408-style ``cont_block`` / ``block``
naming), differing from t8408 only by two added traded-value fields:
    - ``cont_block`` (t8409OutBlock) — metadata + continuation cursor:
      previous-day / today's sector index OHLC, previous-day volume, today's
      cumulative traded value (``disvalue``, added vs t8408), the continuation
      cursors (``cts_date`` / ``cts_time``), session start/end times and the
      record count. Present only while more data is available.
    - ``block`` (t8409OutBlock1) — list of N-minute bars (one row per bar),
      each carrying the bar date/time, the bar index OHLC, the traded volume
      and the traded value (``value``, added vs t8408).

Guard coverage (per plan §6):
  Guard 1 — InBlock / OutBlock / OutBlock1 field SETS match the LS source
            (drift guard; INBLOCK=11, OUTBLOCK=17, OUTBLOCK1=8 — the two added
            value fields are present and t8408's 16/7 shape did not leak in).
  Guard 2 — every field carries >=1 example and every example round-trips
            through ``TypeAdapter`` (chatbot-ready metadata contract).
  Guard 3 — chatbot-disambiguation: index OHLC fields are ``float`` and every
            description says "index points" and "not a price"; volume / count /
            value fields are ``int`` (Guard 3b).
  Guard 4 — Request envelope: tr_cd='t8409', routes to
            KOREA_STOCK_INDTP_CHART_URL ('/indtp/chart').
  Guard 5 — _build_response parses the official LS sample (success), surfaces a
            clear ``error_msg`` on HTTP>=400 (5b) and on exception (5c), and
            yields ``cont_block is None`` on the terminal page (5d) — no silent
            failure.
  Guard 6 — occurs_req cts_date/cts_time continuation feeds the next request
            (6), the updater RAISES on a continuation-less response (6b), and
            the rate-limit config is pinned (6c).
  Guard 7 — unit-note guard: the traded-value fields (``disvalue`` / ``value``)
            document "백만원" / "million KRW" and the volume fields
            (``jivolume`` / ``jdiff_vol``) document "천주" / "thousand shares",
            each flagged as cross-checked / not formally declared by LS.
"""

from __future__ import annotations

from typing import Type

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.indtp.t8409 import TrT8409
from programgarden_finance.ls.indtp.t8409.blocks import (
    T8409InBlock,
    T8409OutBlock,
    T8409OutBlock1,
    T8409Request,
    T8409Response,
)


# ---------------------------------------------------------------------------
# LS source field sets (verbatim from the t8409 spec)
# ---------------------------------------------------------------------------

INBLOCK_FIELDS = {
    "shcode", "ncnt", "qrycnt", "nday", "sdate", "stime", "edate", "etime",
    "cts_date", "cts_time", "comp_yn",
}
OUTBLOCK_FIELDS = {
    "shcode", "jisiga", "jihigh", "jilow", "jiclose", "jivolume",
    "disiga", "dihigh", "dilow", "diclose", "disvalue", "cts_date", "cts_time",
    "s_time", "e_time", "dshmin", "rec_count",
}
OUTBLOCK1_FIELDS = {"date", "time", "open", "high", "low", "close", "jdiff_vol", "value"}

# Sector index OHLC — index levels (index points), NOT KRW prices.
OUTBLOCK_INDEX_OHLC_FIELDS = {
    "jisiga", "jihigh", "jilow", "jiclose",
    "disiga", "dihigh", "dilow", "diclose",
}
OUTBLOCK1_INDEX_OHLC_FIELDS = {"open", "high", "low", "close"}


# Official LS REST sample response (shcode '001', 20230605). Two bars: the
# first is the pin row; the last (102800) is a zero-volume / zero-value bar.
LS_SAMPLE = {
    "t8409OutBlock": {
        "shcode": "001",
        "jisiga": "2586.27", "jihigh": "2601.38", "jilow": "2583.88",
        "jiclose": "2601.36", "jivolume": 569620,
        "disiga": "2617.43", "dihigh": "2617.58", "dilow": "2610.40",
        "diclose": "2610.85", "disvalue": 3886266,
        "cts_date": "20230605", "cts_time": "102300",
        "s_time": "090000", "e_time": "153000", "dshmin": "10", "rec_count": 5,
    },
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t8409OutBlock1": [
        {
            "date": "20230605", "time": "102400",
            "open": "2611.42", "high": "2611.59", "low": "2610.75",
            "close": "2610.97", "jdiff_vol": 1673, "value": 19176,
        },
        {
            "date": "20230605", "time": "102800",
            "open": "2610.97", "high": "2610.97", "low": "2610.97",
            "close": "2610.97", "jdiff_vol": 0, "value": 0,
        },
    ],
}

RESP_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "tr_cd": "t8409", "tr_cont": "N", "tr_cont_key": "",
}


def _resp(status_code: int):
    return type("R", (), {"status_code": status_code})()


def _make_inblock(**overrides) -> T8409InBlock:
    base = dict(shcode="001", ncnt=1, qrycnt=5, nday="0", edate="99999999")
    base.update(overrides)
    return T8409InBlock(**base)


def _make_tr(**overrides) -> TrT8409:
    return TrT8409(T8409Request(body={"t8409InBlock": _make_inblock(**overrides)}))


# ===========================================================================
# Guard 1 — field-set drift guard
# ===========================================================================


def test_inblock_field_set():
    assert set(T8409InBlock.model_fields) == INBLOCK_FIELDS
    assert len(INBLOCK_FIELDS) == 11  # LS source declares exactly 11


def test_outblock_field_set():
    assert set(T8409OutBlock.model_fields) == OUTBLOCK_FIELDS
    # exactly 17 — t8408's 16 + disvalue (today traded value)
    assert len(OUTBLOCK_FIELDS) == 17
    assert "disvalue" in OUTBLOCK_FIELDS


def test_outblock1_field_set():
    assert set(T8409OutBlock1.model_fields) == OUTBLOCK1_FIELDS
    # exactly 8 — t8408's 7 + value (bar traded value)
    assert len(OUTBLOCK1_FIELDS) == 8
    assert "value" in OUTBLOCK1_FIELDS


# ===========================================================================
# Guard 2 — examples coverage + TypeAdapter round-trip
# ===========================================================================


@pytest.mark.parametrize(
    "model_cls",
    [T8409InBlock, T8409OutBlock, T8409OutBlock1],
    ids=["InBlock", "OutBlock", "OutBlock1"],
)
def test_every_field_has_example(model_cls: Type[BaseModel]):
    missing = [n for n, i in model_cls.model_fields.items() if not (i.examples or [])]
    assert not missing, f"{model_cls.__name__} fields without examples: {missing}"


@pytest.mark.parametrize(
    "model_cls",
    [T8409InBlock, T8409OutBlock, T8409OutBlock1],
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
# Guard 3 — chatbot disambiguation: index OHLC float + "index points / not a price"
# ===========================================================================


@pytest.mark.parametrize("field_name", sorted(OUTBLOCK_INDEX_OHLC_FIELDS))
def test_outblock_index_ohlc_fields_are_float(field_name):
    assert T8409OutBlock.model_fields[field_name].annotation is float


@pytest.mark.parametrize("field_name", sorted(OUTBLOCK1_INDEX_OHLC_FIELDS))
def test_outblock1_index_ohlc_fields_are_float(field_name):
    assert T8409OutBlock1.model_fields[field_name].annotation is float


@pytest.mark.parametrize("field_name", sorted(OUTBLOCK_INDEX_OHLC_FIELDS))
def test_outblock_index_ohlc_described_as_index_points_not_price(field_name):
    desc = (T8409OutBlock.model_fields[field_name].description or "").lower()
    assert "index points" in desc, f"{field_name} must say it is index points"
    assert "not a" in desc and "price" in desc, (
        f"{field_name} must say it is NOT a price (index vs price disambiguation)"
    )


@pytest.mark.parametrize("field_name", sorted(OUTBLOCK1_INDEX_OHLC_FIELDS))
def test_outblock1_index_ohlc_described_as_index_points_not_price(field_name):
    desc = (T8409OutBlock1.model_fields[field_name].description or "").lower()
    assert "index points" in desc, f"{field_name} must say it is index points"
    assert "not a" in desc and "price" in desc, (
        f"{field_name} must say it is NOT a price (index vs price disambiguation)"
    )


# ===========================================================================
# Guard 3b — volume / count / value fields are int
# ===========================================================================


def test_volume_count_value_fields_are_int():
    assert T8409OutBlock.model_fields["jivolume"].annotation is int
    assert T8409OutBlock.model_fields["rec_count"].annotation is int
    assert T8409OutBlock.model_fields["disvalue"].annotation is int
    assert T8409OutBlock1.model_fields["jdiff_vol"].annotation is int
    assert T8409OutBlock1.model_fields["value"].annotation is int


# ===========================================================================
# Guard 4 — Request envelope + URL routing
# ===========================================================================


def test_request_envelope():
    req = T8409Request(body={"t8409InBlock": _make_inblock()})
    assert req.header.tr_cd == "t8409"
    assert req.body["t8409InBlock"].shcode == "001"
    # LS-source-declared defaults
    ib = req.body["t8409InBlock"]
    assert ib.comp_yn == "N"
    assert ib.sdate == " "


def test_routes_to_indtp_chart_url():
    tr = _make_tr()
    url = getattr(tr._generic, "_url", getattr(tr._generic, "url", None))
    assert url == URLS.KOREA_STOCK_INDTP_CHART_URL
    assert url.endswith("/indtp/chart")


def test_comp_yn_rejects_invalid():
    with pytest.raises(ValidationError):
        T8409InBlock(shcode="001", ncnt=1, qrycnt=5, nday="0", edate="99999999", comp_yn="X")


def test_ncnt_30sec_and_minute_bars_valid():
    # ncnt '0' = 30 seconds, '1' = 1-minute — both must construct cleanly.
    assert _make_inblock(ncnt=0).ncnt == 0
    assert _make_inblock(ncnt=1).ncnt == 1


# ===========================================================================
# Guard 5 — _build_response success / error clarity
# ===========================================================================


def test_build_response_success_parses_sample():
    tr = _make_tr()
    resp = tr._build_response(_resp(200), LS_SAMPLE, RESP_HEADERS, None)
    assert resp.error_msg is None
    assert resp.rsp_cd == "00000"

    # cont_block metadata parsed
    cb = resp.cont_block
    assert cb is not None
    assert cb.cts_date == "20230605"
    assert cb.cts_time == "102300"
    # string→float coercion + value pin: previous-day OHLC (jisiga↔disiga
    # mapping regression guard — values must not be swapped)
    assert isinstance(cb.jisiga, float) and cb.jisiga == pytest.approx(2586.27)
    assert cb.jihigh == pytest.approx(2601.38)
    assert cb.jilow == pytest.approx(2583.88)
    assert isinstance(cb.jiclose, float) and cb.jiclose == pytest.approx(2601.36)
    # today's OHLC pinned distinctly from previous-day
    assert isinstance(cb.disiga, float) and cb.disiga == pytest.approx(2617.43)
    assert cb.dihigh == pytest.approx(2617.58)
    assert cb.dilow == pytest.approx(2610.40)
    assert isinstance(cb.diclose, float) and cb.diclose == pytest.approx(2610.85)
    # volume / count / today traded value stay int
    assert isinstance(cb.jivolume, int) and cb.jivolume == 569620
    assert isinstance(cb.rec_count, int) and cb.rec_count == 5
    assert isinstance(cb.disvalue, int) and cb.disvalue == 3886266

    # block rows
    assert len(resp.block) == 2
    row = resp.block[0]
    assert row.date == "20230605" and row.time == "102400"
    assert isinstance(row.open, float) and row.open == pytest.approx(2611.42)
    assert row.high == pytest.approx(2611.59)
    assert row.low == pytest.approx(2610.75)
    assert isinstance(row.close, float) and row.close == pytest.approx(2610.97)
    assert isinstance(row.jdiff_vol, int) and row.jdiff_vol == 1673
    assert isinstance(row.value, int) and row.value == 19176
    # terminal zero bar preserved (not dropped / not coerced away)
    zero = resp.block[1]
    assert zero.time == "102800"
    assert zero.jdiff_vol == 0 and zero.value == 0


def test_build_response_http_error_has_error_msg():
    tr = _make_tr()
    resp = tr._build_response(
        _resp(500), {"rsp_cd": "IGW00001", "rsp_msg": "권한이 없습니다"}, RESP_HEADERS, None
    )
    assert resp.error_msg is not None
    assert resp.error_msg.startswith("HTTP 500")
    assert resp.error_msg == "HTTP 500: 권한이 없습니다"
    assert resp.status_code == 500
    assert resp.block == []  # no rows parsed on error
    assert resp.header is None


def test_build_response_exception_has_error_msg():
    tr = _make_tr()
    resp = tr._build_response(None, None, None, RuntimeError("Connection refused"))
    assert resp.error_msg == "Connection refused"
    assert resp.cont_block is None
    assert resp.block == []


def test_terminal_page_cont_block_is_none():
    """Terminal page: LS omits ``t8409OutBlock`` entirely when there is no more
    data → ``cont_block`` must be None while the row block still parses."""
    tr = _make_tr()
    sample = {k: v for k, v in LS_SAMPLE.items() if k != "t8409OutBlock"}
    resp = tr._build_response(_resp(200), sample, RESP_HEADERS, None)
    assert resp.cont_block is None
    assert resp.error_msg is None
    assert len(resp.block) == 2  # rows still parsed on the final page


# ===========================================================================
# Guard 6 — occurs_req cts continuation
# ===========================================================================


def test_occurs_continuation_feeds_cts():
    """The occurs updater must copy the response ``cts_date`` / ``cts_time``
    into the next request's InBlock and propagate ``tr_cont`` so paging
    actually advances."""
    req = T8409Request(body={"t8409InBlock": _make_inblock()})
    tr = TrT8409(req)
    resp = tr._build_response(_resp(200), LS_SAMPLE, RESP_HEADERS, None)

    captured = {}

    def fake_occurs(updater, callback=None, delay=1):
        updater(req, resp)
        captured["cts_date"] = req.body["t8409InBlock"].cts_date
        captured["cts_time"] = req.body["t8409InBlock"].cts_time
        captured["tr_cont"] = req.header.tr_cont
        return [resp]

    tr._generic.occurs_req = fake_occurs  # type: ignore[assignment]
    out = tr.occurs_req()
    assert out == [resp]
    assert captured["cts_date"] == "20230605"
    assert captured["cts_time"] == "102300"
    assert captured["tr_cont"] == "N"


def test_occurs_updater_raises_on_missing_continuation():
    """No silent paging stop: the occurs updater must RAISE (not return) when
    the response lacks header/cont_block (e.g. an error page), so a broken page
    surfaces instead of silently ending continuation."""
    req = T8409Request(body={"t8409InBlock": _make_inblock()})
    tr = TrT8409(req)
    err_resp = tr._build_response(None, None, None, RuntimeError("boom"))

    def fake_occurs(updater, callback=None, delay=1):
        updater(req, err_resp)  # must raise before returning
        return []

    tr._generic.occurs_req = fake_occurs  # type: ignore[assignment]
    with pytest.raises(ValueError, match="missing continuation"):
        tr.occurs_req()


def test_rate_limit_config():
    req = T8409Request(body={"t8409InBlock": _make_inblock()})
    assert req.options.rate_limit_count == 1
    assert req.options.rate_limit_seconds == 1
    assert req.options.rate_limit_key == "t8409"


# ===========================================================================
# Guard 7 — unit-note guard (백만원 / 천주 cross-check documented, not declared)
# ===========================================================================


@pytest.mark.parametrize(
    "model_cls, field_name",
    [(T8409OutBlock, "disvalue"), (T8409OutBlock1, "value")],
    ids=["OutBlock.disvalue", "OutBlock1.value"],
)
def test_traded_value_fields_document_million_krw(model_cls, field_name):
    desc = model_cls.model_fields[field_name].description or ""
    assert "백만원" in desc, f"{field_name} must document the 백만원 unit"
    assert "million" in desc.lower(), f"{field_name} must document 'million KRW'"
    assert "cross-check" in desc.lower(), f"{field_name} must flag the unit as cross-checked"
    assert "not formally declared" in desc.lower(), (
        f"{field_name} must state the unit is not formally declared by LS"
    )


@pytest.mark.parametrize(
    "model_cls, field_name",
    [(T8409OutBlock, "jivolume"), (T8409OutBlock1, "jdiff_vol")],
    ids=["OutBlock.jivolume", "OutBlock1.jdiff_vol"],
)
def test_volume_fields_document_thousand_shares(model_cls, field_name):
    desc = model_cls.model_fields[field_name].description or ""
    assert "천주" in desc, f"{field_name} must document the 천주 unit"
    assert "thousand" in desc.lower(), f"{field_name} must document 'thousand shares'"
    assert "cross-check" in desc.lower(), f"{field_name} must flag the unit as cross-checked"
    assert "not formally declared" in desc.lower(), (
        f"{field_name} must state the unit is not formally declared by LS"
    )


# ===========================================================================
# Response envelope signature
# ===========================================================================


def test_response_envelope_signature():
    for f in ("header", "cont_block", "block", "status_code", "rsp_cd", "rsp_msg", "error_msg"):
        assert f in T8409Response.model_fields
