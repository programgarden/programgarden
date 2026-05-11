"""Unit tests for t1305 기간별주가 (Korea Stock Period-based Price TR).

Covers:
    - blocks.py — Pydantic input/output validation, including LS official
      example response round-trip.
    - TrT1305._build_response — happy / HTTP error / exception paths.
    - Market domain class — Korean alias bridge to TrT1305.
    - KoreaStock chained call — ``ks.시세().기간별주가(...)`` Korean alias path.
    - occurs_req updater — verifies that ``date`` cursor transfers from
      OutBlock back into InBlock for paged calls.
    - Field(examples=[...]) regression guards — examples present + types
      validate against declared annotations.
    - LS-declared enum mapping — ``sign`` description must embed the
      LS-published 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락 mapping.
    - LS-declared enum mapping — ``h_sign`` and ``l_sign`` descriptions
      must embed the LS-published 2=상승 / 3=보합 / 5=하락 mapping.
    - Anti-inference guard — fields LS did NOT declare (o_sign enum mapping,
      change sign conventions, currency unit beyond LS annotation,
      date ordering) must not embed inferred assertions.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.market import Market
from programgarden_finance.ls.korea_stock.market.t1305 import TrT1305
from programgarden_finance.ls.korea_stock.market.t1305.blocks import (
    T1305InBlock,
    T1305OutBlock,
    T1305OutBlock1,
    T1305Request,
    T1305Response,
    T1305ResponseHeader,
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


def _make_request(**overrides: Any) -> T1305Request:
    body = T1305InBlock(
        shcode=overrides.pop("shcode", "001200"),
        dwmcode=overrides.pop("dwmcode", 1),
        date=overrides.pop("date", ""),
        idx=overrides.pop("idx", 0),
        cnt=overrides.pop("cnt", 50),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1305Request(body={"t1305InBlock": body})


# LS official example response (user-supplied).
_LS_OFFICIAL_RESPONSE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1305OutBlock": {
        "date": "20230605",
        "cnt": 1,
        "idx": 0,
    },
    "t1305OutBlock1": [
        {
            "date": "20230605",
            "marketcap": 356953,
            "o_diff": "0.00",
            "sign": "2",
            "l_sign": "5",
            "l_diff": "-0.41",
            "high": 3750,
            "covolume": 0,
            "low": 3645,
            "o_sign": "3",
            "h_sign": "2",
            "close": 3685,
            "value": 1188,
            "h_diff": "2.46",
            "diff_vol": "-74.79",
            "h_change": 90,
            "l_change": -15,
            "change": 25,
            "shcode": "001200",
            "o_change": 0,
            "diff": "0.68",
            "changerate": "0.33",
            "volume": 321201,
            "chdegree": "163.65",
            "ppvolume": 0,
            "sojinrate": "7.17",
            "fpvolume": 0,
            "open": 3660,
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


class TestT1305InBlock:
    def test_valid_minimal(self):
        block = T1305InBlock(shcode="001200", dwmcode=1, cnt=50, exchgubun="K")
        assert block.shcode == "001200"
        assert block.dwmcode == 1
        assert block.date == ""
        assert block.idx == 0
        assert block.cnt == 50
        assert block.exchgubun == "K"

    def test_valid_weekly(self):
        block = T1305InBlock(
            shcode="005930", dwmcode=2, date="20230605", cnt=900, exchgubun="U"
        )
        assert block.dwmcode == 2
        assert block.date == "20230605"
        assert block.cnt == 900
        assert block.exchgubun == "U"

    def test_valid_monthly(self):
        block = T1305InBlock(shcode="000660", dwmcode=3, cnt=10, exchgubun="N")
        assert block.dwmcode == 3

    def test_invalid_dwmcode_rejected(self):
        with pytest.raises(ValidationError):
            T1305InBlock(shcode="001200", dwmcode=4, cnt=50, exchgubun="K")

    def test_invalid_exchgubun_rejected(self):
        with pytest.raises(ValidationError):
            T1305InBlock(shcode="001200", dwmcode=1, cnt=50, exchgubun="X")

    def test_idx_default_zero(self):
        block = T1305InBlock(shcode="001200", dwmcode=1, cnt=1, exchgubun="K")
        assert block.idx == 0

    def test_idx_int_coercion(self):
        # LS example sends int 0 even though spec says "사용안함 (Space)"
        block = T1305InBlock(shcode="001200", dwmcode=1, cnt=1, exchgubun="K", idx=0)
        assert isinstance(block.idx, int)
        assert block.idx == 0


class TestT1305OutBlock:
    def test_defaults(self):
        out = T1305OutBlock()
        assert out.cnt == 0
        assert out.date == ""
        assert out.idx == 0
        assert out.ex_shcode == ""

    def test_decodes_ls_official_payload(self):
        out = T1305OutBlock.model_validate({"date": "20230605", "cnt": 1, "idx": 0})
        assert out.date == "20230605"
        assert out.cnt == 1
        assert out.idx == 0
        # ex_shcode absent → defaults to ""
        assert out.ex_shcode == ""

    def test_decodes_empty_terminal_payload(self):
        out = T1305OutBlock.model_validate({"date": "", "cnt": 0, "idx": 0})
        assert out.date == ""

    def test_ex_shcode_optional(self):
        # ex_shcode absent in example response — must not raise
        out = T1305OutBlock.model_validate({"date": "20230605", "cnt": 1, "idx": 0})
        assert out.ex_shcode == "" or out.ex_shcode is None or isinstance(out.ex_shcode, str)

    def test_ex_shcode_present_when_given(self):
        out = T1305OutBlock.model_validate(
            {"date": "20230605", "cnt": 1, "idx": 0, "ex_shcode": "001200    "}
        )
        assert out.ex_shcode == "001200    "


class TestT1305OutBlock1:
    def test_decodes_ls_official_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1305OutBlock1"][0]
        out = T1305OutBlock1.model_validate(row)
        assert out.date == "20230605"
        assert out.open == 3660
        assert out.high == 3750
        assert out.low == 3645
        assert out.close == 3685
        assert out.sign == "2"
        assert out.change == 25
        assert out.diff == pytest.approx(0.68)
        assert isinstance(out.diff, float)
        assert out.volume == 321201
        assert out.diff_vol == pytest.approx(-74.79)
        assert isinstance(out.diff_vol, float)
        assert out.chdegree == pytest.approx(163.65)
        assert isinstance(out.chdegree, float)
        assert out.sojinrate == pytest.approx(7.17)
        assert isinstance(out.sojinrate, float)
        assert out.changerate == pytest.approx(0.33)
        assert isinstance(out.changerate, float)
        assert out.fpvolume == 0
        assert out.covolume == 0
        assert out.shcode == "001200"
        assert out.value == 1188
        assert out.ppvolume == 0
        assert out.o_sign == "3"
        assert out.o_change == 0
        assert out.o_diff == pytest.approx(0.0)
        assert isinstance(out.o_diff, float)
        assert out.h_sign == "2"
        assert out.h_change == 90
        assert out.h_diff == pytest.approx(2.46)
        assert isinstance(out.h_diff, float)
        assert out.l_sign == "5"
        assert out.l_change == -15
        assert out.l_diff == pytest.approx(-0.41)
        assert isinstance(out.l_diff, float)
        assert out.marketcap == 356953

    def test_l_change_accepts_negative(self):
        out = T1305OutBlock1.model_validate({"l_change": -42})
        assert out.l_change == -42

    def test_defaults_when_missing(self):
        out = T1305OutBlock1()
        assert out.date == ""
        assert out.open == 0
        assert out.high == 0
        assert out.low == 0
        assert out.close == 0
        assert out.sign == ""
        assert out.change == 0
        assert out.diff == 0.0
        assert out.volume == 0
        assert out.diff_vol == 0.0
        assert out.chdegree == 0.0
        assert out.sojinrate == 0.0
        assert out.changerate == 0.0
        assert out.fpvolume == 0
        assert out.covolume == 0
        assert out.shcode == ""
        assert out.value == 0
        assert out.ppvolume == 0
        assert out.o_sign == ""
        assert out.o_change == 0
        assert out.o_diff == 0.0
        assert out.h_sign == ""
        assert out.h_change == 0
        assert out.h_diff == 0.0
        assert out.l_sign == ""
        assert out.l_change == 0
        assert out.l_diff == 0.0
        assert out.marketcap == 0


class TestT1305LSExampleResponseRoundTrip:
    """Regression guard — full LS official example response must round-trip
    through the entire response envelope without ValidationError.
    """

    def test_full_envelope_validates(self):
        rows = _LS_OFFICIAL_RESPONSE["t1305OutBlock1"]
        cont = _LS_OFFICIAL_RESPONSE["t1305OutBlock"]

        resp = T1305Response(
            header=None,
            cont_block=T1305OutBlock.model_validate(cont),
            block=[T1305OutBlock1.model_validate(r) for r in rows],
            rsp_cd=_LS_OFFICIAL_RESPONSE["rsp_cd"],
            rsp_msg=_LS_OFFICIAL_RESPONSE["rsp_msg"],
            status_code=200,
            error_msg=None,
        )

        assert resp.cont_block is not None
        assert resp.cont_block.date == "20230605"
        assert resp.cont_block.cnt == 1
        # ex_shcode absent in example — must not raise
        assert resp.cont_block.ex_shcode == "" or resp.cont_block.ex_shcode is None
        assert len(resp.block) == 1
        assert resp.block[0].date == "20230605"
        assert resp.block[0].close == 3685
        assert resp.rsp_cd == "00000"


# ---------------------------------------------------------------------------
# 3. TrT1305._build_response
# ---------------------------------------------------------------------------


class TestTrT1305BuildResponse:
    def _make_tr(self) -> TrT1305:
        return TrT1305(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1305",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, _LS_OFFICIAL_RESPONSE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.cont_block is not None
        assert result.cont_block.date == "20230605"
        assert len(result.block) == 1
        assert result.block[0].close == 3685
        assert result.header is not None
        assert isinstance(result.header, T1305ResponseHeader)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1305"},
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
    def test_t1305_returns_tr_instance(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        body = T1305InBlock(shcode="001200", dwmcode=1, cnt=50, exchgubun="K")
        tr = market.t1305(body=body)
        assert isinstance(tr, TrT1305)
        assert tr.request_data.body["t1305InBlock"].shcode == "001200"
        assert tr.request_data.body["t1305InBlock"].dwmcode == 1

    def test_korean_alias_class_level(self):
        assert Market.t1305 is Market.기간별주가

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
        body = T1305InBlock(shcode="001200", dwmcode=2, cnt=900, exchgubun="K")
        tr = ks.시세().기간별주가(body=body)
        assert isinstance(tr, TrT1305)
        assert tr.request_data.body["t1305InBlock"].shcode == "001200"
        assert tr.request_data.body["t1305InBlock"].cnt == 900


# ---------------------------------------------------------------------------
# 6. occurs_req updater — date propagation
# ---------------------------------------------------------------------------


class TestTrT1305OccursReqUpdater:
    """Verify that the occurs_req updater closure feeds ``date`` from
    the previous response's cont_block back into the next request's
    ``T1305InBlock.date``. Missing this would cause an infinite loop.
    """

    def test_updater_propagates_date(self):
        tr = TrT1305(_make_request())

        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1305Response(
            header=T1305ResponseHeader(
                content_type="application/json",
                tr_cd="t1305",
                tr_cont="Y",
                tr_cont_key="next-key",
            ),
            cont_block=T1305OutBlock(date="20230605", cnt=1, idx=0),
            block=[],
            rsp_cd="00000",
            rsp_msg="OK",
        )
        updater(tr.request_data, resp)

        assert tr.request_data.header.tr_cont_key == "next-key"
        assert tr.request_data.header.tr_cont == "Y"
        assert tr.request_data.body["t1305InBlock"].date == "20230605"

    def test_updater_raises_on_missing_continuation(self):
        tr = TrT1305(_make_request())
        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1305Response(
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
        [T1305InBlock, T1305OutBlock, T1305OutBlock1],
        ids=["T1305InBlock", "T1305OutBlock", "T1305OutBlock1"],
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
        [T1305InBlock, T1305OutBlock1],
        ids=["T1305InBlock", "T1305OutBlock1"],
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
        assert set(T1305InBlock.model_fields) == {
            "shcode", "dwmcode", "date", "idx", "cnt", "exchgubun",
        }

    def test_outblock_fields(self):
        assert set(T1305OutBlock.model_fields) == {"cnt", "date", "idx", "ex_shcode"}

    def test_outblock1_fields(self):
        expected = {
            "date", "open", "high", "low", "close",
            "sign", "change", "diff",
            "volume", "diff_vol", "chdegree", "sojinrate", "changerate",
            "fpvolume", "covolume", "shcode", "value", "ppvolume",
            "o_sign", "o_change", "o_diff",
            "h_sign", "h_change", "h_diff",
            "l_sign", "l_change", "l_diff",
            "marketcap",
        }
        assert set(T1305OutBlock1.model_fields) == expected


# ---------------------------------------------------------------------------
# 9. LS-declared enum mapping — sign / h_sign / l_sign fields
# ---------------------------------------------------------------------------


class TestSignEnumDocumented:
    """For t1305 LS publishes the ``sign`` enum mapping
    (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락). The description must embed
    the mapping so the AI chatbot can generate correct workflows.
    """

    def test_sign_enum_mapping_present(self):
        desc = T1305OutBlock1.model_fields["sign"].description or ""
        for token in [
            "'1'", "'2'", "'3'", "'4'", "'5'",
            "upper limit", "up", "unchanged", "lower limit", "down",
            "상한", "상승", "보합", "하한", "하락",
        ]:
            assert token in desc, (
                f"T1305OutBlock1.sign description missing LS-declared token "
                f"'{token}'. LS publishes the full 1~5 enum mapping for t1305; "
                f"description must mirror it for AI chatbot accuracy."
            )

    def test_h_sign_enum_mapping_present(self):
        desc = T1305OutBlock1.model_fields["h_sign"].description or ""
        for token in ["'2'", "'3'", "'5'", "상승", "보합", "하락"]:
            assert token in desc, (
                f"T1305OutBlock1.h_sign description missing LS-declared token "
                f"'{token}'. LS declares h_sign enum as 2/3/5 for t1305."
            )

    def test_l_sign_enum_mapping_present(self):
        desc = T1305OutBlock1.model_fields["l_sign"].description or ""
        for token in ["'2'", "'3'", "'5'", "상승", "보합", "하락"]:
            assert token in desc, (
                f"T1305OutBlock1.l_sign description missing LS-declared token "
                f"'{token}'. LS declares l_sign enum as 2/3/5 for t1305."
            )


# ---------------------------------------------------------------------------
# 10. Anti-inference guard — fields LS did NOT declare
# ---------------------------------------------------------------------------


class TestNoInferredUnitOrSemantics:
    """For t1305 LS does NOT declare:
        - o_sign enum mapping
        - Currency unit of close/open/high/low/change beyond LS annotation
        - Sign convention of change / o_change / h_change / l_change
        - Sign convention of fpvolume / covolume / ppvolume
        - Whether OutBlock1 ``date`` marks the bar start or end
        - Time ordering of OutBlock1 rows
    Descriptions must not assert these to avoid teaching the AI chatbot
    false certainty.
    """

    def test_o_sign_enum_not_declared_in_description(self):
        """o_sign enum mapping is NOT declared by LS. Description must not
        assert specific code-to-meaning mapping. Must mention 'not declared'.
        """
        desc = T1305OutBlock1.model_fields["o_sign"].description or ""
        assert "not declared" in desc.lower(), (
            "T1305OutBlock1.o_sign: description must state that enum mapping "
            "is 'not declared in available source' — LS does not publish "
            "the o_sign enum mapping for t1305."
        )

    def test_close_no_inferred_currency(self):
        desc = T1305OutBlock1.model_fields["close"].description or ""
        assert "in KRW" not in desc, (
            "T1305OutBlock1.close: must not infer KRW unit — LS spec does "
            "not declare currency unit explicitly."
        )
        assert " KRW" not in desc, (
            "T1305OutBlock1.close: must not add KRW annotation."
        )

    def test_open_no_inferred_currency(self):
        desc = T1305OutBlock1.model_fields["open"].description or ""
        assert "in KRW" not in desc and " KRW" not in desc, (
            "T1305OutBlock1.open: must not infer KRW unit."
        )

    def test_change_no_inferred_sign_convention(self):
        desc = T1305OutBlock1.model_fields["change"].description or ""
        for forbidden in [
            "positive when up", "negative when down",
            "always positive", "always non-negative",
        ]:
            assert forbidden not in desc, (
                f"T1305OutBlock1.change: must not assert sign convention "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_o_change_no_inferred_sign_convention(self):
        desc = T1305OutBlock1.model_fields["o_change"].description or ""
        for forbidden in [
            "positive when up", "negative when down",
            "always positive", "always non-negative",
        ]:
            assert forbidden not in desc, (
                f"T1305OutBlock1.o_change: must not assert sign convention "
                f"'{forbidden}'."
            )

    def test_h_change_no_inferred_sign_convention(self):
        desc = T1305OutBlock1.model_fields["h_change"].description or ""
        for forbidden in [
            "positive when up", "negative when down",
            "always positive", "always non-negative",
        ]:
            assert forbidden not in desc, (
                f"T1305OutBlock1.h_change: must not assert sign convention "
                f"'{forbidden}'."
            )

    def test_l_change_no_inferred_sign_convention(self):
        desc = T1305OutBlock1.model_fields["l_change"].description or ""
        for forbidden in [
            "positive when up", "negative when down",
            "always positive", "always non-negative",
        ]:
            assert forbidden not in desc, (
                f"T1305OutBlock1.l_change: must not assert sign convention "
                f"'{forbidden}'."
            )

    def test_fpvolume_no_inferred_sign_convention(self):
        desc = T1305OutBlock1.model_fields["fpvolume"].description or ""
        for forbidden in [
            "positive means net buy", "negative means net sell",
            "always positive", "양수=매수우위",
        ]:
            assert forbidden not in desc, (
                f"T1305OutBlock1.fpvolume: must not assert sign convention "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_covolume_no_inferred_sign_convention(self):
        desc = T1305OutBlock1.model_fields["covolume"].description or ""
        for forbidden in [
            "positive means net buy", "negative means net sell",
            "always positive", "양수=매수우위",
        ]:
            assert forbidden not in desc, (
                f"T1305OutBlock1.covolume: must not assert sign convention "
                f"'{forbidden}'."
            )

    def test_ppvolume_no_inferred_sign_convention(self):
        desc = T1305OutBlock1.model_fields["ppvolume"].description or ""
        for forbidden in [
            "positive means net buy", "negative means net sell",
            "always positive", "양수=매수우위",
        ]:
            assert forbidden not in desc, (
                f"T1305OutBlock1.ppvolume: must not assert sign convention "
                f"'{forbidden}'."
            )

    def test_date_carries_semantics_disclaimer(self):
        """LS does not declare whether OutBlock1 ``date`` marks the bar start
        or end. The description must keep an explicit disclaimer.
        """
        desc = T1305OutBlock1.model_fields["date"].description or ""
        assert "not formally declared" in desc, (
            "T1305OutBlock1.date: must keep the LS spec disclaimer "
            "for bar-date semantics (start vs end vs boundary)."
        )

    def test_block_date_ordering_not_asserted_in_response_description(self):
        """Time ordering of OutBlock1 rows is not declared. The T1305Response
        block field description must not assert ascending or descending order.
        """
        block_field = T1305Response.model_fields.get("block")
        desc = (block_field.description or "") if block_field else ""
        for forbidden in ["ascending", "descending", "oldest first", "newest first"]:
            assert forbidden not in desc.lower(), (
                f"T1305Response.block description must not assert row ordering "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_value_currency_only_ls_annotation(self):
        """value field must only carry the LS-label annotation '단위:백만',
        not any additional currency unit assertion like 'KRW' or '원'.
        """
        desc = T1305OutBlock1.model_fields["value"].description or ""
        assert "단위:백만" in desc, (
            "T1305OutBlock1.value: LS label '단위:백만' must be reproduced in "
            "description."
        )
        assert "in KRW" not in desc and " KRW" not in desc, (
            "T1305OutBlock1.value: must not add KRW annotation beyond LS label."
        )

    def test_marketcap_currency_only_ls_annotation(self):
        """marketcap field must only carry the LS-label annotation '단위:백만',
        not any additional currency unit assertion.
        """
        desc = T1305OutBlock1.model_fields["marketcap"].description or ""
        assert "단위:백만" in desc, (
            "T1305OutBlock1.marketcap: LS label '단위:백만' must be reproduced "
            "in description."
        )
        assert "in KRW" not in desc and " KRW" not in desc, (
            "T1305OutBlock1.marketcap: must not add KRW annotation beyond LS label."
        )
