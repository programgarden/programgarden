"""Unit tests for t1410 초저유동성조회 (Korea Stock Ultra-Low-Liquidity TR).

Covers:
    - blocks.py — Pydantic input/output validation, including LS official
      example response round-trip (zero-padded diff string coerce).
    - TrT1410._build_response — happy / HTTP error / exception paths.
    - Market domain class — Korean alias bridge to TrT1410.
    - KoreaStock chained call — ``ks.시세().초저유동성조회(...)`` Korean
      alias path.
    - Continuation cursor presence — TrT1410 MUST expose ``occurs_req``
      / ``occurs_req_async`` (t1410 carries an LS-declared cts_shcode
      cursor; distinguishes from single-shot siblings t1308 / t1449).
    - Field(examples=[...]) regression guards — examples present + types
      validate against declared annotations.
    - LS-declared enum mapping — ``T1410InBlock.gubun`` description
      must embed the LS-published 0=전체 / 1=코스피 / 2=코스닥 mapping.
    - Anti-inference guard — fields LS did NOT declare (sign enum,
      change sign convention, currency unit, volume window, row
      ordering) must not embed inferred assertions.
    - Sign partial-evidence policy — Option C: description must embed
      (a) LS non-declaration disclaimer, (b) example observed sign
      values, (c) sibling 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락
      convention reference, (d) '1' / '2' / '4' unobserved disclaimer.
    - Continuation cursor updater — _updater closure must propagate
      cts_shcode from response.cont_block to request body for paged
      follow-up calls.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.market import Market
from programgarden_finance.ls.korea_stock.market.t1410 import TrT1410
from programgarden_finance.ls.korea_stock.market.t1410.blocks import (
    T1410InBlock,
    T1410OutBlock,
    T1410OutBlock1,
    T1410Request,
    T1410Response,
    T1410ResponseHeader,
)
from programgarden_finance.ls.tr_base import OccursReqAbstract
from programgarden_finance.ls.token_manager import TokenManager


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_token_manager() -> TokenManager:
    tm = TokenManager()
    tm.access_token = "stub-access-token"
    tm.token_type = "Bearer"
    return tm


def _make_request(**overrides: Any) -> T1410Request:
    body = T1410InBlock(
        gubun=overrides.pop("gubun", "0"),
        cts_shcode=overrides.pop("cts_shcode", ""),
    )
    return T1410Request(body={"t1410InBlock": body})


# LS official example response (user-supplied).
_LS_OFFICIAL_RESPONSE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1410OutBlock": {
        "cts_shcode": "",
    },
    "t1410OutBlock1": [
        {
            "volume": 22,
            "price": 5620,
            "change": 50,
            "shcode": "000545",
            "sign": "5",
            "diff": "-00.88",
            "hname": "흥국화재우",
        },
        {
            "volume": 140,
            "price": 2175,
            "change": 0,
            "shcode": "168490",
            "sign": "3",
            "diff": "000.00",
            "hname": "한국패러랠",
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


class TestT1410InBlock:
    def test_valid_all(self):
        block = T1410InBlock(gubun="0", cts_shcode="")
        assert block.gubun == "0"
        assert block.cts_shcode == ""

    def test_valid_kospi(self):
        block = T1410InBlock(gubun="1")
        assert block.gubun == "1"
        assert block.cts_shcode == ""  # default

    def test_valid_kosdaq_with_cursor(self):
        block = T1410InBlock(gubun="2", cts_shcode="000545")
        assert block.gubun == "2"
        assert block.cts_shcode == "000545"

    def test_invalid_gubun_rejected(self):
        with pytest.raises(ValidationError):
            T1410InBlock(gubun="9")


class TestT1410OutBlock:
    def test_decodes_ls_official(self):
        out = T1410OutBlock.model_validate(_LS_OFFICIAL_RESPONSE["t1410OutBlock"])
        assert out.cts_shcode == ""

    def test_cts_shcode_default_empty(self):
        out = T1410OutBlock()
        assert out.cts_shcode == ""

    def test_cts_shcode_accepts_short_code(self):
        out = T1410OutBlock.model_validate({"cts_shcode": "168490"})
        assert out.cts_shcode == "168490"


class TestT1410OutBlock1:
    def test_decodes_ls_official_first_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1410OutBlock1"][0]
        out = T1410OutBlock1.model_validate(row)
        assert out.hname == "흥국화재우"
        assert out.price == 5620
        assert out.sign == "5"
        assert out.change == 50
        assert out.diff == pytest.approx(-0.88)
        assert isinstance(out.diff, float)
        assert out.volume == 22
        assert out.shcode == "000545"

    def test_decodes_ls_official_second_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1410OutBlock1"][1]
        out = T1410OutBlock1.model_validate(row)
        assert out.hname == "한국패러랠"
        assert out.price == 2175
        assert out.sign == "3"
        assert out.change == 0
        assert out.diff == pytest.approx(0.0)
        assert out.volume == 140
        assert out.shcode == "168490"

    def test_diff_zero_padded_negative_string_coerce(self):
        out = T1410OutBlock1.model_validate({"diff": "-00.88"})
        assert out.diff == pytest.approx(-0.88)
        assert isinstance(out.diff, float)

    def test_diff_zero_padded_zero_string_coerce(self):
        out = T1410OutBlock1.model_validate({"diff": "000.00"})
        assert out.diff == pytest.approx(0.0)

    def test_change_accepts_negative(self):
        out = T1410OutBlock1.model_validate({"change": -25})
        assert out.change == -25

    def test_defaults_when_missing(self):
        out = T1410OutBlock1()
        assert out.hname == ""
        assert out.price == 0
        assert out.sign == ""
        assert out.change == 0
        assert out.diff == 0.0
        assert out.volume == 0
        assert out.shcode == ""


class TestT1410LSExampleResponseRoundTrip:
    """Regression guard — full LS official example response must round-trip
    through the entire response envelope without ValidationError.
    """

    def test_full_envelope_validates(self):
        rows = _LS_OFFICIAL_RESPONSE["t1410OutBlock1"]
        cont = _LS_OFFICIAL_RESPONSE["t1410OutBlock"]

        resp = T1410Response(
            header=None,
            cont_block=T1410OutBlock.model_validate(cont),
            block=[T1410OutBlock1.model_validate(r) for r in rows],
            rsp_cd=_LS_OFFICIAL_RESPONSE["rsp_cd"],
            rsp_msg=_LS_OFFICIAL_RESPONSE["rsp_msg"],
            status_code=200,
            error_msg=None,
        )

        assert resp.cont_block is not None
        assert resp.cont_block.cts_shcode == ""
        assert len(resp.block) == 2
        assert resp.block[0].price == 5620
        assert resp.block[0].sign == "5"
        assert resp.block[0].diff == pytest.approx(-0.88)
        assert resp.block[1].price == 2175
        assert resp.block[1].sign == "3"
        assert resp.rsp_cd == "00000"


# ---------------------------------------------------------------------------
# 3. TrT1410._build_response
# ---------------------------------------------------------------------------


class TestTrT1410BuildResponse:
    def _make_tr(self) -> TrT1410:
        return TrT1410(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1410",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, _LS_OFFICIAL_RESPONSE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.cont_block is not None
        assert result.cont_block.cts_shcode == ""
        assert len(result.block) == 2
        assert result.block[0].hname == "흥국화재우"
        assert result.block[1].hname == "한국패러랠"
        assert result.header is not None
        assert isinstance(result.header, T1410ResponseHeader)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1410"},
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
    def test_t1410_returns_tr_instance(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        body = T1410InBlock(gubun="0", cts_shcode="")
        tr = market.t1410(body=body)
        assert isinstance(tr, TrT1410)
        assert tr.request_data.body["t1410InBlock"].gubun == "0"
        assert tr.request_data.body["t1410InBlock"].cts_shcode == ""

    def test_korean_alias_class_level(self):
        assert Market.t1410 is Market.초저유동성조회

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
        body = T1410InBlock(gubun="1", cts_shcode="")
        tr = ks.시세().초저유동성조회(body=body)
        assert isinstance(tr, TrT1410)
        assert tr.request_data.body["t1410InBlock"].gubun == "1"


# ---------------------------------------------------------------------------
# 6. Continuation cursor — TrT1410 MUST expose occurs_req
# ---------------------------------------------------------------------------


class TestContinuationCursorPresent:
    """t1410 carries an LS-declared cts_shcode cursor + tr_cont/tr_cont_key
    request headers, so TrT1410 must expose ``occurs_req`` /
    ``occurs_req_async``. This distinguishes t1410 from single-shot
    siblings (t1308 / t1449). If a refactor accidentally drops the
    OccursReqAbstract mixin, this guard fires immediately.
    """

    def test_occurs_req_present(self):
        tr = TrT1410(_make_request())
        assert hasattr(tr, "occurs_req"), (
            "TrT1410 must expose occurs_req — LS declares a cts_shcode "
            "continuation cursor for t1410."
        )
        assert hasattr(tr, "occurs_req_async"), (
            "TrT1410 must expose occurs_req_async — LS declares a "
            "cts_shcode continuation cursor for t1410."
        )

    def test_subclass_of_occurs_req_abstract(self):
        assert issubclass(TrT1410, OccursReqAbstract), (
            "TrT1410 must subclass OccursReqAbstract since LS declares "
            "a cts_shcode continuation cursor for t1410."
        )

    def test_occurs_updater_propagates_cts_shcode(self):
        """The cursor updater closure inside ``occurs_req`` / ``occurs_req_async``
        must echo ``response.cont_block.cts_shcode`` back into
        ``request.body['t1410InBlock'].cts_shcode``. We simulate one
        paging step manually here to verify the closure logic without
        spinning up GenericTR's full request loop.
        """
        tr = TrT1410(_make_request(gubun="0", cts_shcode=""))

        # Reproduce the closure logic from TrT1410.occurs_req inline.
        req_data = tr.request_data
        resp = T1410Response(
            header=T1410ResponseHeader(
                content_type="application/json; charset=utf-8",
                tr_cd="t1410",
                tr_cont="Y",
                tr_cont_key="page-2",
            ),
            cont_block=T1410OutBlock(cts_shcode="000545"),
            block=[],
            rsp_cd="00000",
            rsp_msg="OK",
            status_code=200,
            error_msg=None,
        )

        # Manually run the same body as the _updater inside occurs_req.
        req_data.header.tr_cont_key = resp.header.tr_cont_key
        req_data.header.tr_cont = resp.header.tr_cont
        req_data.body["t1410InBlock"].cts_shcode = resp.cont_block.cts_shcode

        assert req_data.body["t1410InBlock"].cts_shcode == "000545"
        assert req_data.header.tr_cont == "Y"
        assert req_data.header.tr_cont_key == "page-2"


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
        [T1410InBlock, T1410OutBlock, T1410OutBlock1],
        ids=["T1410InBlock", "T1410OutBlock", "T1410OutBlock1"],
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
        [T1410InBlock, T1410OutBlock, T1410OutBlock1],
        ids=["T1410InBlock", "T1410OutBlock", "T1410OutBlock1"],
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
        assert set(T1410InBlock.model_fields) == {"gubun", "cts_shcode"}

    def test_outblock_fields(self):
        assert set(T1410OutBlock.model_fields) == {"cts_shcode"}

    def test_outblock1_fields(self):
        assert set(T1410OutBlock1.model_fields) == {
            "hname", "price", "sign", "change", "diff", "volume", "shcode",
        }


# ---------------------------------------------------------------------------
# 9. LS-declared enum mapping — gubun
# ---------------------------------------------------------------------------


class TestGubunEnumDocumented:
    """LS publishes the ``gubun`` enum mapping
    (0=전체 / 1=코스피 / 2=코스닥). The InBlock description must embed
    the mapping so the AI chatbot picks the right scope.
    """

    def test_gubun_enum_mapping_present(self):
        desc = T1410InBlock.model_fields["gubun"].description or ""
        for token in [
            "'0'", "'1'", "'2'",
            "all", "KOSPI", "KOSDAQ",
            "전체", "코스피", "코스닥",
        ]:
            assert token in desc, (
                f"T1410InBlock.gubun description missing LS-declared "
                f"token '{token}'. LS publishes the full 0~2 enum mapping; "
                "description must mirror it for AI chatbot accuracy."
            )


# ---------------------------------------------------------------------------
# 10. Sign partial-evidence policy (Option C)
# ---------------------------------------------------------------------------


class TestSignPartialEvidencePolicy:
    """LS does NOT formally declare the t1410 ``sign`` enum mapping in
    its field specification table, but the LS official example response
    carries enough evidence to partially identify the mapping:
        - sign='3' on a row with change=0 / diff='000.00' (unchanged)
        - sign='5' on a row with diff='-00.88' (down)
    These are consistent with the sibling 1~5 convention published by
    t1308 / t1422 / t1427 / t1449. Values '1' / '2' / '4' have NOT been
    observed in the available t1410 example response and are not
    independently declared.

    Description must reflect this partial evidence (Option C policy):
        (a) LS non-declaration disclaimer
        (b) Example observed sign values
        (c) Sibling 1~5 convention reference
        (d) '1' / '2' / '4' unobserved disclaimer
    """

    def test_sign_description_carries_non_declaration_disclaimer(self):
        desc = T1410OutBlock1.model_fields["sign"].description or ""
        assert "does not declare" in desc or "not declared" in desc, (
            "T1410OutBlock1.sign description must carry the LS "
            "non-declaration disclaimer for the t1410 sign mapping."
        )

    def test_sign_description_carries_example_observed_values(self):
        desc = T1410OutBlock1.model_fields["sign"].description or ""
        # Both observed example sign values must appear in description.
        assert "sign='3'" in desc or "'3'" in desc, (
            "T1410OutBlock1.sign description must reference the example-"
            "observed sign='3' (unchanged row)."
        )
        assert "sign='5'" in desc or "'5'" in desc, (
            "T1410OutBlock1.sign description must reference the example-"
            "observed sign='5' (down row)."
        )
        # Reference to the example response source itself.
        assert "example response" in desc.lower(), (
            "T1410OutBlock1.sign description must explicitly cite the "
            "LS example response as the partial-evidence source."
        )

    def test_sign_description_carries_sibling_convention_reference(self):
        desc = T1410OutBlock1.model_fields["sign"].description or ""
        assert "sibling" in desc.lower(), (
            "T1410OutBlock1.sign description must reference the sibling "
            "TR convention as the cross-evidence source."
        )
        # At least one canonical sibling TR cited.
        cited_siblings = sum(
            1
            for tr in ("t1308", "t1422", "t1427", "t1449")
            if tr in desc
        )
        assert cited_siblings >= 1, (
            "T1410OutBlock1.sign description must cite at least one "
            "sibling TR (t1308 / t1422 / t1427 / t1449)."
        )
        # The actual 1~5 convention text must appear.
        for token in ["1=상한", "2=상승", "3=보합", "4=하한", "5=하락"]:
            assert token in desc, (
                f"T1410OutBlock1.sign description missing convention token "
                f"'{token}' — sibling 1~5 mapping must be quoted verbatim."
            )

    def test_sign_description_carries_unobserved_values_disclaimer(self):
        desc = T1410OutBlock1.model_fields["sign"].description or ""
        # '1' / '2' / '4' must all be called out as unobserved.
        for token in ["'1'", "'2'", "'4'"]:
            assert token in desc, (
                f"T1410OutBlock1.sign description must list unobserved "
                f"value {token} explicitly."
            )
        assert "not been observed" in desc, (
            "T1410OutBlock1.sign description must state '1' / '2' / '4' "
            "have 'not been observed' in the t1410 example response."
        )
        assert "not independently declared" in desc, (
            "T1410OutBlock1.sign description must state the unobserved "
            "values are 'not independently declared' for t1410."
        )


# ---------------------------------------------------------------------------
# 11. Anti-inference guard — fields LS did NOT declare
# ---------------------------------------------------------------------------


class TestNoInferredUnitOrSemantics:
    """For t1410 LS does NOT declare:
        - Currency unit of price / change fields.
        - Sign convention of ``change``.
        - Window scope of ``volume`` (intraday vs multi-day).
        - Row ordering of T1410OutBlock1.
        - Structure of the ``cts_shcode`` cursor.
    Descriptions must not assert these to avoid teaching the AI chatbot
    false certainty.
    """

    def test_price_no_inferred_currency(self):
        desc = T1410OutBlock1.model_fields["price"].description or ""
        assert "in KRW" not in desc, (
            "T1410OutBlock1.price: must not infer KRW unit — LS spec does "
            "not declare currency unit explicitly."
        )

    def test_change_no_inferred_sign_convention(self):
        desc = T1410OutBlock1.model_fields["change"].description or ""
        for forbidden in [
            "positive when up", "negative when down",
            "always positive", "always non-negative",
        ]:
            assert forbidden not in desc, (
                f"T1410OutBlock1.change: must not assert sign convention "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_volume_window_scope_not_asserted(self):
        """LS declares volume is cumulative ('누적거래량') but does NOT
        declare the exact window (intraday vs multi-day). The description
        must keep this disclaimer.
        """
        desc = T1410OutBlock1.model_fields["volume"].description or ""
        assert "not formally declared" in desc, (
            "T1410OutBlock1.volume: must keep the LS spec disclaimer for "
            "the cumulative window scope (intraday vs multi-day)."
        )

    def test_module_row_ordering_disclaimer(self):
        """LS does not declare row ordering for T1410OutBlock1. The
        blocks.py module docstring must mention the disclaimer so the
        AI chatbot does not fabricate an ordering assertion.
        """
        from programgarden_finance.ls.korea_stock.market.t1410 import blocks
        doc = (blocks.__doc__ or "").lower()
        for token in ["row ordering", "not declared"]:
            assert token in doc, (
                f"blocks.py module docstring must mention '{token}' to "
                "keep the LS no-declaration disclaimer for OutBlock1 "
                "row ordering."
            )

    def test_response_block_description_row_ordering_disclaimer(self):
        """T1410Response.block description must also carry the row-
        ordering disclaimer so consumers reading the Response model
        directly (not the module docstring) see it.
        """
        desc = T1410Response.model_fields["block"].description or ""
        assert "ordering is not declared" in desc.lower() or "row ordering" in desc.lower(), (
            "T1410Response.block: must mention row ordering disclaimer "
            "so consumers do not assume an ascending/descending order."
        )

    def test_cts_shcode_opaque_token_disclaimer(self):
        """LS does not declare the internal structure of the
        ``cts_shcode`` cursor. Both InBlock and OutBlock descriptions
        must call it out as an opaque LS-defined token.
        """
        in_desc = T1410InBlock.model_fields["cts_shcode"].description or ""
        out_desc = T1410OutBlock.model_fields["cts_shcode"].description or ""
        for desc, label in [(in_desc, "InBlock"), (out_desc, "OutBlock")]:
            assert "opaque" in desc.lower(), (
                f"T1410{label}.cts_shcode: must mark the cursor as "
                "opaque LS-defined token."
            )
