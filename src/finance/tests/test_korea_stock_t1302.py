"""Unit tests for t1302 주식분별주가조회 (Korea Stock Per-minute Price TR).

Covers:
    - blocks.py — Pydantic input/output validation, including LS official
      example response round-trip.
    - TrT1302._build_response — happy / HTTP error / exception paths.
    - Market domain class — Korean alias bridge to TrT1302.
    - KoreaStock chained call — ``ks.시세().주식분별주가조회(...)`` Korean alias path.
    - occurs_req updater — verifies that ``cts_time`` cursor transfers from
      OutBlock back into InBlock for paged calls.
    - Field(examples=[...]) regression guards — examples present + types
      validate against declared annotations.
    - LS-declared enum mapping — ``sign`` description must embed the
      LS-published 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락 mapping.
    - Anti-inference guard — fields LS did NOT declare (currency unit,
      change sign convention, bucket-time semantics) must not embed
      inferred assertions.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.market import Market
from programgarden_finance.ls.korea_stock.market.t1302 import TrT1302
from programgarden_finance.ls.korea_stock.market.t1302.blocks import (
    T1302InBlock,
    T1302OutBlock,
    T1302OutBlock1,
    T1302Request,
    T1302Response,
    T1302ResponseHeader,
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


def _make_request(**overrides: Any) -> T1302Request:
    body = T1302InBlock(
        shcode=overrides.pop("shcode", "005930"),
        gubun=overrides.pop("gubun", "0"),
        time=overrides.pop("time", ""),
        cnt=overrides.pop("cnt", 50),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1302Request(body={"t1302InBlock": body})


# LS official example response (user-supplied).
_LS_OFFICIAL_RESPONSE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1302OutBlock": {
        "cts_time": "101700",
    },
    "t1302OutBlock1": [
        {
            "mdchecnttm": 0,
            "mdvolumetm": 0,
            "change": 25,
            "mdchecnt": 256,
            "sign": "2",
            "rechecnt": -18,
            "msvolumetm": 0,
            "diff": "000.68",
            "mschecnt": 238,
            "chetime": "102700",
            "mdvolume": 119531,
            "revolume": 76076,
            "cvolume": 0,
            "volume": 321201,
            "chdegree": "163.65",
            "high": 3685,
            "low": 3685,
            "msvolume": 195607,
            "mschecnttm": 0,
            "totofferrem": 18352,
            "close": 3685,
            "open": 3685,
            "totbidrem": 35195,
        }
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


class TestT1302InBlock:
    def test_valid_minimal(self):
        block = T1302InBlock(shcode="005930", gubun="0", cnt=50, exchgubun="K")
        assert block.shcode == "005930"
        assert block.gubun == "0"
        assert block.time == ""
        assert block.cnt == 50
        assert block.exchgubun == "K"

    def test_valid_with_continuation_cursor(self):
        block = T1302InBlock(
            shcode="001200", gubun="1", time="101700", cnt=900, exchgubun="U"
        )
        assert block.time == "101700"
        assert block.cnt == 900
        assert block.exchgubun == "U"

    def test_invalid_gubun_rejected(self):
        with pytest.raises(ValidationError):
            T1302InBlock(shcode="005930", gubun="9", cnt=50, exchgubun="K")

    def test_invalid_exchgubun_rejected(self):
        with pytest.raises(ValidationError):
            T1302InBlock(shcode="005930", gubun="0", cnt=50, exchgubun="X")


class TestT1302OutBlock:
    def test_defaults(self):
        out = T1302OutBlock()
        assert out.cts_time == ""

    def test_decodes_continuation_payload(self):
        out = T1302OutBlock.model_validate({"cts_time": "101700"})
        assert out.cts_time == "101700"

    def test_decodes_empty_terminal_payload(self):
        out = T1302OutBlock.model_validate({"cts_time": ""})
        assert out.cts_time == ""


class TestT1302OutBlock1:
    def test_decodes_ls_official_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1302OutBlock1"][0]
        out = T1302OutBlock1.model_validate(row)
        assert out.chetime == "102700"
        assert out.close == 3685
        assert out.sign == "2"
        assert out.change == 25
        assert out.diff == pytest.approx(0.68)
        assert isinstance(out.diff, float)
        assert out.chdegree == pytest.approx(163.65)
        assert isinstance(out.chdegree, float)
        assert out.mdvolume == 119531
        assert out.msvolume == 195607
        assert out.revolume == 76076
        assert out.mdchecnt == 256
        assert out.mschecnt == 238
        assert out.rechecnt == -18
        assert out.volume == 321201
        assert out.open == 3685
        assert out.high == 3685
        assert out.low == 3685
        assert out.cvolume == 0
        assert out.mdchecnttm == 0
        assert out.mschecnttm == 0
        assert out.totofferrem == 18352
        assert out.totbidrem == 35195
        assert out.mdvolumetm == 0
        assert out.msvolumetm == 0

    def test_rechecnt_accepts_negative(self):
        out = T1302OutBlock1.model_validate({"rechecnt": -42})
        assert out.rechecnt == -42

    def test_defaults_when_missing(self):
        out = T1302OutBlock1()
        assert out.chetime == ""
        assert out.close == 0
        assert out.sign == ""
        assert out.change == 0
        assert out.diff == 0.0
        assert out.chdegree == 0.0
        assert out.volume == 0


class TestT1302LSExampleResponseRoundTrip:
    """Regression guard — full LS official example response must round-trip
    through the entire response envelope without ValidationError.
    """

    def test_full_envelope_validates(self):
        rows = _LS_OFFICIAL_RESPONSE["t1302OutBlock1"]
        cont = _LS_OFFICIAL_RESPONSE["t1302OutBlock"]

        resp = T1302Response(
            header=None,
            cont_block=T1302OutBlock.model_validate(cont),
            block=[T1302OutBlock1.model_validate(r) for r in rows],
            rsp_cd=_LS_OFFICIAL_RESPONSE["rsp_cd"],
            rsp_msg=_LS_OFFICIAL_RESPONSE["rsp_msg"],
            status_code=200,
            error_msg=None,
        )

        assert resp.cont_block is not None
        assert resp.cont_block.cts_time == "101700"
        assert len(resp.block) == 1
        assert resp.block[0].chetime == "102700"
        assert resp.rsp_cd == "00000"


# ---------------------------------------------------------------------------
# 3. TrT1302._build_response
# ---------------------------------------------------------------------------


class TestTrT1302BuildResponse:
    def _make_tr(self) -> TrT1302:
        return TrT1302(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1302",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, _LS_OFFICIAL_RESPONSE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.cont_block is not None
        assert result.cont_block.cts_time == "101700"
        assert len(result.block) == 1
        assert result.block[0].close == 3685
        assert result.header is not None
        assert isinstance(result.header, T1302ResponseHeader)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1302"},
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


# ---------------------------------------------------------------------------
# 4. Market domain class
# ---------------------------------------------------------------------------


class TestMarketDomain:
    def test_t1302_returns_tr_instance(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        body = T1302InBlock(shcode="005930", gubun="0", cnt=50, exchgubun="K")
        tr = market.t1302(body=body)
        assert isinstance(tr, TrT1302)
        assert tr.request_data.body["t1302InBlock"].shcode == "005930"
        assert tr.request_data.body["t1302InBlock"].gubun == "0"

    def test_korean_alias_class_level(self):
        assert Market.t1302 is Market.주식분별주가조회

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
        body = T1302InBlock(shcode="001200", gubun="1", cnt=900, exchgubun="K")
        tr = ks.시세().주식분별주가조회(body=body)
        assert isinstance(tr, TrT1302)
        assert tr.request_data.body["t1302InBlock"].shcode == "001200"
        assert tr.request_data.body["t1302InBlock"].cnt == 900


# ---------------------------------------------------------------------------
# 6. occurs_req updater — cts_time propagation
# ---------------------------------------------------------------------------


class TestTrT1302OccursReqUpdater:
    """Verify that the occurs_req updater closure feeds ``cts_time`` from
    the previous response's cont_block back into the next request's
    ``T1302InBlock.time``. Missing this would cause an infinite loop.
    """

    def test_updater_propagates_cts_time(self):
        tr = TrT1302(_make_request())

        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1302Response(
            header=T1302ResponseHeader(
                content_type="application/json",
                tr_cd="t1302",
                tr_cont="Y",
                tr_cont_key="next-key",
            ),
            cont_block=T1302OutBlock(cts_time="101700"),
            block=[],
            rsp_cd="00000",
            rsp_msg="OK",
        )
        updater(tr.request_data, resp)

        assert tr.request_data.header.tr_cont_key == "next-key"
        assert tr.request_data.header.tr_cont == "Y"
        assert tr.request_data.body["t1302InBlock"].time == "101700"

    def test_updater_raises_on_missing_continuation(self):
        tr = TrT1302(_make_request())
        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1302Response(
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
        [T1302InBlock, T1302OutBlock, T1302OutBlock1],
        ids=["T1302InBlock", "T1302OutBlock", "T1302OutBlock1"],
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
        [T1302InBlock, T1302OutBlock1],
        ids=["T1302InBlock", "T1302OutBlock1"],
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
        assert set(T1302InBlock.model_fields) == {
            "shcode", "gubun", "time", "cnt", "exchgubun",
        }

    def test_outblock_fields(self):
        assert set(T1302OutBlock.model_fields) == {"cts_time"}

    def test_outblock1_fields(self):
        expected = {
            "chetime", "close", "sign", "change", "diff", "chdegree",
            "mdvolume", "msvolume", "revolume",
            "mdchecnt", "mschecnt", "rechecnt",
            "volume", "open", "high", "low", "cvolume",
            "mdchecnttm", "mschecnttm",
            "totofferrem", "totbidrem",
            "mdvolumetm", "msvolumetm",
        }
        assert set(T1302OutBlock1.model_fields) == expected


# ---------------------------------------------------------------------------
# 9. LS-declared enum mapping — sign field documents the published mapping
# ---------------------------------------------------------------------------


class TestSignEnumDocumented:
    """For t1302 LS publishes the ``sign`` enum mapping
    (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락). Unlike t1109 (where LS
    does not declare it), the description must embed the mapping so the AI
    chatbot can generate correct workflows.
    """

    def test_sign_enum_mapping_present(self):
        desc = T1302OutBlock1.model_fields["sign"].description or ""
        for token in [
            "'1'", "'2'", "'3'", "'4'", "'5'",
            "upper limit", "up", "unchanged", "lower limit", "down",
            "상한", "상승", "보합", "하한", "하락",
        ]:
            assert token in desc, (
                f"T1302OutBlock1.sign description missing LS-declared token "
                f"'{token}'. LS publishes the full 1~5 enum mapping for t1302; "
                f"description must mirror it for AI chatbot accuracy."
            )


# ---------------------------------------------------------------------------
# 10. Anti-inference guard — fields LS did NOT declare
# ---------------------------------------------------------------------------


class TestNoInferredUnitOrSemantics:
    """For t1302 LS does NOT declare:
        - Currency unit of close/open/high/low/change
        - Sign convention of change / revolume / rechecnt
        - Whether ``chetime`` marks bucket start or end
        - Relationship between ``volume`` and ``cvolume``
    Descriptions must not assert these to avoid teaching the AI chatbot
    false certainty.
    """

    def test_close_no_inferred_currency(self):
        desc = T1302OutBlock1.model_fields["close"].description or ""
        assert "in KRW" not in desc, (
            "T1302OutBlock1.close: must not infer KRW unit — LS spec does "
            "not declare currency unit explicitly."
        )

    def test_change_no_inferred_sign_convention(self):
        desc = T1302OutBlock1.model_fields["change"].description or ""
        for forbidden in [
            "positive when up", "negative when down",
            "always positive", "always non-negative",
        ]:
            assert forbidden not in desc, (
                f"T1302OutBlock1.change: must not assert sign convention "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_chetime_carries_bucket_semantics_disclaimer(self):
        """LS does not declare whether ``chetime`` marks the bucket start
        or end. The description must keep an explicit ``not declared``
        disclaimer so future readers (and the AI chatbot) do not assume
        either interpretation.
        """
        desc = T1302OutBlock1.model_fields["chetime"].description or ""
        assert "not formally declared" in desc, (
            "T1302OutBlock1.chetime: must keep the LS spec disclaimer "
            "for bucket-time semantics (start vs end)."
        )

    def test_volume_cvolume_relationship_not_asserted(self):
        v_desc = T1302OutBlock1.model_fields["volume"].description or ""
        c_desc = T1302OutBlock1.model_fields["cvolume"].description or ""
        for forbidden in [
            "volume = sum of cvolume",
            "cvolume sums to volume",
            "running total of cvolume",
        ]:
            assert forbidden not in v_desc, (
                f"T1302OutBlock1.volume: must not assert relationship "
                f"'{forbidden}' with cvolume — LS spec does not declare it."
            )
            assert forbidden not in c_desc, (
                f"T1302OutBlock1.cvolume: must not assert relationship "
                f"'{forbidden}' with volume — LS spec does not declare it."
            )
