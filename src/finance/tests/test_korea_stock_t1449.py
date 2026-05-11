"""Unit tests for t1449 가격대별매매비중조회 (Korea Stock Trading-Share by Price-Level TR).

Covers:
    - blocks.py — Pydantic input/output validation, including LS official
      example response round-trip.
    - TrT1449._build_response — happy / HTTP error / exception paths.
    - Market domain class — Korean alias bridge to TrT1449.
    - KoreaStock chained call — ``ks.시세().가격대별매매비중조회(...)``
      Korean alias path.
    - Single-shot guard — TrT1449 must not expose ``occurs_req`` (no
      LS-declared continuation cursor for t1449).
    - Field(examples=[...]) regression guards — examples present + types
      validate against declared annotations.
    - LS-declared enum mapping — both ``T1449OutBlock.sign`` and
      ``T1449OutBlock1.sign`` descriptions must embed the LS-published
      1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락 mapping.
    - LS-declared enum mapping — ``T1449InBlock.dategb`` description
      must embed 1=당일 / 2=전일 / 3=당일+전일 mapping.
    - Anti-inference guard — fields LS did NOT declare (currency unit,
      change sign convention, OutBlock1 row ordering, ``diff`` /
      ``msdiff`` / ``tickdiff`` denominators) must not embed inferred
      assertions.
    - JSON-key collision disclaimer — both blocks expose a ``diff`` field
      with different semantics (등락율 vs 비중); the OutBlock1 ``diff``
      description must call this out so the AI chatbot does not conflate
      them.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.market import Market
from programgarden_finance.ls.korea_stock.market.t1449 import TrT1449
from programgarden_finance.ls.korea_stock.market.t1449.blocks import (
    T1449InBlock,
    T1449OutBlock,
    T1449OutBlock1,
    T1449Request,
    T1449Response,
    T1449ResponseHeader,
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


def _make_request(**overrides: Any) -> T1449Request:
    body = T1449InBlock(
        shcode=overrides.pop("shcode", "001200"),
        dategb=overrides.pop("dategb", "1"),
    )
    return T1449Request(body={"t1449InBlock": body})


# LS official example response (user-supplied).
_LS_OFFICIAL_RESPONSE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1449OutBlock": {
        "volume": 322192,
        "price": 3685,
        "change": 25,
        "msvolume": 195607,
        "sign": "2",
        "diff": "0.68",
        "mdvolume": 120522,
    },
    "t1449OutBlock1": [
        {
            "price": 3750,
            "change": 90,
            "msvolume": 22107,
            "sign": "2",
            "msdiff": "100.00",
            "diff": "6.86",
            "tickdiff": "2.46",
            "mdvolume": 0,
            "cvolume": 22107,
        },
        {
            "price": 3645,
            "change": -15,
            "msvolume": 0,
            "sign": "5",
            "msdiff": "0.00",
            "diff": "0.05",
            "tickdiff": "-0.41",
            "mdvolume": 147,
            "cvolume": 147,
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


class TestT1449InBlock:
    def test_valid_today(self):
        block = T1449InBlock(shcode="001200", dategb="1")
        assert block.shcode == "001200"
        assert block.dategb == "1"

    def test_valid_yesterday(self):
        block = T1449InBlock(shcode="005930", dategb="2")
        assert block.dategb == "2"

    def test_valid_combined(self):
        block = T1449InBlock(shcode="000660", dategb="3")
        assert block.dategb == "3"

    def test_invalid_dategb_rejected(self):
        with pytest.raises(ValidationError):
            T1449InBlock(shcode="005930", dategb="9")


class TestT1449OutBlock:
    def test_decodes_ls_official(self):
        out = T1449OutBlock.model_validate(_LS_OFFICIAL_RESPONSE["t1449OutBlock"])
        assert out.price == 3685
        assert out.sign == "2"
        assert out.change == 25
        assert out.diff == pytest.approx(0.68)
        assert isinstance(out.diff, float)
        assert out.volume == 322192
        assert out.msvolume == 195607
        assert out.mdvolume == 120522

    def test_change_accepts_negative(self):
        out = T1449OutBlock.model_validate({"change": -25})
        assert out.change == -25

    def test_diff_accepts_negative_string(self):
        out = T1449OutBlock.model_validate({"diff": "-1.20"})
        assert out.diff == pytest.approx(-1.20)

    def test_defaults(self):
        out = T1449OutBlock()
        assert out.price == 0
        assert out.sign == ""
        assert out.change == 0
        assert out.diff == 0.0
        assert out.volume == 0
        assert out.msvolume == 0
        assert out.mdvolume == 0


class TestT1449OutBlock1:
    def test_decodes_ls_official_first_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1449OutBlock1"][0]
        out = T1449OutBlock1.model_validate(row)
        assert out.price == 3750
        assert out.sign == "2"
        assert out.change == 90
        assert out.tickdiff == pytest.approx(2.46)
        assert isinstance(out.tickdiff, float)
        assert out.cvolume == 22107
        assert out.diff == pytest.approx(6.86)
        assert isinstance(out.diff, float)
        assert out.mdvolume == 0
        assert out.msvolume == 22107
        assert out.msdiff == pytest.approx(100.00)
        assert isinstance(out.msdiff, float)

    def test_decodes_ls_official_second_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1449OutBlock1"][1]
        out = T1449OutBlock1.model_validate(row)
        assert out.price == 3645
        assert out.sign == "5"
        assert out.change == -15
        assert out.tickdiff == pytest.approx(-0.41)
        assert out.cvolume == 147
        assert out.diff == pytest.approx(0.05)
        assert out.mdvolume == 147
        assert out.msvolume == 0
        assert out.msdiff == pytest.approx(0.0)

    def test_defaults_when_missing(self):
        out = T1449OutBlock1()
        assert out.price == 0
        assert out.sign == ""
        assert out.change == 0
        assert out.tickdiff == 0.0
        assert out.cvolume == 0
        assert out.diff == 0.0
        assert out.mdvolume == 0
        assert out.msvolume == 0
        assert out.msdiff == 0.0


class TestT1449LSExampleResponseRoundTrip:
    """Regression guard — full LS official example response must round-trip
    through the entire response envelope without ValidationError.
    """

    def test_full_envelope_validates(self):
        rows = _LS_OFFICIAL_RESPONSE["t1449OutBlock1"]
        out_summary = _LS_OFFICIAL_RESPONSE["t1449OutBlock"]

        resp = T1449Response(
            header=None,
            out_block=T1449OutBlock.model_validate(out_summary),
            block=[T1449OutBlock1.model_validate(r) for r in rows],
            rsp_cd=_LS_OFFICIAL_RESPONSE["rsp_cd"],
            rsp_msg=_LS_OFFICIAL_RESPONSE["rsp_msg"],
            status_code=200,
            error_msg=None,
        )

        assert resp.out_block is not None
        assert resp.out_block.price == 3685
        assert len(resp.block) == 2
        assert resp.block[0].price == 3750
        assert resp.block[1].price == 3645
        assert resp.rsp_cd == "00000"


# ---------------------------------------------------------------------------
# 3. TrT1449._build_response
# ---------------------------------------------------------------------------


class TestTrT1449BuildResponse:
    def _make_tr(self) -> TrT1449:
        return TrT1449(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1449",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, _LS_OFFICIAL_RESPONSE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.out_block is not None
        assert result.out_block.price == 3685
        assert result.out_block.volume == 322192
        assert len(result.block) == 2
        assert result.block[0].price == 3750
        assert result.block[1].price == 3645
        assert result.header is not None
        assert isinstance(result.header, T1449ResponseHeader)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1449"},
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


# ---------------------------------------------------------------------------
# 4. Market domain class
# ---------------------------------------------------------------------------


class TestMarketDomain:
    def test_t1449_returns_tr_instance(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        body = T1449InBlock(shcode="001200", dategb="1")
        tr = market.t1449(body=body)
        assert isinstance(tr, TrT1449)
        assert tr.request_data.body["t1449InBlock"].shcode == "001200"
        assert tr.request_data.body["t1449InBlock"].dategb == "1"

    def test_korean_alias_class_level(self):
        assert Market.t1449 is Market.가격대별매매비중조회

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
        body = T1449InBlock(shcode="005930", dategb="3")
        tr = ks.시세().가격대별매매비중조회(body=body)
        assert isinstance(tr, TrT1449)
        assert tr.request_data.body["t1449InBlock"].shcode == "005930"
        assert tr.request_data.body["t1449InBlock"].dategb == "3"


# ---------------------------------------------------------------------------
# 6. Single-shot guard — t1449 has no continuation cursor
# ---------------------------------------------------------------------------


class TestNoContinuationCursor:
    """LS spec available to this codebase exposes no continuation cursor
    (``cts_*`` / ``idx``) and no row-count input for t1449. TrT1449 must
    therefore NOT advertise ``occurs_req`` / ``occurs_req_async`` — adding
    them silently would cause callers to depend on a paged contract that
    LS does not honor.
    """

    def test_occurs_req_not_implemented(self):
        tr = TrT1449(_make_request())
        assert not hasattr(tr, "occurs_req"), (
            "TrT1449 must not expose occurs_req — LS spec for t1449 has "
            "no continuation cursor."
        )
        assert not hasattr(tr, "occurs_req_async"), (
            "TrT1449 must not expose occurs_req_async — LS spec for "
            "t1449 has no continuation cursor."
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
        [T1449InBlock, T1449OutBlock, T1449OutBlock1],
        ids=["T1449InBlock", "T1449OutBlock", "T1449OutBlock1"],
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
        [T1449InBlock, T1449OutBlock, T1449OutBlock1],
        ids=["T1449InBlock", "T1449OutBlock", "T1449OutBlock1"],
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
        assert set(T1449InBlock.model_fields) == {"shcode", "dategb"}

    def test_outblock_fields(self):
        assert set(T1449OutBlock.model_fields) == {
            "price", "sign", "change", "diff",
            "volume", "msvolume", "mdvolume",
        }

    def test_outblock1_fields(self):
        expected = {
            "price", "sign", "change", "tickdiff",
            "cvolume", "diff",
            "mdvolume", "msvolume", "msdiff",
        }
        assert set(T1449OutBlock1.model_fields) == expected


# ---------------------------------------------------------------------------
# 9. LS-declared enum mappings — sign + dategb document the published mappings
# ---------------------------------------------------------------------------


class TestSignEnumDocumented:
    """For t1449 LS publishes the ``sign`` enum mapping
    (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락) for BOTH OutBlock and
    OutBlock1. Both descriptions must embed the mapping so the AI chatbot
    can generate correct workflows.
    """

    @pytest.mark.parametrize(
        "model_cls,label",
        [(T1449OutBlock, "T1449OutBlock"), (T1449OutBlock1, "T1449OutBlock1")],
    )
    def test_sign_enum_mapping_present(self, model_cls: Type[BaseModel], label: str):
        desc = model_cls.model_fields["sign"].description or ""
        for token in [
            "'1'", "'2'", "'3'", "'4'", "'5'",
            "upper limit", "up", "unchanged", "lower limit", "down",
            "상한", "상승", "보합", "하한", "하락",
        ]:
            assert token in desc, (
                f"{label}.sign description missing LS-declared token "
                f"'{token}'. LS publishes the full 1~5 enum mapping for t1449; "
                f"description must mirror it for AI chatbot accuracy."
            )


class TestDategbEnumDocumented:
    """LS publishes the ``dategb`` enum mapping
    (1=당일 / 2=전일 / 3=당일+전일). The InBlock description must embed
    the mapping so the AI chatbot picks the right scope.
    """

    def test_dategb_enum_mapping_present(self):
        desc = T1449InBlock.model_fields["dategb"].description or ""
        for token in [
            "'1'", "'2'", "'3'",
            "today", "previous trading day", "combined",
            "당일", "전일",
        ]:
            assert token in desc, (
                f"T1449InBlock.dategb description missing LS-declared "
                f"token '{token}'. LS publishes the full 1~3 enum mapping; "
                "description must mirror it for AI chatbot accuracy."
            )


# ---------------------------------------------------------------------------
# 10. Anti-inference guard — fields LS did NOT declare
# ---------------------------------------------------------------------------


class TestNoInferredUnitOrSemantics:
    """For t1449 LS does NOT declare:
        - Currency unit of price/change fields.
        - Sign convention of ``change`` (positive when up vs always
          non-negative magnitude).
        - Row ordering of T1449OutBlock1 (price ascending / descending /
          trade-time / other).
        - The exact denominator for ``T1449OutBlock1.diff`` ("비중").
        - The exact denominator for ``T1449OutBlock1.msdiff`` (매수비율).
        - The reference base of ``T1449OutBlock1.tickdiff`` ("등락율").
    Descriptions must not assert these to avoid teaching the AI chatbot
    false certainty.
    """

    def test_outblock_price_no_inferred_currency(self):
        desc = T1449OutBlock.model_fields["price"].description or ""
        assert "in KRW" not in desc, (
            "T1449OutBlock.price: must not infer KRW unit — LS spec does "
            "not declare currency unit explicitly."
        )

    def test_outblock1_price_no_inferred_currency(self):
        desc = T1449OutBlock1.model_fields["price"].description or ""
        assert "in KRW" not in desc, (
            "T1449OutBlock1.price: must not infer KRW unit — LS spec does "
            "not declare currency unit explicitly."
        )

    @pytest.mark.parametrize(
        "model_cls,label",
        [(T1449OutBlock, "T1449OutBlock"), (T1449OutBlock1, "T1449OutBlock1")],
    )
    def test_change_no_inferred_sign_convention(
        self, model_cls: Type[BaseModel], label: str
    ):
        desc = model_cls.model_fields["change"].description or ""
        for forbidden in [
            "positive when up", "negative when down",
            "always positive", "always non-negative",
        ]:
            assert forbidden not in desc, (
                f"{label}.change: must not assert sign convention "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_outblock1_diff_denominator_disclaimer(self):
        """LS does not declare the exact denominator for OutBlock1.diff
        ("비중", per-row trading share). The description must keep an
        explicit disclaimer.
        """
        desc = T1449OutBlock1.model_fields["diff"].description or ""
        assert "not formally declared" in desc, (
            "T1449OutBlock1.diff: must keep the LS spec disclaimer for "
            "the 비중 denominator (e.g., row volume / day-total volume)."
        )

    def test_outblock1_msdiff_denominator_disclaimer(self):
        """LS does not declare the exact denominator for OutBlock1.msdiff
        (매수비율). The description must keep an explicit disclaimer.
        """
        desc = T1449OutBlock1.model_fields["msdiff"].description or ""
        assert "not formally declared" in desc, (
            "T1449OutBlock1.msdiff: must keep the LS spec disclaimer for "
            "the 매수비율 denominator (msvolume / cvolume vs other formula)."
        )

    def test_outblock1_tickdiff_reference_base_disclaimer(self):
        """LS does not declare the reference base for OutBlock1.tickdiff
        ("등락율"). The description must keep an explicit disclaimer.
        """
        desc = T1449OutBlock1.model_fields["tickdiff"].description or ""
        assert "not formally declared" in desc, (
            "T1449OutBlock1.tickdiff: must keep the LS spec disclaimer "
            "for the 등락율 reference base."
        )

    def test_module_row_ordering_disclaimer(self):
        """LS does not declare row ordering for T1449OutBlock1. The
        blocks.py module docstring AND the Response.block field
        description must mention the disclaimer so the AI chatbot does
        not fabricate an ordering assertion.
        """
        from programgarden_finance.ls.korea_stock.market.t1449 import blocks
        doc = (blocks.__doc__ or "").lower()
        for token in ["row ordering", "not declared"]:
            assert token in doc, (
                f"blocks.py module docstring must mention '{token}' to "
                "keep the LS no-declaration disclaimer for OutBlock1 "
                "row ordering."
            )

    def test_response_block_description_row_ordering_disclaimer(self):
        """T1449Response.block description must also carry the row-
        ordering disclaimer so consumers reading the Response model
        directly (not the module docstring) see it.
        """
        desc = T1449Response.model_fields["block"].description or ""
        assert "ordering not declared" in desc.lower(), (
            "T1449Response.block: must mention 'ordering not declared' "
            "so consumers do not assume an ascending/descending order."
        )


# ---------------------------------------------------------------------------
# 11. JSON-key collision disclaimer — OutBlock.diff vs OutBlock1.diff
# ---------------------------------------------------------------------------


class TestDiffSemanticCollisionDocumented:
    """Both blocks expose a ``diff`` field but with different LS labels:
    OutBlock.diff = 등락율 (percent change vs previous close);
    OutBlock1.diff = 비중 (per-row trading share). The OutBlock1.diff
    description must explicitly call this out so the AI chatbot does
    not conflate them.
    """

    def test_outblock1_diff_calls_out_collision(self):
        desc = T1449OutBlock1.model_fields["diff"].description or ""
        assert "등락율" in desc and "비중" in desc, (
            "T1449OutBlock1.diff description must contrast OutBlock.diff "
            "(등락율) vs OutBlock1.diff (비중) so the AI chatbot does "
            "not conflate the two."
        )
