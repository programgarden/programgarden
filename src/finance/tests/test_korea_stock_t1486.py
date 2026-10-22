"""Unit tests for t1486 시간별예상체결가 (Korea Stock Time-bucket Expected-conclusion Price TR).

Covers:
    - blocks.py — Pydantic input/output validation, including LS official
      example response round-trip.
    - TrT1486._build_response — happy / HTTP error / exception paths.
    - Market domain class — Korean alias bridge to TrT1486.
    - KoreaStock chained call — ``ks.시세().시간별예상체결가(...)`` Korean alias path.
    - occurs_req updater — verifies that ``cts_time`` cursor transfers from
      OutBlock back into InBlock for paged calls.
    - Field(examples=[...]) regression guards — examples present + types
      validate against declared annotations.
    - LS-declared enum mapping — ``sign`` description must embed the
      LS-published 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락 mapping.
    - Anti-inference guard — fields LS did NOT declare (currency unit,
      change sign convention, bucket-time semantics, expected-conclusion
      session window) must not embed inferred assertions.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.market import Market
from programgarden_finance.ls.korea_stock.market.t1486 import TrT1486
from programgarden_finance.ls.korea_stock.market.t1486.blocks import (
    T1486InBlock,
    T1486OutBlock,
    T1486OutBlock1,
    T1486Request,
    T1486Response,
    T1486ResponseHeader,
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


def _make_request(**overrides: Any) -> T1486Request:
    body = T1486InBlock(
        shcode=overrides.pop("shcode", "001200"),
        cts_time=overrides.pop("cts_time", ""),
        cnt=overrides.pop("cnt", 20),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1486Request(body={"t1486InBlock": body})


# LS official example response (user-supplied).
_LS_OFFICIAL_RESPONSE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "조회완료",
    "t1486OutBlock": {
        "cts_time": "08594423 0",
    },
    "t1486OutBlock1": [
        {
            "bidrem1": 8713,
            "price": 3660,
            "change": 0,
            "offerrem1": 956,
            "sign": "3",
            "diff": "0.00",
            "chetime": "09000854",
            "bidho1": 3660,
            "cvolume": 6062,
            "offerho1": 3665,
        },
        {
            "bidrem1": 1270,
            "price": 3680,
            "change": 20,
            "offerrem1": 191,
            "sign": "2",
            "diff": "0.55",
            "chetime": "08594423",
            "bidho1": 3665,
            "cvolume": 1552,
            "offerho1": 3680,
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


class TestT1486InBlock:
    def test_valid_minimal(self):
        block = T1486InBlock(shcode="001200", cnt=20, exchgubun="K")
        assert block.shcode == "001200"
        assert block.cts_time == ""
        assert block.cnt == 20
        assert block.exchgubun == "K"

    def test_valid_with_continuation_cursor(self):
        block = T1486InBlock(
            shcode="005930", cts_time="08594423", cnt=100, exchgubun="U"
        )
        assert block.cts_time == "08594423"
        assert block.cnt == 100
        assert block.exchgubun == "U"

    def test_invalid_exchgubun_rejected(self):
        with pytest.raises(ValidationError):
            T1486InBlock(shcode="005930", cnt=20, exchgubun="X")


class TestT1486OutBlock:
    def test_defaults(self):
        out = T1486OutBlock()
        assert out.cts_time == ""
        assert out.ex_shcode == ""

    def test_decodes_continuation_payload(self):
        out = T1486OutBlock.model_validate({"cts_time": "08594423 0"})
        assert out.cts_time == "08594423 0"

    def test_decodes_with_ex_shcode(self):
        out = T1486OutBlock.model_validate({"cts_time": "", "ex_shcode": "001200"})
        assert out.cts_time == ""
        assert out.ex_shcode == "001200"


class TestT1486OutBlock1:
    def test_decodes_ls_official_first_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1486OutBlock1"][0]
        out = T1486OutBlock1.model_validate(row)
        assert out.chetime == "09000854"
        assert out.price == 3660
        assert out.sign == "3"
        assert out.change == 0
        assert out.diff == pytest.approx(0.0)
        assert isinstance(out.diff, float)
        assert out.cvolume == 6062
        assert out.offerho1 == 3665
        assert out.bidho1 == 3660
        assert out.offerrem1 == 956
        assert out.bidrem1 == 8713

    def test_decodes_ls_official_second_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1486OutBlock1"][1]
        out = T1486OutBlock1.model_validate(row)
        assert out.chetime == "08594423"
        assert out.price == 3680
        assert out.sign == "2"
        assert out.change == 20
        assert out.diff == pytest.approx(0.55)
        assert isinstance(out.diff, float)
        assert out.cvolume == 1552

    def test_change_accepts_negative(self):
        out = T1486OutBlock1.model_validate({"change": -25})
        assert out.change == -25

    def test_diff_accepts_negative_string(self):
        out = T1486OutBlock1.model_validate({"diff": "-1.20"})
        assert out.diff == pytest.approx(-1.20)

    def test_defaults_when_missing(self):
        out = T1486OutBlock1()
        assert out.chetime == ""
        assert out.price == 0
        assert out.sign == ""
        assert out.change == 0
        assert out.diff == 0.0
        assert out.cvolume == 0
        assert out.exchname == ""


class TestT1486LSExampleResponseRoundTrip:
    """Regression guard — full LS official example response must round-trip
    through the entire response envelope without ValidationError.
    """

    def test_full_envelope_validates(self):
        rows = _LS_OFFICIAL_RESPONSE["t1486OutBlock1"]
        cont = _LS_OFFICIAL_RESPONSE["t1486OutBlock"]

        resp = T1486Response(
            header=None,
            cont_block=T1486OutBlock.model_validate(cont),
            block=[T1486OutBlock1.model_validate(r) for r in rows],
            rsp_cd=_LS_OFFICIAL_RESPONSE["rsp_cd"],
            rsp_msg=_LS_OFFICIAL_RESPONSE["rsp_msg"],
            status_code=200,
            error_msg=None,
        )

        assert resp.cont_block is not None
        assert resp.cont_block.cts_time == "08594423 0"
        assert len(resp.block) == 2
        assert resp.block[0].chetime == "09000854"
        assert resp.block[1].chetime == "08594423"
        assert resp.rsp_cd == "00000"


# ---------------------------------------------------------------------------
# 3. TrT1486._build_response
# ---------------------------------------------------------------------------


class TestTrT1486BuildResponse:
    def _make_tr(self) -> TrT1486:
        return TrT1486(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1486",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, _LS_OFFICIAL_RESPONSE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.cont_block is not None
        assert result.cont_block.cts_time == "08594423 0"
        assert len(result.block) == 2
        assert result.block[0].price == 3660
        assert result.block[1].price == 3680
        assert result.header is not None
        assert isinstance(result.header, T1486ResponseHeader)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1486"},
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
    def test_t1486_returns_tr_instance(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        body = T1486InBlock(shcode="001200", cnt=20, exchgubun="K")
        tr = market.t1486(body=body)
        assert isinstance(tr, TrT1486)
        assert tr.request_data.body["t1486InBlock"].shcode == "001200"
        assert tr.request_data.body["t1486InBlock"].cnt == 20

    def test_korean_alias_class_level(self):
        assert Market.t1486 is Market.시간별예상체결가

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
        body = T1486InBlock(shcode="005930", cts_time="", cnt=50, exchgubun="K")
        tr = ks.시세().시간별예상체결가(body=body)
        assert isinstance(tr, TrT1486)
        assert tr.request_data.body["t1486InBlock"].shcode == "005930"
        assert tr.request_data.body["t1486InBlock"].cnt == 50


# ---------------------------------------------------------------------------
# 6. occurs_req updater — cts_time propagation
# ---------------------------------------------------------------------------


class TestTrT1486OccursReqUpdater:
    """Verify that the occurs_req updater closure feeds ``cts_time`` from
    the previous response's cont_block back into the next request's
    ``T1486InBlock.cts_time``. Missing this would cause an infinite loop.
    """

    def test_updater_propagates_cts_time(self):
        tr = TrT1486(_make_request())

        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1486Response(
            header=T1486ResponseHeader(
                content_type="application/json",
                tr_cd="t1486",
                tr_cont="Y",
                tr_cont_key="next-key",
            ),
            cont_block=T1486OutBlock(cts_time="08594423 0"),
            block=[],
            rsp_cd="00000",
            rsp_msg="OK",
        )
        updater(tr.request_data, resp)

        assert tr.request_data.header.tr_cont_key == "next-key"
        assert tr.request_data.header.tr_cont == "Y"
        assert tr.request_data.body["t1486InBlock"].cts_time == "08594423 0"

    def test_updater_raises_on_missing_continuation(self):
        tr = TrT1486(_make_request())
        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1486Response(
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
        [T1486InBlock, T1486OutBlock, T1486OutBlock1],
        ids=["T1486InBlock", "T1486OutBlock", "T1486OutBlock1"],
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
        [T1486InBlock, T1486OutBlock1],
        ids=["T1486InBlock", "T1486OutBlock1"],
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
        assert set(T1486InBlock.model_fields) == {
            "shcode", "cts_time", "cnt", "exchgubun",
        }

    def test_outblock_fields(self):
        assert set(T1486OutBlock.model_fields) == {"cts_time", "ex_shcode"}

    def test_outblock1_fields(self):
        expected = {
            "chetime", "price", "sign", "change", "diff",
            "cvolume",
            "offerho1", "bidho1", "offerrem1", "bidrem1",
            "exchname",
        }
        assert set(T1486OutBlock1.model_fields) == expected


# ---------------------------------------------------------------------------
# 9. LS-declared enum mapping — sign field documents the published mapping
# ---------------------------------------------------------------------------


class TestSignEnumDocumented:
    """For t1486 LS publishes the ``sign`` enum mapping
    (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락). The description must embed
    the mapping so the AI chatbot can generate correct workflows.
    """

    def test_sign_enum_mapping_present(self):
        desc = T1486OutBlock1.model_fields["sign"].description or ""
        for token in [
            "'1'", "'2'", "'3'", "'4'", "'5'",
            "upper limit", "up", "unchanged", "lower limit", "down",
            "상한", "상승", "보합", "하한", "하락",
        ]:
            assert token in desc, (
                f"T1486OutBlock1.sign description missing LS-declared token "
                f"'{token}'. LS publishes the full 1~5 enum mapping for t1486; "
                f"description must mirror it for AI chatbot accuracy."
            )


# ---------------------------------------------------------------------------
# 10. Anti-inference guard — fields LS did NOT declare
# ---------------------------------------------------------------------------


class TestNoInferredUnitOrSemantics:
    """For t1486 LS does NOT declare:
        - Currency unit of price/offerho1/bidho1/change
        - Sign convention of change
        - Whether ``chetime`` marks bucket start or end
        - The exact session window the expected-conclusion stream covers
          (pre-open / closing auction / both)
    Descriptions must not assert these to avoid teaching the AI chatbot
    false certainty.
    """

    def test_price_no_inferred_currency(self):
        desc = T1486OutBlock1.model_fields["price"].description or ""
        assert "in KRW" not in desc, (
            "T1486OutBlock1.price: must not infer KRW unit — LS spec does "
            "not declare currency unit explicitly."
        )

    def test_change_no_inferred_sign_convention(self):
        desc = T1486OutBlock1.model_fields["change"].description or ""
        for forbidden in [
            "positive when up", "negative when down",
            "always positive", "always non-negative",
        ]:
            assert forbidden not in desc, (
                f"T1486OutBlock1.change: must not assert sign convention "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_chetime_carries_bucket_semantics_disclaimer(self):
        """LS does not declare whether ``chetime`` marks the bucket start
        or end. The description must keep an explicit ``not declared``
        disclaimer so future readers (and the AI chatbot) do not assume
        either interpretation.
        """
        desc = T1486OutBlock1.model_fields["chetime"].description or ""
        assert "not formally declared" in desc, (
            "T1486OutBlock1.chetime: must keep the LS spec disclaimer "
            "for bucket-time semantics (start vs end)."
        )

    def test_module_session_window_disclaimer(self):
        """t1486 covers an expected-conclusion (auction) stream, but LS does
        not declare which session window (pre-open / closing auction / both)
        it returns. The blocks.py module docstring must keep that disclaimer
        so the AI chatbot does not fabricate a session-window assertion.
        """
        from programgarden_finance.ls.korea_stock.market.t1486 import blocks
        doc = (blocks.__doc__ or "").lower()
        for token in ["session window", "not declared"]:
            assert token in doc, (
                f"blocks.py module docstring must mention '{token}' to keep "
                "the LS no-declaration disclaimer for the expected-conclusion "
                "session window."
            )
