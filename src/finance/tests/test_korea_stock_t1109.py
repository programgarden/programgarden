"""Unit tests for t1109 시간외체결량 (Korea Stock Off-hours Execution Volume TR).

Covers:
    - blocks.py — Pydantic input/output validation, including LS official
      example response round-trip.
    - TrT1109._build_response — happy / HTTP error / exception paths.
    - Market domain class — Korean alias bridge to TrT1109.
    - KoreaStock chained call — ``ks.시세().시간외체결량(...)`` Korean alias path.
    - occurs_req updater — verifies that ``dan_chetime`` + ``idx`` pair
      both transfer from OutBlock back into InBlock for paged calls.
    - Field(examples=[...]) regression guards — examples present + types
      validate against declared annotations.
    - Anti-inference guard — ``dan_sign`` description must not embed an
      LS-undocumented enum mapping.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.market import Market
from programgarden_finance.ls.korea_stock.market.t1109 import TrT1109
from programgarden_finance.ls.korea_stock.market.t1109.blocks import (
    T1109InBlock,
    T1109OutBlock,
    T1109OutBlock1,
    T1109Request,
    T1109Response,
    T1109ResponseHeader,
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


def _make_request(**overrides: Any) -> T1109Request:
    body = T1109InBlock(
        shcode=overrides.pop("shcode", "005930"),
        dan_chetime=overrides.pop("dan_chetime", ""),
        idx=overrides.pop("idx", 0),
    )
    return T1109Request(body={"t1109InBlock": body})


# LS official example response (from the user-supplied spec).
_LS_OFFICIAL_RESPONSE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1109OutBlock": {
        "ctsshcode": "",
        "idx": 0,
        "ctschetime": "",
    },
    "t1109OutBlock1": [
        {"chdegree": "000000.00", "dan_volume": 1791, "dan_chetime": "1800300943",
         "dan_change": 0, "diff": "000.00", "dan_cvolume": 500, "dan_sign": "3", "dan_price": 3660},
        {"chdegree": "000000.00", "dan_volume": 1291, "dan_chetime": "1750307180",
         "dan_change": 0, "diff": "000.00", "dan_cvolume": 1002, "dan_sign": "3", "dan_price": 3660},
        {"chdegree": "000000.00", "dan_volume": 289, "dan_chetime": "1730305708",
         "dan_change": 0, "diff": "000.00", "dan_cvolume": 1, "dan_sign": "3", "dan_price": 3660},
        {"chdegree": "000000.00", "dan_volume": 288, "dan_chetime": "1700308255",
         "dan_change": 0, "diff": "000.00", "dan_cvolume": 147, "dan_sign": "3", "dan_price": 3660},
        {"chdegree": "000000.00", "dan_volume": 141, "dan_chetime": "1640306509",
         "dan_change": 5, "diff": "000.14", "dan_cvolume": 27, "dan_sign": "2", "dan_price": 3665},
        {"chdegree": "000000.00", "dan_volume": 114, "dan_chetime": "1630297536",
         "dan_change": 5, "diff": "000.14", "dan_cvolume": 12, "dan_sign": "2", "dan_price": 3665},
        {"chdegree": "000000.00", "dan_volume": 102, "dan_chetime": "1620305084",
         "dan_change": 15, "diff": "000.41", "dan_cvolume": 100, "dan_sign": "2", "dan_price": 3675},
        {"chdegree": "000000.00", "dan_volume": 2, "dan_chetime": "1610309356",
         "dan_change": 15, "diff": "-00.41", "dan_cvolume": 2, "dan_sign": "5", "dan_price": 3645},
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


class TestT1109InBlock:
    def test_valid_minimal(self):
        block = T1109InBlock(shcode="005930")
        assert block.shcode == "005930"
        assert block.dan_chetime == ""
        assert block.idx == 0

    def test_valid_with_continuation_cursor(self):
        block = T1109InBlock(shcode="001200", dan_chetime="1640306509", idx=312)
        assert block.shcode == "001200"
        assert block.dan_chetime == "1640306509"
        assert block.idx == 312


class TestT1109OutBlock:
    def test_defaults(self):
        out = T1109OutBlock()
        assert out.ctsshcode == ""
        assert out.ctschetime == ""
        assert out.idx == 0

    def test_decodes_continuation_payload(self):
        out = T1109OutBlock.model_validate({
            "ctsshcode": "005930",
            "ctschetime": "1610309356",
            "idx": 312,
        })
        assert out.ctsshcode == "005930"
        assert out.ctschetime == "1610309356"
        assert out.idx == 312

    def test_decodes_empty_terminal_payload(self):
        out = T1109OutBlock.model_validate({
            "ctsshcode": "",
            "ctschetime": "",
            "idx": 0,
        })
        assert out.ctsshcode == ""
        assert out.idx == 0


class TestT1109OutBlock1:
    def test_decodes_ls_official_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1109OutBlock1"][4]
        out = T1109OutBlock1.model_validate(row)
        assert out.dan_chetime == "1640306509"
        assert out.dan_price == 3665
        assert out.dan_sign == "2"
        assert out.dan_change == 5
        assert out.diff == pytest.approx(0.14)
        assert isinstance(out.diff, float)
        assert out.dan_cvolume == 27
        assert out.chdegree == 0.0
        assert isinstance(out.chdegree, float)
        assert out.dan_volume == 141

    def test_diff_string_negative_coerces(self):
        row = _LS_OFFICIAL_RESPONSE["t1109OutBlock1"][7]
        out = T1109OutBlock1.model_validate(row)
        assert out.diff == pytest.approx(-0.41)
        assert out.dan_sign == "5"

    def test_defaults_when_missing(self):
        out = T1109OutBlock1()
        assert out.dan_chetime == ""
        assert out.dan_price == 0
        assert out.dan_sign == ""
        assert out.dan_change == 0
        assert out.diff == 0.0
        assert out.dan_cvolume == 0
        assert out.chdegree == 0.0
        assert out.dan_volume == 0


class TestT1109LSExampleResponseRoundTrip:
    """Regression guard #4 — full LS official example response must round-trip
    through the entire response envelope without ValidationError.
    """

    def test_full_envelope_validates(self):
        rows = _LS_OFFICIAL_RESPONSE["t1109OutBlock1"]
        cont = _LS_OFFICIAL_RESPONSE["t1109OutBlock"]

        resp = T1109Response(
            header=None,
            cont_block=T1109OutBlock.model_validate(cont),
            block=[T1109OutBlock1.model_validate(r) for r in rows],
            rsp_cd=_LS_OFFICIAL_RESPONSE["rsp_cd"],
            rsp_msg=_LS_OFFICIAL_RESPONSE["rsp_msg"],
            status_code=200,
            error_msg=None,
        )

        assert resp.cont_block is not None
        assert resp.cont_block.idx == 0
        assert len(resp.block) == 8
        # Time ordering preserved verbatim from LS — first row is the latest trade
        assert resp.block[0].dan_chetime == "1800300943"
        assert resp.block[-1].dan_chetime == "1610309356"
        assert resp.rsp_cd == "00000"


# ---------------------------------------------------------------------------
# 3. TrT1109._build_response
# ---------------------------------------------------------------------------


class TestTrT1109BuildResponse:
    def _make_tr(self) -> TrT1109:
        return TrT1109(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1109",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, _LS_OFFICIAL_RESPONSE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.cont_block is not None
        assert result.cont_block.idx == 0
        assert len(result.block) == 8
        assert result.block[4].dan_price == 3665
        assert result.header is not None
        assert isinstance(result.header, T1109ResponseHeader)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1109"},
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
    def test_t1109_returns_tr_instance(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        body = T1109InBlock(shcode="005930")
        tr = market.t1109(body=body)
        assert isinstance(tr, TrT1109)
        assert tr.request_data.body["t1109InBlock"].shcode == "005930"

    def test_korean_alias_class_level(self):
        # Class-level: alias must reference the SAME function object.
        assert Market.t1109 is Market.시간외체결량

    def test_token_manager_required(self):
        with pytest.raises(ValueError):
            Market(token_manager=None)


# ---------------------------------------------------------------------------
# 5. KoreaStock entry point
# ---------------------------------------------------------------------------


class TestKoreaStockMarketEntry:
    def test_market_returns_market_instance(self):
        tm = _make_token_manager()
        ks = KoreaStock(tm)
        assert isinstance(ks.market(), Market)

    def test_korean_alias_class_level(self):
        assert KoreaStock.market is KoreaStock.시세

    def test_chained_call_korean_alias(self):
        tm = _make_token_manager()
        ks = KoreaStock(tm)
        body = T1109InBlock(shcode="001200")
        tr = ks.시세().시간외체결량(body=body)
        assert isinstance(tr, TrT1109)
        assert tr.request_data.body["t1109InBlock"].shcode == "001200"


# ---------------------------------------------------------------------------
# 6. occurs_req updater — dan_chetime + idx pair propagation
# ---------------------------------------------------------------------------


class TestTrT1109OccursReqUpdater:
    """Verify that the occurs_req updater closure feeds BOTH ``dan_chetime``
    AND ``idx`` from the previous response's cont_block back into the next
    request's InBlock. Missing either would cause an infinite loop or a
    missed page.
    """

    def test_updater_propagates_both_pair_fields(self):
        tr = TrT1109(_make_request())

        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1109Response(
            header=T1109ResponseHeader(
                content_type="application/json",
                tr_cd="t1109",
                tr_cont="Y",
                tr_cont_key="next-key",
            ),
            cont_block=T1109OutBlock(
                ctsshcode="005930",
                ctschetime="1610309356",
                idx=312,
            ),
            block=[],
            rsp_cd="00000",
            rsp_msg="OK",
        )
        updater(tr.request_data, resp)

        assert tr.request_data.header.tr_cont_key == "next-key"
        assert tr.request_data.header.tr_cont == "Y"
        assert tr.request_data.body["t1109InBlock"].dan_chetime == "1610309356"
        assert tr.request_data.body["t1109InBlock"].idx == 312

    def test_updater_raises_on_missing_continuation(self):
        tr = TrT1109(_make_request())
        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1109Response(
            header=None, cont_block=None, block=[], rsp_cd="", rsp_msg=""
        )
        with pytest.raises(ValueError, match="missing continuation"):
            updater(tr.request_data, resp)


# ---------------------------------------------------------------------------
# 7. Field(examples=[...]) regression guard
# ---------------------------------------------------------------------------


class TestFieldExamplesValidate:
    """Each value declared in ``Field(examples=[...])`` must round-trip through
    ``TypeAdapter(<annotation>).validate_python(value)``. AI chatbots learn
    from these; an example with a wrong type or wrong Literal value silently
    teaches bad input.
    """

    @pytest.mark.parametrize(
        "model_cls",
        [T1109InBlock, T1109OutBlock, T1109OutBlock1],
        ids=["T1109InBlock", "T1109OutBlock", "T1109OutBlock1"],
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
        [T1109InBlock, T1109OutBlock1],
        ids=["T1109InBlock", "T1109OutBlock1"],
    )
    def test_every_field_has_examples(self, model_cls: Type[BaseModel]):
        """Every public field in user-facing blocks must declare at least one
        example so the JSON schema carries usable AI hints."""
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
        assert set(T1109InBlock.model_fields) == {"shcode", "dan_chetime", "idx"}

    def test_outblock_fields(self):
        assert set(T1109OutBlock.model_fields) == {"ctsshcode", "ctschetime", "idx"}

    def test_outblock1_fields(self):
        expected = {
            "dan_chetime",
            "dan_price",
            "dan_sign",
            "dan_change",
            "diff",
            "dan_cvolume",
            "chdegree",
            "dan_volume",
        }
        assert set(T1109OutBlock1.model_fields) == expected


# ---------------------------------------------------------------------------
# 9. Anti-inference guard — dan_sign / dan_chetime descriptions
# ---------------------------------------------------------------------------


class TestNoInferredEnumOrUnit:
    """LS spec for t1109 declares no enum mapping for ``dan_sign``, no
    currency unit for ``dan_price`` / ``dan_change``, and no formal time
    format for ``dan_chetime``. The AI chatbot ingests descriptions
    verbatim — embedding inferred mappings/units would degrade workflow
    generation accuracy.
    """

    def test_dan_sign_no_inferred_enum_mapping(self):
        desc = T1109OutBlock1.model_fields["dan_sign"].description or ""
        for forbidden in [
            "limit-up", "limit-down",
            "upper limit", "lower limit",
            "상한", "하한", "상승", "하락",
            "= up", "= down",
        ]:
            assert forbidden not in desc, (
                f"T1109OutBlock1.dan_sign: must not embed inferred enum token "
                f"'{forbidden}' — LS spec for t1109 declares none."
            )

    def test_dan_price_no_inferred_currency(self):
        desc = T1109OutBlock1.model_fields["dan_price"].description or ""
        assert "in KRW" not in desc, (
            "T1109OutBlock1.dan_price: must not infer KRW unit — "
            "LS spec does not declare currency unit explicitly."
        )

    def test_dan_change_no_inferred_currency(self):
        desc = T1109OutBlock1.model_fields["dan_change"].description or ""
        assert "in KRW" not in desc, (
            "T1109OutBlock1.dan_change: must not infer KRW unit."
        )

    def test_dan_chetime_format_disclaimer_present(self):
        """The dan_chetime description observes ``HHMMSS`` + 4-digit suffix
        but must keep the LS-formal-spec disclaimer to honour the
        no-inference policy.
        """
        desc = T1109OutBlock1.model_fields["dan_chetime"].description or ""
        assert "not formally declared" in desc, (
            "T1109OutBlock1.dan_chetime: must keep the LS spec disclaimer "
            "since the suffix unit is not officially declared."
        )
        assert "HHMMSS" in desc, (
            "T1109OutBlock1.dan_chetime: should document the observed "
            "HHMMSS prefix structure for AI chatbot guidance."
        )
