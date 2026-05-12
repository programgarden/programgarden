"""Unit tests for t1308 주식시간대별체결조회챠트 (Korea Stock Time-Bucket Trade Chart TR).

Covers:
    - blocks.py — Pydantic input/output validation, including LS official
      example response round-trip.
    - TrT1308._build_response — happy / HTTP error / exception paths.
    - Market domain class — Korean alias bridge to TrT1308.
    - KoreaStock chained call — ``ks.시세().주식시간대별체결조회챠트(...)``
      Korean alias path.
    - Single-shot guard — TrT1308 must not expose ``occurs_req`` (no
      LS-declared continuation cursor for t1308).
    - Field(examples=[...]) regression guards — examples present + types
      validate against declared annotations.
    - LS-declared enum mappings — both ``T1308InBlock.exchgubun`` and
      ``T1308OutBlock1.sign`` descriptions must embed the LS-published
      mappings (K/N/U + 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락).
    - Anti-inference guard — fields LS did NOT declare (currency unit,
      change sign convention, OHLC bucket scope, volume↔cvolume
      cumulative-vs-per-bucket relationship, chetime exact format,
      ex_shcode structure, row ordering) must not embed inferred
      assertions.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.market import Market
from programgarden_finance.ls.korea_stock.market.t1308 import TrT1308
from programgarden_finance.ls.korea_stock.market.t1308.blocks import (
    T1308InBlock,
    T1308OutBlock,
    T1308OutBlock1,
    T1308Request,
    T1308Response,
    T1308ResponseHeader,
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


def _make_request(**overrides: Any) -> T1308Request:
    body = T1308InBlock(
        shcode=overrides.pop("shcode", "001200"),
        starttime=overrides.pop("starttime", ""),
        endtime=overrides.pop("endtime", ""),
        bun_term=overrides.pop("bun_term", ""),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1308Request(body={"t1308InBlock": body})


# LS official example response (user-supplied).
_LS_OFFICIAL_RESPONSE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1308OutBlock1": [
        {
            "change": 25,
            "mdchecnt": 256,
            "sign": "2",
            "chdegcnt": "92.97",
            "diff": "0.69",
            "mschecnt": 238,
            "chetime": "102700",
            "mdvolume": 119531,
            "cvolume": 0,
            "volume": 321201,
            "chdegvol": "163.65",
            "high": 3685,
            "low": 3685,
            "price": 3685,
            "msvolume": 195607,
            "open": 3685,
        },
        {
            "change": 0,
            "mdchecnt": 14,
            "sign": "3",
            "chdegcnt": "14.29",
            "diff": "0.01",
            "mschecnt": 2,
            "chetime": "090030",
            "mdvolume": 12895,
            "cvolume": 19856,
            "volume": 19857,
            "chdegvol": "6.97",
            "high": 3660,
            "low": 3660,
            "price": 3660,
            "msvolume": 899,
            "open": 3660,
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


class TestT1308InBlock:
    def test_valid_minimum(self):
        block = T1308InBlock(shcode="005930")
        assert block.shcode == "005930"
        assert block.starttime == ""
        assert block.endtime == ""
        assert block.bun_term == ""
        assert block.exchgubun == "K"

    def test_valid_full(self):
        block = T1308InBlock(
            shcode="001200",
            starttime="0900",
            endtime="1500",
            bun_term="05",
            exchgubun="N",
        )
        assert block.starttime == "0900"
        assert block.endtime == "1500"
        assert block.bun_term == "05"
        assert block.exchgubun == "N"

    def test_default_exchgubun_is_krx(self):
        block = T1308InBlock(shcode="005930")
        assert block.exchgubun == "K"

    def test_invalid_exchgubun_rejected(self):
        with pytest.raises(ValidationError):
            T1308InBlock(shcode="005930", exchgubun="X")

    def test_shcode_required(self):
        with pytest.raises(ValidationError):
            T1308InBlock()


class TestT1308OutBlock:
    def test_default_empty_ex_shcode(self):
        out = T1308OutBlock()
        assert out.ex_shcode == ""

    def test_accepts_arbitrary_string(self):
        out = T1308OutBlock.model_validate({"ex_shcode": "KR7001200004"})
        assert out.ex_shcode == "KR7001200004"


class TestT1308OutBlock1:
    def test_decodes_ls_official_first_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1308OutBlock1"][0]
        out = T1308OutBlock1.model_validate(row)
        assert out.chetime == "102700"
        assert out.price == 3685
        assert out.sign == "2"
        assert out.change == 25
        assert out.diff == pytest.approx(0.69)
        assert isinstance(out.diff, float)
        assert out.cvolume == 0
        assert out.chdegvol == pytest.approx(163.65)
        assert isinstance(out.chdegvol, float)
        assert out.chdegcnt == pytest.approx(92.97)
        assert isinstance(out.chdegcnt, float)
        assert out.volume == 321201
        assert out.mdvolume == 119531
        assert out.mdchecnt == 256
        assert out.msvolume == 195607
        assert out.mschecnt == 238
        assert out.open == 3685
        assert out.high == 3685
        assert out.low == 3685

    def test_decodes_ls_official_second_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1308OutBlock1"][1]
        out = T1308OutBlock1.model_validate(row)
        assert out.chetime == "090030"
        assert out.price == 3660
        assert out.sign == "3"
        assert out.change == 0
        assert out.diff == pytest.approx(0.01)
        assert out.cvolume == 19856
        assert out.chdegvol == pytest.approx(6.97)
        assert out.chdegcnt == pytest.approx(14.29)
        assert out.volume == 19857
        assert out.mdvolume == 12895
        assert out.mdchecnt == 14
        assert out.msvolume == 899
        assert out.mschecnt == 2
        assert out.open == 3660
        assert out.high == 3660
        assert out.low == 3660

    def test_change_accepts_negative(self):
        out = T1308OutBlock1.model_validate({"change": -25})
        assert out.change == -25

    def test_diff_accepts_negative_string(self):
        out = T1308OutBlock1.model_validate({"diff": "-1.20"})
        assert out.diff == pytest.approx(-1.20)

    def test_defaults_when_missing(self):
        out = T1308OutBlock1()
        assert out.chetime == ""
        assert out.price == 0
        assert out.sign == ""
        assert out.change == 0
        assert out.diff == 0.0
        assert out.cvolume == 0
        assert out.chdegvol == 0.0
        assert out.chdegcnt == 0.0
        assert out.volume == 0
        assert out.mdvolume == 0
        assert out.mdchecnt == 0
        assert out.msvolume == 0
        assert out.mschecnt == 0
        assert out.open == 0
        assert out.high == 0
        assert out.low == 0


class TestT1308LSExampleResponseRoundTrip:
    """Regression guard — full LS official example response must round-trip
    through the entire response envelope without ValidationError.
    """

    def test_full_envelope_validates(self):
        rows = _LS_OFFICIAL_RESPONSE["t1308OutBlock1"]

        resp = T1308Response(
            header=None,
            out_block=None,
            block=[T1308OutBlock1.model_validate(r) for r in rows],
            rsp_cd=_LS_OFFICIAL_RESPONSE["rsp_cd"],
            rsp_msg=_LS_OFFICIAL_RESPONSE["rsp_msg"],
            status_code=200,
            error_msg=None,
        )

        assert len(resp.block) == 2
        assert resp.block[0].chetime == "102700"
        assert resp.block[1].chetime == "090030"
        assert resp.rsp_cd == "00000"


# ---------------------------------------------------------------------------
# 3. TrT1308._build_response
# ---------------------------------------------------------------------------


class TestTrT1308BuildResponse:
    def _make_tr(self) -> TrT1308:
        return TrT1308(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1308",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, _LS_OFFICIAL_RESPONSE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        # LS official example response has no t1308OutBlock — out_block stays None
        assert result.out_block is None
        assert len(result.block) == 2
        assert result.block[0].chetime == "102700"
        assert result.block[1].chetime == "090030"
        assert result.header is not None
        assert isinstance(result.header, T1308ResponseHeader)

    def test_happy_path_with_outblock(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        payload = dict(_LS_OFFICIAL_RESPONSE)
        payload["t1308OutBlock"] = {"ex_shcode": "KR7001200004"}
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1308",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, payload, resp_headers, None)

        assert result.error_msg is None
        assert result.out_block is not None
        assert result.out_block.ex_shcode == "KR7001200004"
        assert len(result.block) == 2

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1308"},
            None,
        )
        assert result.status_code == 500
        assert result.error_msg is not None
        assert "500" in result.error_msg
        assert "Internal error" in result.error_msg
        assert result.header is None
        assert result.out_block is None
        assert result.block == []

    def test_exception_path(self):
        tr = self._make_tr()
        result = tr._build_response(None, None, None, RuntimeError("boom"))
        assert result.error_msg == "boom"
        assert result.status_code is None
        assert result.out_block is None
        assert result.block == []

    def test_url_targets_market_endpoint(self):
        tr = self._make_tr()
        assert tr._generic._url == URLS.KOREA_STOCK_MARKET_URL


# ---------------------------------------------------------------------------
# 4. Market domain class
# ---------------------------------------------------------------------------


class TestMarketDomain:
    def test_t1308_returns_tr_instance(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        body = T1308InBlock(shcode="001200")
        tr = market.t1308(body=body)
        assert isinstance(tr, TrT1308)
        assert tr.request_data.body["t1308InBlock"].shcode == "001200"
        assert tr.request_data.body["t1308InBlock"].exchgubun == "K"

    def test_korean_alias_class_level(self):
        assert Market.t1308 is Market.주식시간대별체결조회챠트

    def test_korean_alias_doc(self):
        assert Market.주식시간대별체결조회챠트.__doc__


# ---------------------------------------------------------------------------
# 5. KoreaStock entry point
# ---------------------------------------------------------------------------


class TestKoreaStockMarketEntry:
    def test_chained_call_korean_alias(self):
        tm = _make_token_manager()
        ks = KoreaStock(tm)
        body = T1308InBlock(shcode="005930", bun_term="05")
        tr = ks.시세().주식시간대별체결조회챠트(body=body)
        assert isinstance(tr, TrT1308)
        assert tr.request_data.body["t1308InBlock"].shcode == "005930"
        assert tr.request_data.body["t1308InBlock"].bun_term == "05"


# ---------------------------------------------------------------------------
# 6. Single-shot guard — t1308 has no continuation cursor
# ---------------------------------------------------------------------------


class TestNoContinuationCursor:
    """LS spec available to this codebase exposes no continuation cursor
    (``cts_*`` / ``idx``) for t1308. TrT1308 must therefore NOT advertise
    ``occurs_req`` / ``occurs_req_async`` — adding them silently would
    cause callers to depend on a paged contract that LS does not honor.
    """

    def test_occurs_req_not_implemented(self):
        tr = TrT1308(_make_request())
        assert not hasattr(tr, "occurs_req"), (
            "TrT1308 must not expose occurs_req — LS spec for t1308 has "
            "no continuation cursor."
        )
        assert not hasattr(tr, "occurs_req_async"), (
            "TrT1308 must not expose occurs_req_async — LS spec for "
            "t1308 has no continuation cursor."
        )


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
        [T1308InBlock, T1308OutBlock, T1308OutBlock1],
        ids=["T1308InBlock", "T1308OutBlock", "T1308OutBlock1"],
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
        [T1308InBlock, T1308OutBlock, T1308OutBlock1],
        ids=["T1308InBlock", "T1308OutBlock", "T1308OutBlock1"],
    )
    def test_every_field_has_examples(self, model_cls: Type[BaseModel]):
        missing = [
            name
            for name, info in model_cls.model_fields.items()
            if not (info.examples or [])
        ]
        assert not missing, (
            f"{model_cls.__name__} fields without examples=[...]: {missing}. "
            "All InBlock / OutBlock / OutBlock1 fields must carry "
            "AI-readable examples."
        )


# ---------------------------------------------------------------------------
# 8. Model fields coverage — guard against silent LS spec drift
# ---------------------------------------------------------------------------


class TestModelFieldsCoverage:
    """If LS adds or removes fields silently, this guard fires immediately."""

    def test_inblock_fields(self):
        assert set(T1308InBlock.model_fields) == {
            "shcode", "starttime", "endtime", "bun_term", "exchgubun"
        }

    def test_outblock_fields(self):
        assert set(T1308OutBlock.model_fields) == {"ex_shcode"}

    def test_outblock1_fields(self):
        expected = {
            "chetime", "price", "sign", "change", "diff",
            "cvolume", "chdegvol", "chdegcnt",
            "volume", "mdvolume", "mdchecnt", "msvolume", "mschecnt",
            "open", "high", "low",
        }
        assert set(T1308OutBlock1.model_fields) == expected


# ---------------------------------------------------------------------------
# 9. LS-declared enum mappings — sign + exchgubun document the published mappings
# ---------------------------------------------------------------------------


class TestSignEnumDocumented:
    """LS publishes the ``sign`` enum mapping for t1308
    (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락) per xingAPI reference.
    The OutBlock1 description must embed the full mapping so the AI
    chatbot can generate correct workflows.
    """

    def test_sign_enum_mapping_present(self):
        desc = T1308OutBlock1.model_fields["sign"].description or ""
        for token in [
            "'1'", "'2'", "'3'", "'4'", "'5'",
            "upper limit", "up", "unchanged", "lower limit", "down",
            "상한", "상승", "보합", "하한", "하락",
        ]:
            assert token in desc, (
                f"T1308OutBlock1.sign description missing LS-declared "
                f"token '{token}'. LS publishes the full 1~5 enum mapping "
                f"for t1308; description must mirror it for AI chatbot "
                f"accuracy."
            )


class TestExchgubunEnumDocumented:
    """LS publishes the ``exchgubun`` enum mapping (K=KRX / N=NXT / U=통합)
    and the fallback behavior ("any other input treated as KRX"). The
    InBlock description must embed the mapping so the AI chatbot picks
    the right exchange.
    """

    def test_exchgubun_enum_mapping_present(self):
        desc = T1308InBlock.model_fields["exchgubun"].description or ""
        for token in [
            "'K'", "'N'", "'U'",
            "KRX", "NXT", "unified",
            "통합",
        ]:
            assert token in desc, (
                f"T1308InBlock.exchgubun description missing LS-declared "
                f"token '{token}'."
            )


# ---------------------------------------------------------------------------
# 10. Anti-inference guard — fields LS did NOT declare
# ---------------------------------------------------------------------------


class TestNoInferredUnitOrSemantics:
    """For t1308 LS does NOT declare:
        - Currency unit of price / open / high / low / change fields.
        - Sign convention of ``change`` (positive when up vs always
          non-negative magnitude).
        - Exact format of ``chetime`` (HHMMSS vs HHMM00 vs other).
        - Cumulative-vs-per-bucket relationship of ``volume`` /
          ``mdvolume`` / ``msvolume`` / ``mdchecnt`` / ``mschecnt``
          relative to ``cvolume``.
        - Bucket scope of OHLC (per row time bucket vs daily aggregate).
        - Row ordering of T1308OutBlock1.
        - Token structure of ``ex_shcode``.
    Descriptions must not assert these to avoid teaching the AI chatbot
    false certainty.
    """

    @pytest.mark.parametrize("field_name", ["price", "open", "high", "low"])
    def test_outblock1_price_fields_no_inferred_currency(self, field_name: str):
        desc = T1308OutBlock1.model_fields[field_name].description or ""
        assert "KRW" not in desc, (
            f"T1308OutBlock1.{field_name}: must not infer KRW unit — LS "
            "spec does not declare currency unit explicitly."
        )

    def test_change_no_inferred_sign_convention(self):
        desc = T1308OutBlock1.model_fields["change"].description or ""
        for forbidden in [
            "positive when up", "negative when down",
            "always positive", "always non-negative",
        ]:
            assert forbidden not in desc, (
                f"T1308OutBlock1.change: must not assert sign convention "
                f"'{forbidden}' — LS spec does not declare it."
            )
        assert "not declared" in desc, (
            "T1308OutBlock1.change: must keep the LS spec sign-convention "
            "disclaimer."
        )

    def test_chetime_format_disclaimer(self):
        desc = T1308OutBlock1.model_fields["chetime"].description or ""
        assert "not formally declared" in desc, (
            "T1308OutBlock1.chetime: must keep the LS spec disclaimer "
            "for exact format (HHMMSS vs other)."
        )

    @pytest.mark.parametrize(
        "field_name",
        ["volume", "mdvolume", "msvolume", "mdchecnt", "mschecnt"],
    )
    def test_cumulative_relationship_disclaimer(self, field_name: str):
        desc = T1308OutBlock1.model_fields[field_name].description or ""
        assert "not declared" in desc, (
            f"T1308OutBlock1.{field_name}: must keep the LS spec "
            f"disclaimer for cumulative-vs-per-bucket semantics."
        )

    @pytest.mark.parametrize("field_name", ["open", "high", "low"])
    def test_ohlc_bucket_scope_disclaimer(self, field_name: str):
        desc = T1308OutBlock1.model_fields[field_name].description or ""
        assert "Bucket scope" in desc and "not declared" in desc, (
            f"T1308OutBlock1.{field_name}: must keep the LS spec "
            f"disclaimer for bucket scope (per row vs daily)."
        )

    def test_ex_shcode_structure_disclaimer(self):
        desc = T1308OutBlock.model_fields["ex_shcode"].description or ""
        assert "not declared" in desc, (
            "T1308OutBlock.ex_shcode: must keep the LS spec disclaimer "
            "for token structure."
        )

    def test_module_row_ordering_disclaimer(self):
        """LS does not declare row ordering for T1308OutBlock1. The
        blocks.py module docstring AND the Response.block field
        description must mention the disclaimer so the AI chatbot does
        not fabricate an ordering assertion.
        """
        from programgarden_finance.ls.korea_stock.market.t1308 import blocks
        doc = (blocks.__doc__ or "").lower()
        assert "row time ordering" in doc and "not declared" in doc, (
            "blocks.py module docstring must mention row time ordering "
            "disclaimer."
        )

    def test_response_block_description_row_ordering_disclaimer(self):
        """T1308Response.block description must also carry the row-
        ordering disclaimer so consumers reading the Response model
        directly (not the module docstring) see it.
        """
        desc = T1308Response.model_fields["block"].description or ""
        assert "ordering not declared" in desc.lower(), (
            "T1308Response.block: must mention 'ordering not declared' "
            "so consumers do not assume an ascending/descending order."
        )
