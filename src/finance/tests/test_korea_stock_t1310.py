"""Unit tests for t1310 주식당일전일분틱조회 (Korea Stock Today/Yesterday Minute-or-Tick TR).

Covers:
    - blocks.py — Pydantic input/output validation, including LS official
      example response round-trip (with embedded null-byte preservation).
    - TrT1310._build_response — happy / HTTP error / exception paths.
    - Market domain class — Korean alias bridge to TrT1310.
    - KoreaStock chained call — ``ks.시세().주식당일전일분틱조회(...)`` Korean alias path.
    - occurs_req updater — verifies that ``cts_time`` cursor transfers from
      OutBlock back into InBlock for paged calls.
    - Field(examples=[...]) regression guards — examples present + types
      validate against declared annotations.
    - LS-undeclared ``sign`` enum mapping — description must carry a
      "not declared" disclaimer; must NOT embed t1302-style 1~5 mapping.
    - Anti-inference guard — fields LS did NOT declare (currency unit,
      change/revolume/rechecnt sign convention, chetime time-window
      semantics, volume↔cvolume relationship) must not embed inferred
      assertions.
    - Null-byte preservation in ``chetime`` and ``cts_time`` (LS-observed
      opaque token quirk).
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.market import Market
from programgarden_finance.ls.korea_stock.market.t1310 import TrT1310
from programgarden_finance.ls.korea_stock.market.t1310.blocks import (
    T1310InBlock,
    T1310OutBlock,
    T1310OutBlock1,
    T1310Request,
    T1310Response,
    T1310ResponseHeader,
)
from programgarden_finance.ls.token_manager import TokenManager


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_token_manager() -> TokenManager:
    tm = TokenManager()
    tm.access_token = "stub-access-token"
    tm.token_type = "Bearer"
    return tm


def _make_request(**overrides: Any) -> T1310Request:
    body = T1310InBlock(
        daygb=overrides.pop("daygb", "0"),
        timegb=overrides.pop("timegb", "0"),
        shcode=overrides.pop("shcode", "001200"),
        endtime=overrides.pop("endtime", ""),
        cts_time=overrides.pop("cts_time", ""),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1310Request(body={"t1310InBlock": body})


# LS official example response (user-supplied 2026-05-11). The second row's
# ``chetime`` carries 3 trailing NUL bytes ("100800\x00\x00\x00") — this
# byte-for-byte preservation is part of the round-trip contract.
_LS_OFFICIAL_RESPONSE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1310OutBlock": {
        "cts_time": "100700\x00\x00\x00",
    },
    "t1310OutBlock1": [
        {
            "change": 25,
            "mdchecnt": 256,
            "sign": "2",
            "rechecnt": -18,
            "diff": "000.68",
            "mschecnt": 238,
            "chetime": "102700",
            "mdvolume": 119531,
            "revolume": 76076,
            "cvolume": 5,
            "volume": 321201,
            "chdegree": "00163.65",
            "price": 3685,
            "msvolume": 195607,
        },
        {
            "change": 25,
            "mdchecnt": 237,
            "sign": "2",
            "rechecnt": -20,
            "diff": "000.68",
            "mschecnt": 217,
            "chetime": "100800\x00\x00\x00",
            "mdvolume": 115072,
            "revolume": 64440,
            "cvolume": 69,
            "volume": 300647,
            "chdegree": "00156.00",
            "price": 3685,
            "msvolume": 179512,
        },
    ],
}


# ---------------------------------------------------------------------------
# 1. URL registration
# ---------------------------------------------------------------------------


class TestKoreaStockMarketURL:
    def test_market_url_exposed(self):
        assert URLS.KOREA_STOCK_MARKET_URL.endswith("/stock/market-data")
        assert URLS.KOREA_STOCK_MARKET_URL.startswith("https://")


# ---------------------------------------------------------------------------
# 2. blocks.py validation
# ---------------------------------------------------------------------------


class TestT1310InBlock:
    def test_valid_minimal(self):
        block = T1310InBlock(daygb="0", timegb="0", shcode="001200")
        assert block.daygb == "0"
        assert block.timegb == "0"
        assert block.shcode == "001200"
        assert block.endtime == ""
        assert block.cts_time == ""
        assert block.exchgubun == "K"

    def test_valid_full(self):
        block = T1310InBlock(
            daygb="1",
            timegb="1",
            shcode="005930",
            endtime="1500",
            cts_time="100700",
            exchgubun="U",
        )
        assert block.daygb == "1"
        assert block.timegb == "1"
        assert block.endtime == "1500"
        assert block.cts_time == "100700"
        assert block.exchgubun == "U"

    def test_invalid_daygb_rejected(self):
        with pytest.raises(ValidationError):
            T1310InBlock(daygb="2", timegb="0", shcode="001200")

    def test_invalid_timegb_rejected(self):
        with pytest.raises(ValidationError):
            T1310InBlock(daygb="0", timegb="9", shcode="001200")

    def test_invalid_exchgubun_rejected(self):
        with pytest.raises(ValidationError):
            T1310InBlock(daygb="0", timegb="0", shcode="001200", exchgubun="X")


class TestT1310OutBlock:
    def test_defaults(self):
        out = T1310OutBlock()
        assert out.cts_time == ""

    def test_decodes_continuation_payload(self):
        out = T1310OutBlock.model_validate({"cts_time": "100700"})
        assert out.cts_time == "100700"

    def test_decodes_payload_with_embedded_null_bytes(self):
        """LS-observed quirk: cts_time may contain embedded null bytes
        (e.g. '100700\\x00\\x00\\x00'). Byte-for-byte preservation is
        required because the value is echoed back as an opaque LS token.
        """
        raw = "100700\x00\x00\x00"
        out = T1310OutBlock.model_validate({"cts_time": raw})
        assert out.cts_time == raw
        assert len(out.cts_time) == 9

    def test_decodes_empty_terminal_payload(self):
        out = T1310OutBlock.model_validate({"cts_time": ""})
        assert out.cts_time == ""


class TestT1310OutBlock1:
    def test_decodes_ls_official_first_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1310OutBlock1"][0]
        out = T1310OutBlock1.model_validate(row)
        assert out.chetime == "102700"
        assert out.price == 3685
        assert out.sign == "2"
        assert out.change == 25
        assert out.diff == pytest.approx(0.68)
        assert isinstance(out.diff, float)
        assert out.cvolume == 5
        assert out.chdegree == pytest.approx(163.65)
        assert isinstance(out.chdegree, float)
        assert out.volume == 321201
        assert out.mdvolume == 119531
        assert out.mdchecnt == 256
        assert out.msvolume == 195607
        assert out.mschecnt == 238
        assert out.revolume == 76076
        assert out.rechecnt == -18

    def test_decodes_ls_official_second_row_with_null_bytes(self):
        """chetime preserves the 3 trailing NUL bytes byte-for-byte."""
        row = _LS_OFFICIAL_RESPONSE["t1310OutBlock1"][1]
        out = T1310OutBlock1.model_validate(row)
        assert out.chetime == "100800\x00\x00\x00"
        assert len(out.chetime) == 9
        assert out.cvolume == 69
        assert out.rechecnt == -20

    def test_rechecnt_accepts_negative(self):
        out = T1310OutBlock1.model_validate({"rechecnt": -42})
        assert out.rechecnt == -42

    def test_defaults_when_missing(self):
        out = T1310OutBlock1()
        assert out.chetime == ""
        assert out.price == 0
        assert out.sign == ""
        assert out.change == 0
        assert out.diff == 0.0
        assert out.chdegree == 0.0
        assert out.volume == 0
        assert out.cvolume == 0
        assert out.exchname == ""


class TestT1310LSExampleResponseRoundTrip:
    """Regression guard — full LS official example response must round-trip
    through the entire response envelope without ValidationError, and the
    null-byte chetime must survive.
    """

    def test_full_envelope_validates(self):
        rows = _LS_OFFICIAL_RESPONSE["t1310OutBlock1"]
        cont = _LS_OFFICIAL_RESPONSE["t1310OutBlock"]

        resp = T1310Response(
            header=None,
            cont_block=T1310OutBlock.model_validate(cont),
            block=[T1310OutBlock1.model_validate(r) for r in rows],
            rsp_cd=_LS_OFFICIAL_RESPONSE["rsp_cd"],
            rsp_msg=_LS_OFFICIAL_RESPONSE["rsp_msg"],
            status_code=200,
            error_msg=None,
        )

        assert resp.cont_block is not None
        assert resp.cont_block.cts_time == "100700\x00\x00\x00"
        assert len(resp.block) == 2
        assert resp.block[0].chetime == "102700"
        assert resp.block[1].chetime == "100800\x00\x00\x00"
        assert resp.rsp_cd == "00000"


# ---------------------------------------------------------------------------
# 3. TrT1310._build_response
# ---------------------------------------------------------------------------


class TestTrT1310BuildResponse:
    def _make_tr(self) -> TrT1310:
        return TrT1310(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1310",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, _LS_OFFICIAL_RESPONSE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.cont_block is not None
        assert result.cont_block.cts_time == "100700\x00\x00\x00"
        assert len(result.block) == 2
        assert result.block[0].price == 3685
        assert result.block[1].chetime == "100800\x00\x00\x00"
        assert result.header is not None
        assert isinstance(result.header, T1310ResponseHeader)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1310"},
            None,
        )
        assert result.status_code == 500
        assert result.error_msg is not None
        assert "500" in result.error_msg
        assert "Internal error" in result.error_msg
        assert result.header is None
        assert result.cont_block is None
        assert result.block == []

    def test_exception_path(self):
        tr = self._make_tr()
        result = tr._build_response(None, None, None, RuntimeError("boom"))
        assert result.error_msg == "boom"
        assert result.status_code is None
        assert result.cont_block is None
        assert result.block == []

    def test_no_outblock_yields_none_cont(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1310",
            "tr_cont": "N",
            "tr_cont_key": "",
        }
        result = tr._build_response(
            resp_obj,
            {"rsp_cd": "00000", "rsp_msg": "ok"},
            resp_headers,
            None,
        )
        assert result.cont_block is None
        assert result.block == []


# ---------------------------------------------------------------------------
# 4. Market domain class
# ---------------------------------------------------------------------------


class TestMarketDomain:
    def test_t1310_returns_tr_instance(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        body = T1310InBlock(daygb="0", timegb="0", shcode="001200", exchgubun="K")
        tr = market.t1310(body=body)
        assert isinstance(tr, TrT1310)
        assert tr.request_data.body["t1310InBlock"].shcode == "001200"
        assert tr.request_data.body["t1310InBlock"].daygb == "0"
        assert tr.request_data.body["t1310InBlock"].timegb == "0"

    def test_korean_alias_class_level(self):
        assert Market.t1310 is Market.주식당일전일분틱조회

    def test_token_manager_required(self):
        with pytest.raises(ValueError):
            Market(token_manager=None)


# ---------------------------------------------------------------------------
# 5. KoreaStock entry point
# ---------------------------------------------------------------------------


class TestKoreaStockMarketEntry:
    def test_chained_call_korean_alias(self):
        tm = _make_token_manager()
        ks = KoreaStock(tm)
        body = T1310InBlock(daygb="1", timegb="1", shcode="005930", exchgubun="U")
        tr = ks.시세().주식당일전일분틱조회(body=body)
        assert isinstance(tr, TrT1310)
        assert tr.request_data.body["t1310InBlock"].shcode == "005930"
        assert tr.request_data.body["t1310InBlock"].daygb == "1"


# ---------------------------------------------------------------------------
# 6. occurs_req updater — cts_time propagation
# ---------------------------------------------------------------------------


class TestTrT1310OccursReqUpdater:
    """Verify that the occurs_req updater closure feeds ``cts_time`` from
    the previous response's cont_block back into the next request's
    ``T1310InBlock.cts_time``. Missing this would cause an infinite loop.
    """

    def test_updater_propagates_cts_time(self):
        tr = TrT1310(_make_request())

        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1310Response(
            header=T1310ResponseHeader(
                content_type="application/json",
                tr_cd="t1310",
                tr_cont="Y",
                tr_cont_key="next-key",
            ),
            cont_block=T1310OutBlock(cts_time="100700\x00\x00\x00"),
            block=[],
            rsp_cd="00000",
            rsp_msg="OK",
        )
        updater(tr.request_data, resp)

        assert tr.request_data.header.tr_cont_key == "next-key"
        assert tr.request_data.header.tr_cont == "Y"
        # Null bytes preserved through the cursor handoff.
        assert tr.request_data.body["t1310InBlock"].cts_time == "100700\x00\x00\x00"

    def test_updater_raises_on_missing_continuation(self):
        tr = TrT1310(_make_request())
        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1310Response(
            header=None, cont_block=None, block=[], rsp_cd="", rsp_msg=""
        )
        with pytest.raises(ValueError, match="missing continuation"):
            updater(tr.request_data, resp)


# ---------------------------------------------------------------------------
# 7. Field(examples=[...]) regression guard
# ---------------------------------------------------------------------------


class TestFieldExamplesValidate:
    """Each value in ``Field(examples=[...])`` must round-trip through
    ``TypeAdapter(<annotation>).validate_python(value)``. AI chatbots learn
    from these; an example with a wrong type or wrong Literal value silently
    teaches bad input.
    """

    @pytest.mark.parametrize(
        "model_cls",
        [T1310InBlock, T1310OutBlock, T1310OutBlock1],
        ids=["T1310InBlock", "T1310OutBlock", "T1310OutBlock1"],
    )
    def test_all_field_examples_validate(self, model_cls: Type[BaseModel]):
        failures: list[str] = []
        for field_name, field_info in model_cls.model_fields.items():
            examples = field_info.examples or []
            if not examples:
                continue
            adapter = TypeAdapter(field_info.annotation)
            for ex in examples:
                try:
                    adapter.validate_python(ex)
                except ValidationError as exc:
                    failures.append(
                        f"{model_cls.__name__}.{field_name} example {ex!r} "
                        f"failed: {exc.errors()[0]['msg']}"
                    )
        assert not failures, "Invalid Field examples:\n" + "\n".join(failures)

    @pytest.mark.parametrize(
        "model_cls",
        [T1310InBlock, T1310OutBlock1],
        ids=["T1310InBlock", "T1310OutBlock1"],
    )
    def test_every_field_has_examples(self, model_cls: Type[BaseModel]):
        missing = [
            name
            for name, info in model_cls.model_fields.items()
            if not (info.examples or [])
        ]
        assert not missing, (
            f"{model_cls.__name__} fields without examples=[...]: {missing}. "
            "All InBlock / OutBlock1 fields must carry AI-readable examples."
        )


# ---------------------------------------------------------------------------
# 8. Model fields coverage — guard against silent LS spec drift
# ---------------------------------------------------------------------------


class TestModelFieldsCoverage:
    """If LS adds or removes fields silently, this guard fires immediately."""

    def test_inblock_fields(self):
        assert set(T1310InBlock.model_fields) == {
            "daygb", "timegb", "shcode", "endtime", "cts_time", "exchgubun",
        }

    def test_outblock_fields(self):
        assert set(T1310OutBlock.model_fields) == {"cts_time"}

    def test_outblock1_fields(self):
        expected = {
            "chetime", "price", "sign", "change", "diff", "cvolume",
            "chdegree", "volume",
            "mdvolume", "mdchecnt", "msvolume", "mschecnt",
            "revolume", "rechecnt", "exchname",
        }
        assert set(T1310OutBlock1.model_fields) == expected


# ---------------------------------------------------------------------------
# 9. LS-UNDECLARED ``sign`` enum mapping — must carry disclaimer, must NOT
#    embed t1302-style 1~5 mapping (anti-inference policy).
# ---------------------------------------------------------------------------


class TestSignEnumNotInferred:
    """For t1310 LS does NOT publish a ``sign`` enum mapping (unlike t1302).
    The description must carry an explicit "not declared" disclaimer, and
    must NOT embed t1302's 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락
    mapping — that would teach the AI chatbot a false certainty.
    """

    def test_sign_description_carries_not_declared_disclaimer(self):
        desc = T1310OutBlock1.model_fields["sign"].description or ""
        assert "NOT declared" in desc or "not declared" in desc, (
            "T1310OutBlock1.sign description must carry a 'not declared' "
            "disclaimer — LS does not publish the enum mapping for t1310."
        )

    def test_sign_description_does_not_embed_t1302_mapping(self):
        desc = T1310OutBlock1.model_fields["sign"].description or ""
        for forbidden in [
            "상한", "보합", "하한", "하락",
            "upper limit", "unchanged", "lower limit",
        ]:
            assert forbidden not in desc, (
                f"T1310OutBlock1.sign: must not embed t1302-style mapping "
                f"token '{forbidden}' — LS does not declare it for t1310."
            )


# ---------------------------------------------------------------------------
# 10. Anti-inference guard — fields LS did NOT declare for t1310
# ---------------------------------------------------------------------------


class TestNoInferredUnitOrSemantics:
    """For t1310 LS does NOT declare:
        - Currency unit / decimal scale of price
        - Sign convention of change / revolume / rechecnt
        - Time-window semantics of chetime (bucket start vs end)
        - Relationship between volume (cumulative) and cvolume (per-row)
        - Time ordering of rows
    Descriptions must not assert these to avoid teaching the AI chatbot
    false certainty.
    """

    def test_price_no_inferred_currency(self):
        desc = T1310OutBlock1.model_fields["price"].description or ""
        for forbidden in ["KRW", "in won", "Korean won"]:
            assert forbidden not in desc, (
                f"T1310OutBlock1.price: must not infer currency unit "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_change_no_inferred_sign_convention(self):
        desc = T1310OutBlock1.model_fields["change"].description or ""
        for forbidden in [
            "positive when up", "negative when down",
            "always positive", "always non-negative",
        ]:
            assert forbidden not in desc, (
                f"T1310OutBlock1.change: must not assert sign convention "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_revolume_no_inferred_sign_convention(self):
        desc = T1310OutBlock1.model_fields["revolume"].description or ""
        for forbidden in [
            "positive when buyers dominate",
            "negative when sellers dominate",
            "buy minus sell", "sell minus buy",
        ]:
            assert forbidden not in desc, (
                f"T1310OutBlock1.revolume: must not assert sign convention "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_rechecnt_no_inferred_sign_convention(self):
        desc = T1310OutBlock1.model_fields["rechecnt"].description or ""
        for forbidden in [
            "positive when buyers dominate",
            "buy minus sell", "sell minus buy",
        ]:
            assert forbidden not in desc, (
                f"T1310OutBlock1.rechecnt: must not assert sign convention "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_chetime_carries_bucket_semantics_disclaimer(self):
        """LS does not declare whether ``chetime`` marks the bucket start
        or end. The description must keep an explicit disclaimer (positive
        assertion guard, matching the t1302 anti-inference pattern) so
        future readers and the AI chatbot do not assume either
        interpretation.
        """
        desc = T1310OutBlock1.model_fields["chetime"].description or ""
        assert "not declared" in desc, (
            "T1310OutBlock1.chetime: must keep the LS spec disclaimer "
            "for bucket-time semantics (start vs end)."
        )

    def test_volume_cvolume_relationship_not_asserted(self):
        v_desc = T1310OutBlock1.model_fields["volume"].description or ""
        c_desc = T1310OutBlock1.model_fields["cvolume"].description or ""
        for forbidden in [
            "volume = sum of cvolume",
            "cvolume sums to volume",
            "running total of cvolume",
        ]:
            assert forbidden not in v_desc, (
                f"T1310OutBlock1.volume: must not assert relationship "
                f"'{forbidden}' with cvolume — LS spec does not declare it."
            )
            assert forbidden not in c_desc, (
                f"T1310OutBlock1.cvolume: must not assert relationship "
                f"'{forbidden}' with volume — LS spec does not declare it."
            )

    def test_block_rows_ordering_not_asserted(self):
        """The ``block`` field's description must not claim a time ordering
        (ascending / descending) since LS does not declare it.
        """
        desc = T1310Response.model_fields["block"].description or ""
        for forbidden in [
            "sorted ascending", "sorted descending",
            "newest first", "oldest first",
            "chronological order",
        ]:
            assert forbidden not in desc, (
                f"T1310Response.block: must not assert ordering "
                f"'{forbidden}' — LS spec does not declare it."
            )
