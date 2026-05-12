"""Unit tests for t1105 주식피봇/디마크조회 (Korea Stock Pivot & Demark Levels TR).

Covers:
    - blocks.py — Pydantic input/output validation, including LS official
      example response round-trip.
    - TrT1105._build_response — happy / HTTP error / exception paths.
    - Market domain class — Korean alias bridge to TrT1105.
    - KoreaStock chained call — ``ks.시세().주식피봇디마크조회(...)``
      Korean alias path.
    - Single-shot guard — TrT1105 must not expose ``occurs_req`` (no
      LS-declared continuation cursor for t1105).
    - Field(examples=[...]) regression guards — examples present + types
      validate against declared annotations.
    - LS-declared enum mapping — ``T1105InBlock.exchgubun`` description
      must embed K=KRX / N=NXT / U=unified mapping.
    - Anti-inference guard — t1105's pivot / Demark / support / resistance
      formulas are NOT declared in available LS source. Descriptions
      must not embed inferred formulas, derivations, or vendor-specific
      assertions.
    - Rate limit guard — 3 TR/sec, key=t1105.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.market import Market
from programgarden_finance.ls.korea_stock.market.t1105 import TrT1105
from programgarden_finance.ls.korea_stock.market.t1105.blocks import (
    T1105InBlock,
    T1105OutBlock,
    T1105Request,
    T1105Response,
    T1105ResponseHeader,
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


def _make_request(**overrides: Any) -> T1105Request:
    body = T1105InBlock(
        shcode=overrides.pop("shcode", "001200"),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1105Request(body={"t1105InBlock": body})


# LS official example response (from t1105 spec sample).
_LS_OFFICIAL_RESPONSE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1105OutBlock": {
        "offer2": 3883,
        "stdprc": 7182,
        "offer1": 3771,
        "pbot": 3563,
        "supp1": 3451,
        "shcode": "001200",
        "suppd": 3507,
        "supp2": 3243,
        "offerd": 3827,
    },
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


class TestT1105InBlock:
    def test_valid_krx_default(self):
        block = T1105InBlock(shcode="001200")
        assert block.shcode == "001200"
        assert block.exchgubun == "K"

    def test_valid_nxt(self):
        block = T1105InBlock(shcode="005930", exchgubun="N")
        assert block.exchgubun == "N"

    def test_valid_unified(self):
        block = T1105InBlock(shcode="000660", exchgubun="U")
        assert block.exchgubun == "U"

    def test_invalid_exchgubun_rejected(self):
        with pytest.raises(ValidationError):
            T1105InBlock(shcode="005930", exchgubun="Z")


class TestT1105OutBlock:
    def test_decodes_ls_official(self):
        out = T1105OutBlock.model_validate(_LS_OFFICIAL_RESPONSE["t1105OutBlock"])
        assert out.shcode == "001200"
        assert out.pbot == 3563
        assert out.offer1 == 3771
        assert out.supp1 == 3451
        assert out.offer2 == 3883
        assert out.supp2 == 3243
        assert out.stdprc == 7182
        assert out.offerd == 3827
        assert out.suppd == 3507

    def test_defaults(self):
        out = T1105OutBlock()
        assert out.shcode == ""
        assert out.pbot == 0
        assert out.offer1 == 0
        assert out.supp1 == 0
        assert out.offer2 == 0
        assert out.supp2 == 0
        assert out.stdprc == 0
        assert out.offerd == 0
        assert out.suppd == 0


class TestT1105LSExampleResponseRoundTrip:
    """Regression guard — full LS official example response must round-trip
    through the entire response envelope without ValidationError.
    """

    def test_full_envelope_validates(self):
        out_block = _LS_OFFICIAL_RESPONSE["t1105OutBlock"]

        resp = T1105Response(
            header=None,
            block=T1105OutBlock.model_validate(out_block),
            rsp_cd=_LS_OFFICIAL_RESPONSE["rsp_cd"],
            rsp_msg=_LS_OFFICIAL_RESPONSE["rsp_msg"],
            status_code=200,
            error_msg=None,
        )

        assert resp.block is not None
        assert resp.block.pbot == 3563
        assert resp.block.shcode == "001200"
        assert resp.rsp_cd == "00000"


# ---------------------------------------------------------------------------
# 3. TrT1105._build_response
# ---------------------------------------------------------------------------


class TestTrT1105BuildResponse:
    def _make_tr(self) -> TrT1105:
        return TrT1105(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1105",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, _LS_OFFICIAL_RESPONSE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.block is not None
        assert result.block.pbot == 3563
        assert result.block.offer1 == 3771
        assert result.block.suppd == 3507
        assert result.header is not None
        assert isinstance(result.header, T1105ResponseHeader)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1105"},
            None,
        )
        assert result.status_code == 500
        assert result.error_msg is not None
        assert "500" in result.error_msg
        assert "Internal error" in result.error_msg
        assert result.header is None
        assert result.block is None

    def test_exception_path(self):
        tr = self._make_tr()
        result = tr._build_response(None, None, None, RuntimeError("boom"))
        assert result.error_msg == "boom"
        assert result.status_code is None
        assert result.block is None

    def test_empty_outblock_path(self):
        """When LS returns rsp_cd but omits the OutBlock (e.g.,
        '해당자료가 없습니다.'), parsed_block stays None and rsp fields
        still propagate.
        """
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        result = tr._build_response(
            resp_obj,
            {"rsp_cd": "00136", "rsp_msg": "해당자료가 없습니다."},
            {
                "Content-Type": "application/json; charset=utf-8",
                "tr_cd": "t1105",
                "tr_cont": "N",
                "tr_cont_key": "",
            },
            None,
        )
        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00136"
        assert result.rsp_msg == "해당자료가 없습니다."
        assert result.block is None


# ---------------------------------------------------------------------------
# 4. Market domain class
# ---------------------------------------------------------------------------


class TestMarketDomain:
    def test_t1105_returns_tr_instance(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        body = T1105InBlock(shcode="001200", exchgubun="K")
        tr = market.t1105(body=body)
        assert isinstance(tr, TrT1105)
        assert tr.request_data.body["t1105InBlock"].shcode == "001200"
        assert tr.request_data.body["t1105InBlock"].exchgubun == "K"

    def test_korean_alias_class_level(self):
        assert Market.t1105 is Market.주식피봇디마크조회

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
        body = T1105InBlock(shcode="005930", exchgubun="U")
        tr = ks.시세().주식피봇디마크조회(body=body)
        assert isinstance(tr, TrT1105)
        assert tr.request_data.body["t1105InBlock"].shcode == "005930"
        assert tr.request_data.body["t1105InBlock"].exchgubun == "U"


# ---------------------------------------------------------------------------
# 6. Single-shot guard — t1105 has no continuation cursor
# ---------------------------------------------------------------------------


class TestNoContinuationCursor:
    """LS spec available to this codebase exposes no continuation cursor
    (``cts_*`` / ``idx``) and no row-count input for t1105. TrT1105 must
    therefore NOT advertise ``occurs_req`` / ``occurs_req_async`` — adding
    them silently would cause callers to depend on a paged contract that
    LS does not honor.
    """

    def test_occurs_req_not_implemented(self):
        tr = TrT1105(_make_request())
        assert not hasattr(tr, "occurs_req"), (
            "TrT1105 must not expose occurs_req — LS spec for t1105 has "
            "no continuation cursor."
        )
        assert not hasattr(tr, "occurs_req_async"), (
            "TrT1105 must not expose occurs_req_async — LS spec for "
            "t1105 has no continuation cursor."
        )


# ---------------------------------------------------------------------------
# 7. Rate limit guard
# ---------------------------------------------------------------------------


class TestRateLimit:
    def test_rate_limit_values(self):
        req = _make_request()
        assert req.options.rate_limit_count == 3
        assert req.options.rate_limit_seconds == 1
        assert req.options.rate_limit_key == "t1105"


# ---------------------------------------------------------------------------
# 8. Field(examples=[...]) regression guard
# ---------------------------------------------------------------------------


class TestFieldExamplesValidate:
    """Each value in ``Field(examples=[...])`` must round-trip through
    ``TypeAdapter(<annotation>).validate_python(value)``. AI chatbots learn
    from these; an example with a wrong type or wrong Literal value silently
    teaches bad input.
    """

    @pytest.mark.parametrize(
        "model_cls",
        [T1105InBlock, T1105OutBlock],
        ids=["T1105InBlock", "T1105OutBlock"],
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
        [T1105InBlock, T1105OutBlock],
        ids=["T1105InBlock", "T1105OutBlock"],
    )
    def test_every_field_has_examples(self, model_cls: Type[BaseModel]):
        missing = [
            name
            for name, info in model_cls.model_fields.items()
            if not (info.examples or [])
        ]
        assert not missing, (
            f"{model_cls.__name__} fields without examples=[...]: {missing}. "
            "All InBlock / OutBlock fields must carry AI-readable examples."
        )


# ---------------------------------------------------------------------------
# 9. Model fields coverage — guard against silent LS spec drift
# ---------------------------------------------------------------------------


class TestModelFieldsCoverage:
    """If LS adds or removes fields silently, this guard fires immediately."""

    def test_inblock_fields(self):
        assert set(T1105InBlock.model_fields) == {"shcode", "exchgubun"}

    def test_outblock_fields(self):
        assert set(T1105OutBlock.model_fields) == {
            "shcode",
            "pbot",
            "offer1",
            "supp1",
            "offer2",
            "supp2",
            "stdprc",
            "offerd",
            "suppd",
        }


# ---------------------------------------------------------------------------
# 10. LS-declared enum mapping — exchgubun documents the published mapping
# ---------------------------------------------------------------------------


class TestExchgubunEnumDocumented:
    """LS publishes the ``exchgubun`` enum mapping
    (K = KRX, N = NXT, U = unified). The Pydantic Literal type in this
    client strictly rejects empty string and other values before LS sees
    them — the LS-side "그외 입력값은 KRX로 처리" coercion is therefore
    unreachable. The description must embed the mapping AND the strict
    validation contract so the AI chatbot generates correct workflows.
    """

    def test_exchgubun_enum_mapping_present(self):
        desc = T1105InBlock.model_fields["exchgubun"].description or ""
        for token in [
            "'K'", "'N'", "'U'",
            "KRX", "NXT", "unified",
            "validates strictly", "rejected",
        ]:
            assert token in desc, (
                f"T1105InBlock.exchgubun description missing required token "
                f"'{token}'. Description must list the K/N/U enum mapping AND "
                f"state that Pydantic validates strictly (rejecting empty "
                f"string and other values)."
            )


# ---------------------------------------------------------------------------
# 11. Anti-inference guard — pivot / Demark formulas are NOT declared
# ---------------------------------------------------------------------------


class TestNoInferredFormulas:
    """For t1105 LS publishes only the field labels (피봇, 1차/2차 저항/지지,
    기준가격, D저항/D지지). The underlying pivot / Demark mathematical
    formulas are vendor-specific and NOT declared in available LS source.

    Per CLAUDE.md ``feedback_no_inferred_formulas``, descriptions must
    not assert a derivation (classical pivot formula, Demark formula,
    ratio relationships, etc.) that LS itself does not document.
    """

    # Tokens that would indicate an inferred derivation. We use word-
    # boundary-aware patterns so harmless substrings (e.g., "high level")
    # do not accidentally fail.
    _FORBIDDEN_TOKEN_PATTERNS = [
        r"\bclassical pivot\b",
        r"\(high \+ low \+ close\)",
        r"\bH \+ L \+ C\b",
        r"\bcalculated as\b",
        r"\bequals\b",
        r"\bformula:\s",
        r"= 2 \* pbot",
        r"= 2\*pbot",
        r"\bpbot - \(high - low\)",
        r"\bDemark formula:",
    ]

    _LEVEL_FIELDS = ["pbot", "offer1", "supp1", "offer2", "supp2", "stdprc", "offerd", "suppd"]

    @pytest.mark.parametrize("field_name", _LEVEL_FIELDS)
    def test_no_inferred_derivation(self, field_name: str):
        desc = T1105OutBlock.model_fields[field_name].description or ""
        for pattern in self._FORBIDDEN_TOKEN_PATTERNS:
            assert not re.search(pattern, desc, flags=re.IGNORECASE), (
                f"T1105OutBlock.{field_name} description must not embed "
                f"the inferred pattern '{pattern}'. LS does not declare "
                f"pivot/Demark formulas — per feedback_no_inferred_formulas, "
                f"only restate the field label."
            )

    @pytest.mark.parametrize("field_name", _LEVEL_FIELDS)
    def test_disclaimer_present(self, field_name: str):
        """Every level field must carry an explicit 'not declared in
        available source' (or equivalent) disclaimer. Without it, an AI
        chatbot would default to assuming the classical pivot formula.
        """
        desc = T1105OutBlock.model_fields[field_name].description or ""
        assert "not declared in available source" in desc, (
            f"T1105OutBlock.{field_name} description must explicitly "
            f"state that the LS source does not declare the derivation "
            f"(formula / reference base) for this field."
        )

    def test_module_docstring_disclaimer(self):
        """blocks.py module docstring must declare the no-formula policy
        for AI chatbot context loading.
        """
        from programgarden_finance.ls.korea_stock.market.t1105 import blocks
        doc = (blocks.__doc__ or "").lower()
        for token in ["formula", "not declared"]:
            assert token in doc, (
                f"blocks.py module docstring must mention '{token}' to "
                "keep the LS no-formula disclaimer for pivot/Demark levels."
            )


class TestNoInferredUnitOrSemantics:
    """LS does NOT declare:
        - Currency unit of price fields.
        - Decimal scale.
        - Reference base of ``stdprc`` (today / previous close / other).
    Descriptions must not assert these to avoid teaching the AI chatbot
    false certainty.
    """

    @pytest.mark.parametrize(
        "field_name",
        ["pbot", "offer1", "supp1", "offer2", "supp2", "stdprc", "offerd", "suppd"],
    )
    def test_price_no_inferred_currency(self, field_name: str):
        desc = T1105OutBlock.model_fields[field_name].description or ""
        assert "in KRW" not in desc, (
            f"T1105OutBlock.{field_name}: must not infer KRW unit — "
            f"LS spec does not declare currency unit explicitly."
        )

    def test_stdprc_no_inferred_reference_base(self):
        """LS does not declare whether stdprc reflects today's reference
        price, previous close, or another base. Description must not
        assert one.
        """
        desc = T1105OutBlock.model_fields["stdprc"].description or ""
        for forbidden in [
            "previous closing price",
            "previous close price",
            "today's opening price",
            "today's reference price is",
        ]:
            assert forbidden not in desc, (
                f"T1105OutBlock.stdprc: must not assert reference base "
                f"'{forbidden}' — LS spec does not declare it."
            )
