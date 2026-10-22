"""Unit tests for t1488 예상체결가등락율상위조회 (Korea Stock Top Expected-conclusion Percent-change TR).

Covers:
    - blocks.py — Pydantic input/output validation, including LS official
      example response round-trip.
    - TrT1488._build_response — happy / HTTP error / exception paths.
    - Market domain class — Korean alias bridge to TrT1488.
    - KoreaStock chained call — ``ks.시세().예상체결가등락율상위조회(...)`` Korean alias path.
    - occurs_req updater — verifies that ``idx`` cursor transfers from
      OutBlock back into InBlock for paged calls.
    - Field(examples=[...]) regression guards — examples present + types
      validate against declared annotations.
    - LS-declared bit map — ``jongchk`` description must embed the
      LS-published exclusion-bit constants.
    - Anti-inference guard — fields LS did NOT declare (output ``sign``
      enum, currency unit, change sign convention, ``cnt`` counting
      window, row ordering) must not embed inferred assertions.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.market import Market
from programgarden_finance.ls.korea_stock.market.t1488 import TrT1488
from programgarden_finance.ls.korea_stock.market.t1488.blocks import (
    T1488InBlock,
    T1488OutBlock,
    T1488OutBlock1,
    T1488Request,
    T1488Response,
    T1488ResponseHeader,
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


def _make_request(**overrides: Any) -> T1488Request:
    body = T1488InBlock(
        gubun=overrides.pop("gubun", "0"),
        sign=overrides.pop("sign", "1"),
        jgubun=overrides.pop("jgubun", "1"),
        jongchk=overrides.pop("jongchk", "0x00000080"),
        idx=overrides.pop("idx", 0),
        volume=overrides.pop("volume", "0"),
        yesprice=overrides.pop("yesprice", 0),
        yeeprice=overrides.pop("yeeprice", 0),
        yevolume=overrides.pop("yevolume", 0),
    )
    return T1488Request(body={"t1488InBlock": body})


# LS official example response (user-supplied).
_LS_OFFICIAL_RESPONSE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1488OutBlock": {"idx": 20},
    "t1488OutBlock1": [
        {
            "change": 1320,
            "shcode": "203690",
            "sign": "2",
            "cnt": 1,
            "diff": "029.01",
            "offerho": 5870,
            "bidrem": 19,
            "offerrem": 504,
            "volume": 48087,
            "bidho": 5860,
            "price": 5870,
            "jnilvolume": 390674,
            "jkrate": "100",
            "hname": "프로스테믹스",
        },
        {
            "change": 144,
            "shcode": "007460",
            "sign": "2",
            "cnt": 1,
            "diff": "009.66",
            "offerho": 1636,
            "bidrem": 2924,
            "offerrem": 3009,
            "volume": 142226,
            "bidho": 1635,
            "price": 1635,
            "jnilvolume": 6923364,
            "jkrate": "100",
            "hname": "에이프로젠",
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


class TestT1488InBlock:
    def test_valid_minimal(self):
        block = T1488InBlock(
            gubun="0", sign="1", jgubun="1", jongchk="0x00000080",
            volume="0",
        )
        assert block.gubun == "0"
        assert block.sign == "1"
        assert block.jgubun == "1"
        assert block.jongchk == "0x00000080"
        assert block.idx == 0
        assert block.volume == "0"
        assert block.yesprice == 0
        assert block.yeeprice == 0
        assert block.yevolume == 0

    def test_valid_with_filters(self):
        block = T1488InBlock(
            gubun="1", sign="2", jgubun="3", jongchk="0",
            idx=20, volume="3",
            yesprice=1000, yeeprice=100000, yevolume=10000,
        )
        assert block.gubun == "1"
        assert block.sign == "2"
        assert block.jgubun == "3"
        assert block.idx == 20
        assert block.volume == "3"
        assert block.yesprice == 1000
        assert block.yeeprice == 100000
        assert block.yevolume == 10000

    def test_invalid_gubun_rejected(self):
        with pytest.raises(ValidationError):
            T1488InBlock(
                gubun="9", sign="1", jgubun="1", jongchk="0", volume="0",
            )

    def test_invalid_sign_rejected(self):
        with pytest.raises(ValidationError):
            T1488InBlock(
                gubun="0", sign="3", jgubun="1", jongchk="0", volume="0",
            )

    def test_invalid_jgubun_rejected(self):
        with pytest.raises(ValidationError):
            T1488InBlock(
                gubun="0", sign="1", jgubun="4", jongchk="0", volume="0",
            )

    def test_invalid_volume_rejected(self):
        with pytest.raises(ValidationError):
            T1488InBlock(
                gubun="0", sign="1", jgubun="1", jongchk="0", volume="6",
            )


class TestT1488OutBlock:
    def test_decodes_idx(self):
        out = T1488OutBlock.model_validate({"idx": 20})
        assert out.idx == 20

    def test_zero_idx_terminates_pagination(self):
        out = T1488OutBlock.model_validate({"idx": 0})
        assert out.idx == 0

    def test_idx_required(self):
        with pytest.raises(ValidationError):
            T1488OutBlock.model_validate({})


class TestT1488OutBlock1:
    def test_decodes_ls_official_first_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1488OutBlock1"][0]
        out = T1488OutBlock1.model_validate(row)
        assert out.hname == "프로스테믹스"
        assert out.shcode == "203690"
        assert out.price == 5870
        assert out.sign == "2"
        assert out.change == 1320
        assert out.diff == pytest.approx(29.01)
        assert isinstance(out.diff, float)
        assert out.volume == 48087
        assert out.offerrem == 504
        assert out.offerho == 5870
        assert out.bidho == 5860
        assert out.bidrem == 19
        assert out.cnt == 1
        assert out.jkrate == "100"
        assert out.jnilvolume == 390674

    def test_decodes_ls_official_second_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1488OutBlock1"][1]
        out = T1488OutBlock1.model_validate(row)
        assert out.hname == "에이프로젠"
        assert out.shcode == "007460"
        assert out.price == 1635
        assert out.sign == "2"
        assert out.change == 144
        assert out.diff == pytest.approx(9.66)
        assert isinstance(out.diff, float)
        assert out.volume == 142226

    def test_change_accepts_negative(self):
        out = T1488OutBlock1.model_validate({"change": -25})
        assert out.change == -25

    def test_diff_accepts_negative_string(self):
        out = T1488OutBlock1.model_validate({"diff": "-1.20"})
        assert out.diff == pytest.approx(-1.20)

    def test_defaults_when_missing(self):
        out = T1488OutBlock1()
        assert out.hname == ""
        assert out.shcode == ""
        assert out.price == 0
        assert out.sign == ""
        assert out.change == 0
        assert out.diff == 0.0
        assert out.volume == 0
        assert out.offerrem == 0
        assert out.offerho == 0
        assert out.bidho == 0
        assert out.bidrem == 0
        assert out.cnt == 0
        assert out.jkrate == ""
        assert out.jnilvolume == 0


class TestT1488LSExampleResponseRoundTrip:
    """Regression guard — full LS official example response must round-trip
    through the entire response envelope without ValidationError.
    """

    def test_full_envelope_validates(self):
        rows = _LS_OFFICIAL_RESPONSE["t1488OutBlock1"]
        cont = _LS_OFFICIAL_RESPONSE["t1488OutBlock"]

        resp = T1488Response(
            header=None,
            cont_block=T1488OutBlock.model_validate(cont),
            block=[T1488OutBlock1.model_validate(r) for r in rows],
            rsp_cd=_LS_OFFICIAL_RESPONSE["rsp_cd"],
            rsp_msg=_LS_OFFICIAL_RESPONSE["rsp_msg"],
            status_code=200,
            error_msg=None,
        )

        assert resp.cont_block is not None
        assert resp.cont_block.idx == 20
        assert len(resp.block) == 2
        assert resp.block[0].shcode == "203690"
        assert resp.block[1].shcode == "007460"
        assert resp.rsp_cd == "00000"


# ---------------------------------------------------------------------------
# 3. TrT1488._build_response
# ---------------------------------------------------------------------------


class TestTrT1488BuildResponse:
    def _make_tr(self) -> TrT1488:
        return TrT1488(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1488",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, _LS_OFFICIAL_RESPONSE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.cont_block is not None
        assert result.cont_block.idx == 20
        assert len(result.block) == 2
        assert result.block[0].shcode == "203690"
        assert result.block[1].shcode == "007460"
        assert result.header is not None
        assert isinstance(result.header, T1488ResponseHeader)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1488"},
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
    def test_t1488_returns_tr_instance(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        body = T1488InBlock(
            gubun="0", sign="1", jgubun="1", jongchk="0x00000080",
            volume="0",
        )
        tr = market.t1488(body=body)
        assert isinstance(tr, TrT1488)
        assert tr.request_data.body["t1488InBlock"].gubun == "0"
        assert tr.request_data.body["t1488InBlock"].sign == "1"

    def test_korean_alias_class_level(self):
        assert Market.t1488 is Market.예상체결가등락율상위조회

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
        body = T1488InBlock(
            gubun="1", sign="2", jgubun="3", jongchk="0",
            volume="2",
        )
        tr = ks.시세().예상체결가등락율상위조회(body=body)
        assert isinstance(tr, TrT1488)
        assert tr.request_data.body["t1488InBlock"].gubun == "1"
        assert tr.request_data.body["t1488InBlock"].sign == "2"
        assert tr.request_data.body["t1488InBlock"].volume == "2"


# ---------------------------------------------------------------------------
# 6. occurs_req updater — idx propagation
# ---------------------------------------------------------------------------


class TestTrT1488OccursReqUpdater:
    """Verify that the occurs_req updater closure feeds ``idx`` from the
    previous response's cont_block back into the next request's
    ``T1488InBlock.idx``. Missing this would cause an infinite loop.
    """

    def test_updater_propagates_idx(self):
        tr = TrT1488(_make_request())

        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1488Response(
            header=T1488ResponseHeader(
                content_type="application/json",
                tr_cd="t1488",
                tr_cont="Y",
                tr_cont_key="next-key",
            ),
            cont_block=T1488OutBlock(idx=20),
            block=[],
            rsp_cd="00000",
            rsp_msg="OK",
        )
        updater(tr.request_data, resp)

        assert tr.request_data.header.tr_cont_key == "next-key"
        assert tr.request_data.header.tr_cont == "Y"
        assert tr.request_data.body["t1488InBlock"].idx == 20

    def test_updater_raises_on_missing_continuation(self):
        tr = TrT1488(_make_request())
        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1488Response(
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
        [T1488InBlock, T1488OutBlock, T1488OutBlock1],
        ids=["T1488InBlock", "T1488OutBlock", "T1488OutBlock1"],
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
        [T1488InBlock, T1488OutBlock1],
        ids=["T1488InBlock", "T1488OutBlock1"],
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
        assert set(T1488InBlock.model_fields) == {
            "gubun", "sign", "jgubun", "jongchk", "idx",
            "volume", "yesprice", "yeeprice", "yevolume",
        }

    def test_outblock_fields(self):
        assert set(T1488OutBlock.model_fields) == {"idx"}

    def test_outblock1_fields(self):
        expected = {
            "hname", "price", "sign", "change", "diff", "volume",
            "offerrem", "offerho", "bidho", "bidrem",
            "cnt", "shcode", "jkrate", "jnilvolume",
        }
        assert set(T1488OutBlock1.model_fields) == expected


# ---------------------------------------------------------------------------
# 9. LS-declared bitmap — jongchk description documents the published bits
# ---------------------------------------------------------------------------


class TestJongchkBitMapDocumented:
    """For t1488 LS publishes the ``jongchk`` exclusion bitmap
    (0x00000080 관리종목, 0x00000100 시장경보, etc.). The description must
    embed the bit constants so the AI chatbot can generate correct filters.
    """

    def test_jongchk_bits_present(self):
        desc = T1488InBlock.model_fields["jongchk"].description or ""
        for token in [
            "0x00000080", "관리종목",
            "0x00000100", "시장경보",
            "0x00000200", "거래정지",
            "0x00004000", "우선주",
            "0x01000000", "정리매매",
            "0x80000000", "불성실공시",
        ]:
            assert token in desc, (
                f"T1488InBlock.jongchk description missing LS-declared token "
                f"'{token}'. LS publishes the exclusion bitmap; description "
                f"must mirror it for AI chatbot accuracy."
            )


# ---------------------------------------------------------------------------
# 10. Anti-inference guard — fields LS did NOT declare
# ---------------------------------------------------------------------------


class TestNoInferredUnitOrSemantics:
    """For t1488 LS does NOT declare:
        - Output ``sign`` enum mapping (only input sign 1=상승/2=하락 is declared)
        - Currency unit of price / offerho / bidho / change
        - Sign convention of change
        - ``cnt`` (연속일수) counting window
        - Row ordering within OutBlock1
    Descriptions must not assert these to avoid teaching the AI chatbot
    false certainty.
    """

    def test_output_sign_no_inferred_enum_mapping(self):
        desc = T1488OutBlock1.model_fields["sign"].description or ""
        # The output sign enum is NOT declared by LS for t1488 — must keep
        # the explicit disclaimer.
        assert "NOT declared" in desc or "not declared" in desc, (
            "T1488OutBlock1.sign: must keep the LS-no-declaration "
            "disclaimer; the t1488 output sign enum mapping is not "
            "published in available source."
        )
        # Must NOT bake in the 1~5 mapping from other LS TRs as truth.
        forbidden_assertions = [
            "'1' = upper limit", "'2' = up", "'3' = unchanged",
            "'4' = lower limit", "'5' = down",
        ]
        for forbidden in forbidden_assertions:
            assert forbidden not in desc, (
                f"T1488OutBlock1.sign: must not assert '{forbidden}' as "
                f"truth — LS does not declare the output sign enum for t1488."
            )

    def test_price_no_inferred_currency(self):
        desc = T1488OutBlock1.model_fields["price"].description or ""
        assert "in KRW" not in desc, (
            "T1488OutBlock1.price: must not infer KRW unit — LS spec does "
            "not declare currency unit explicitly."
        )

    def test_change_no_inferred_sign_convention(self):
        desc = T1488OutBlock1.model_fields["change"].description or ""
        for forbidden in [
            "positive when up", "negative when down",
            "always positive", "always non-negative",
        ]:
            assert forbidden not in desc, (
                f"T1488OutBlock1.change: must not assert sign convention "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_cnt_no_inferred_counting_window(self):
        desc = T1488OutBlock1.model_fields["cnt"].description or ""
        assert "not declared" in desc, (
            "T1488OutBlock1.cnt: must keep the LS-no-declaration disclaimer "
            "for the consecutive-day counting window."
        )

    def test_module_row_ordering_disclaimer(self):
        """LS does not declare row ordering within ``t1488OutBlock1``. The
        blocks.py module docstring must keep that disclaimer so the AI
        chatbot does not fabricate an ordering assumption (e.g., descending
        by percent change).
        """
        from programgarden_finance.ls.korea_stock.market.t1488 import blocks
        doc = (blocks.__doc__ or "").lower()
        for token in ["row ordering", "not declared"]:
            assert token in doc, (
                f"blocks.py module docstring must mention '{token}' to keep "
                "the LS no-declaration disclaimer for row ordering within "
                "OutBlock1."
            )
