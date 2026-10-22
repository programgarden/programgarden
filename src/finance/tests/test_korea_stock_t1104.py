"""Unit tests for t1104 주식현재가시세메모 (Korea Stock Current-Quote Memo TR).

Covers:
    - blocks.py — Pydantic input/output validation, Literal enum guards.
    - TrT1104._build_response — happy / HTTP error / exception paths.
    - Market domain class — Korean alias bridge to TrT1104.
    - KoreaStock chained call — ``ks.시세().주식현재가시세메모(...)`` path.
    - Field(examples=[...]) regression guards — examples present + types
      validate against declared annotations.
    - Model fields coverage — silent LS spec drift guard.
    - LS-declared enum mappings — ``gubn`` / ``dat1`` / ``dat2``
      descriptions must embed the LS-published mapping.
    - Anti-inference guard — ``vals`` description must NOT assert
      unit / decimal scale / format (LS did not declare).
    - No-pagination guard — TrT1104 must NOT expose ``occurs_req``.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.market import Market
from programgarden_finance.ls.korea_stock.market.t1104 import TrT1104
from programgarden_finance.ls.korea_stock.market.t1104.blocks import (
    T1104InBlock,
    T1104InBlock1,
    T1104OutBlock,
    T1104OutBlock1,
    T1104Request,
    T1104Response,
    T1104ResponseHeader,
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


def _make_request(**overrides: Any) -> T1104Request:
    in_body = T1104InBlock(
        code=overrides.pop("code", "078020"),
        nrec=overrides.pop("nrec", "02"),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    in_body1 = overrides.pop("in_body1", [
        T1104InBlock1(indx="0", gubn="1", dat1="1", dat2="1"),
        T1104InBlock1(indx="1", gubn="2", dat1="2", dat2="2"),
    ])
    return T1104Request(body={
        "t1104InBlock": in_body,
        "t1104InBlock1": in_body1,
    })


# A synthetic happy-path response payload. LS official spec only publishes
# the "no-data" example ("해당자료가 없습니다."); the values below are
# representative shapes that satisfy the published Length/enum constraints.
_SYNTHETIC_HAPPY_RESPONSE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1104OutBlock": {"nrec": "02"},
    "t1104OutBlock1": [
        {"indx": "0", "gubn": "1", "vals": "00079800"},
        {"indx": "1", "gubn": "2", "vals": "00078900"},
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


class TestT1104InBlock:
    def test_valid_minimal(self):
        block = T1104InBlock(code="005930")
        assert block.code == "005930"
        assert block.nrec == ""
        assert block.exchgubun == "K"

    def test_valid_full(self):
        block = T1104InBlock(code="000660", nrec="04", exchgubun="N")
        assert block.code == "000660"
        assert block.nrec == "04"
        assert block.exchgubun == "N"

    def test_exchgubun_unified(self):
        block = T1104InBlock(code="005930", exchgubun="U")
        assert block.exchgubun == "U"

    def test_invalid_exchgubun_rejected(self):
        with pytest.raises(ValidationError):
            T1104InBlock(code="005930", exchgubun="X")

    def test_code_required(self):
        with pytest.raises(ValidationError):
            T1104InBlock(nrec="01")


class TestT1104InBlock1:
    def test_valid_all_categories(self):
        for gubn in ["1", "2", "3", "4"]:
            block = T1104InBlock1(indx="0", gubn=gubn, dat1="1", dat2="1")
            assert block.gubn == gubn

    def test_valid_dat1_keys(self):
        for dat1 in ["1", "2", "3", "4"]:
            block = T1104InBlock1(indx="0", gubn="1", dat1=dat1, dat2="1")
            assert block.dat1 == dat1

    def test_valid_dat2_keys(self):
        for dat2 in ["1", "2"]:
            block = T1104InBlock1(indx="0", gubn="1", dat1="1", dat2=dat2)
            assert block.dat2 == dat2

    def test_invalid_gubn_rejected(self):
        with pytest.raises(ValidationError):
            T1104InBlock1(indx="0", gubn="9", dat1="1", dat2="1")

    def test_invalid_dat1_rejected(self):
        with pytest.raises(ValidationError):
            T1104InBlock1(indx="0", gubn="1", dat1="9", dat2="1")

    def test_invalid_dat2_rejected(self):
        with pytest.raises(ValidationError):
            T1104InBlock1(indx="0", gubn="1", dat1="1", dat2="3")


class TestT1104OutBlock:
    def test_decodes_nrec(self):
        out = T1104OutBlock.model_validate({"nrec": "04"})
        assert out.nrec == "04"

    def test_default_empty(self):
        out = T1104OutBlock()
        assert out.nrec == ""


class TestT1104OutBlock1:
    def test_decodes_row(self):
        row = _SYNTHETIC_HAPPY_RESPONSE["t1104OutBlock1"][0]
        out = T1104OutBlock1.model_validate(row)
        assert out.indx == "0"
        assert out.gubn == "1"
        assert out.vals == "00079800"

    def test_invalid_gubn_rejected(self):
        with pytest.raises(ValidationError):
            T1104OutBlock1.model_validate({"indx": "0", "gubn": "9", "vals": ""})

    def test_defaults_when_missing(self):
        out = T1104OutBlock1()
        assert out.indx == ""
        assert out.gubn == "1"
        assert out.vals == ""


# ---------------------------------------------------------------------------
# 3. TrT1104._build_response
# ---------------------------------------------------------------------------


class TestTrT1104BuildResponse:
    def _make_tr(self) -> TrT1104:
        return TrT1104(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1104",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, _SYNTHETIC_HAPPY_RESPONSE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.summary_block is not None
        assert result.summary_block.nrec == "02"
        assert len(result.block) == 2
        assert result.block[0].indx == "0"
        assert result.block[0].gubn == "1"
        assert result.block[0].vals == "00079800"
        assert result.block[1].indx == "1"
        assert result.block[1].gubn == "2"
        assert result.header is not None
        assert isinstance(result.header, T1104ResponseHeader)

    def test_no_data_path(self):
        """LS official example response (해당자료가 없습니다.)."""
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        result = tr._build_response(
            resp_obj,
            {"rsp_cd": "00000", "rsp_msg": "해당자료가 없습니다."},
            {
                "Content-Type": "application/json; charset=utf-8",
                "tr_cd": "t1104",
                "tr_cont": "N",
                "tr_cont_key": "",
            },
            None,
        )
        assert result.error_msg is None
        assert result.rsp_cd == "00000"
        assert result.summary_block is None
        assert result.block == []

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1104"},
            None,
        )
        assert result.status_code == 500
        assert result.error_msg is not None
        assert "500" in result.error_msg
        assert "Internal error" in result.error_msg
        assert result.header is None
        assert result.summary_block is None
        assert result.block == []

    def test_exception_path(self):
        tr = self._make_tr()
        result = tr._build_response(None, None, None, RuntimeError("boom"))
        assert result.error_msg == "boom"
        assert result.status_code is None
        assert result.summary_block is None
        assert result.block == []


# ---------------------------------------------------------------------------
# 4. Market domain class
# ---------------------------------------------------------------------------


class TestMarketDomain:
    def test_t1104_returns_tr_instance(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        in0 = T1104InBlock(code="078020", nrec="01", exchgubun="K")
        in1 = [T1104InBlock1(indx="0", gubn="1", dat1="1", dat2="1")]
        tr = market.t1104(t1104InBlock_body=in0, t1104InBlock1_body=in1)
        assert isinstance(tr, TrT1104)
        assert tr.request_data.body["t1104InBlock"].code == "078020"
        assert tr.request_data.body["t1104InBlock"].exchgubun == "K"
        in_list = tr.request_data.body["t1104InBlock1"]
        assert isinstance(in_list, list)
        assert len(in_list) == 1
        assert in_list[0].gubn == "1"

    def test_t1104_accepts_none_occurs_body(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        in0 = T1104InBlock(code="005930", exchgubun="K")
        tr = market.t1104(t1104InBlock_body=in0)
        assert isinstance(tr, TrT1104)
        assert tr.request_data.body["t1104InBlock1"] is None

    def test_korean_alias_class_level(self):
        assert Market.t1104 is Market.주식현재가시세메모

    def test_token_manager_required(self):
        with pytest.raises(ValueError):
            Market(token_manager=None)


# ---------------------------------------------------------------------------
# 5. KoreaStock entry point — Korean alias chain
# ---------------------------------------------------------------------------


class TestKoreaStockMarketEntry:
    def test_chained_call_korean_alias(self):
        tm = _make_token_manager()
        ks = KoreaStock(tm)
        in0 = T1104InBlock(code="000660", nrec="01", exchgubun="N")
        in1 = [T1104InBlock1(indx="0", gubn="3", dat1="2", dat2="2")]
        tr = ks.시세().주식현재가시세메모(t1104InBlock_body=in0, t1104InBlock1_body=in1)
        assert isinstance(tr, TrT1104)
        assert tr.request_data.body["t1104InBlock"].code == "000660"
        assert tr.request_data.body["t1104InBlock"].exchgubun == "N"


# ---------------------------------------------------------------------------
# 6. Field(examples=[...]) regression guard
# ---------------------------------------------------------------------------


class TestFieldExamplesValidate:
    """Each value in ``Field(examples=[...])`` must round-trip through
    ``TypeAdapter(<annotation>).validate_python(value)``. AI chatbots learn
    from these; an example with a wrong type or wrong Literal value silently
    teaches bad input.
    """

    @pytest.mark.parametrize(
        "model_cls",
        [T1104InBlock, T1104InBlock1, T1104OutBlock, T1104OutBlock1],
        ids=["T1104InBlock", "T1104InBlock1", "T1104OutBlock", "T1104OutBlock1"],
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
        [T1104InBlock, T1104InBlock1, T1104OutBlock1],
        ids=["T1104InBlock", "T1104InBlock1", "T1104OutBlock1"],
    )
    def test_every_field_has_examples(self, model_cls: Type[BaseModel]):
        missing = [
            name
            for name, info in model_cls.model_fields.items()
            if not (info.examples or [])
        ]
        assert not missing, (
            f"{model_cls.__name__} fields without examples=[...]: {missing}. "
            "All InBlock / InBlock1 / OutBlock1 fields must carry AI-readable "
            "examples."
        )


# ---------------------------------------------------------------------------
# 7. Model fields coverage — guard against silent LS spec drift
# ---------------------------------------------------------------------------


class TestModelFieldsCoverage:
    def test_inblock_fields(self):
        assert set(T1104InBlock.model_fields) == {"code", "nrec", "exchgubun"}

    def test_inblock1_fields(self):
        assert set(T1104InBlock1.model_fields) == {"indx", "gubn", "dat1", "dat2"}

    def test_outblock_fields(self):
        assert set(T1104OutBlock.model_fields) == {"nrec"}

    def test_outblock1_fields(self):
        assert set(T1104OutBlock1.model_fields) == {"indx", "gubn", "vals"}


# ---------------------------------------------------------------------------
# 8. LS-declared enum mappings present in descriptions
# ---------------------------------------------------------------------------


class TestEnumMappingDocumented:
    """LS publishes enum mappings for ``gubn`` / ``dat1`` / ``dat2`` /
    ``exchgubun``. Descriptions must embed the mapping so AI chatbots can
    generate correct directive payloads and interpret responses.
    """

    def test_gubn_mapping_present_in_inblock1(self):
        desc = T1104InBlock1.model_fields["gubn"].description or ""
        for token in [
            "'1' = quote", "시세",
            "'2' = period high/low", "최고저가",
            "'3' = Pivot", "피봇",
            "'4' = moving average", "이동평균선",
        ]:
            assert token in desc, (
                f"T1104InBlock1.gubn description missing LS-declared token "
                f"'{token}'."
            )

    def test_dat1_mapping_present_in_inblock1(self):
        desc = T1104InBlock1.model_fields["dat1"].description or ""
        for token in [
            "'1' = open", "시가",
            "'2' = high", "고가",
            "'3' = low", "저가",
            "'4' = weighted average", "가중평균가",
        ]:
            assert token in desc

    def test_dat2_mapping_present_in_inblock1(self):
        desc = T1104InBlock1.model_fields["dat2"].description or ""
        for token in [
            "'1' = today", "당일",
            "'2' = previous day", "전일",
        ]:
            assert token in desc

    def test_exchgubun_mapping_present_in_inblock(self):
        # Description must list the K/N/U enum mapping AND state that the
        # Pydantic Literal strictly rejects empty string and other values
        # (LS-side "treat as KRX" coercion is unreachable through this client).
        desc = T1104InBlock.model_fields["exchgubun"].description or ""
        for token in [
            "'K' = KRX", "한국거래소",
            "'N' = NXT", "넥스트레이드",
            "'U' = unified", "통합",
            "validates strictly", "rejected",
        ]:
            assert token in desc

    def test_outblock1_gubn_mapping_present(self):
        desc = T1104OutBlock1.model_fields["gubn"].description or ""
        for token in [
            "'1' = quote", "'2' = period high/low",
            "'3' = Pivot", "'4' = moving average",
        ]:
            assert token in desc


# ---------------------------------------------------------------------------
# 9. Anti-inference guard — vals must not assert undeclared semantics
# ---------------------------------------------------------------------------


class TestNoInferredVals:
    """LS does not publish unit / decimal scale / format for the OutBlock1
    ``vals`` field. The description must explicitly note this rather than
    invent semantics.
    """

    def test_vals_description_states_unknown(self):
        desc = T1104OutBlock1.model_fields["vals"].description or ""
        assert "not declared" in desc, (
            "T1104OutBlock1.vals description must state that unit / scale / "
            "format are not declared in available source (no inference)."
        )


# ---------------------------------------------------------------------------
# 10. No-pagination guard — t1104 must not expose occurs_req
# ---------------------------------------------------------------------------


class TestNoPagination:
    def test_no_occurs_req(self):
        assert not hasattr(TrT1104, "occurs_req"), (
            "t1104 has no LS pagination cursor — occurs_req must not be exposed."
        )

    def test_no_occurs_req_async(self):
        assert not hasattr(TrT1104, "occurs_req_async")


# ---------------------------------------------------------------------------
# 11. Rate-limit configuration matches LS spec (3 TR/sec)
# ---------------------------------------------------------------------------


class TestRateLimit:
    def test_default_options(self):
        req = _make_request()
        assert req.options.rate_limit_count == 3
        assert req.options.rate_limit_seconds == 1
        assert req.options.rate_limit_key == "t1104"
