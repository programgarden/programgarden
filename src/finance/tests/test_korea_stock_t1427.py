"""Unit tests for t1427 상/하한가직전 (Korea Stock Approaching-Limit TR).

Covers:
    - blocks.py — Pydantic input/output validation, including LS official
      example response round-trip.
    - TrT1427._build_response — happy / HTTP error / exception paths.
    - Market domain class — Korean alias bridge to TrT1427.
    - KoreaStock chained call — ``ks.시세().상하한가직전(...)`` Korean alias path.
    - occurs_req updater — verifies that ``idx`` cursor transfers from
      OutBlock back into InBlock for paged calls.
    - Field(examples=[...]) regression guards — examples present + types
      validate against declared annotations.
    - LS-declared bit map — ``jc_num`` description must embed the
      LS-published exclusion-bit constants.
    - LS-declared sign enum — ``OutBlock1.sign`` description must embed
      the 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락 mapping.
    - Anti-inference guard — fields LS did NOT declare (currency unit,
      change sign convention, ``lmtdaycnt`` counting window, ``rate``
      reference base, row ordering) must not embed inferred assertions.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.market import Market
from programgarden_finance.ls.korea_stock.market.t1427 import TrT1427
from programgarden_finance.ls.korea_stock.market.t1427.blocks import (
    T1427InBlock,
    T1427OutBlock,
    T1427OutBlock1,
    T1427Request,
    T1427Response,
    T1427ResponseHeader,
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


def _make_request(**overrides: Any) -> T1427Request:
    body = T1427InBlock(
        qrygb=overrides.pop("qrygb", "1"),
        gubun=overrides.pop("gubun", "0"),
        signgubun=overrides.pop("signgubun", "1"),
        diff=overrides.pop("diff", 0),
        jc_num=overrides.pop("jc_num", 0),
        sprice=overrides.pop("sprice", 0),
        eprice=overrides.pop("eprice", 0),
        volume=overrides.pop("volume", 0),
        idx=overrides.pop("idx", 0),
        jshex=overrides.pop("jshex", "c"),
    )
    return T1427Request(body={"t1427InBlock": body})


# LS official example response (user-supplied).
_LS_OFFICIAL_RESPONSE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1427OutBlock": {"cnt": 2447, "idx": 20},
    "t1427OutBlock1": [
        {
            "diff_vol": "0001456.56",
            "lmtdaycnt": 0,
            "change": 319,
            "shcode": "328380",
            "sign": "2",
            "diff": "026.34",
            "lmtprice": 1574,
            "volume": 30556301,
            "high": 1572,
            "total": 524,
            "rate": "-00000002.80",
            "low": 1251,
            "price": 1530,
            "jnilvolume": 1963072,
            "value": 44062,
            "hname": "솔트웨어",
            "open": 1251,
        },
        {
            "diff_vol": "0000101.36",
            "lmtdaycnt": 0,
            "change": 295,
            "shcode": "377630",
            "sign": "2",
            "diff": "007.31",
            "lmtprice": 5240,
            "volume": 202798,
            "high": 4330,
            "total": 174,
            "rate": "-00000017.37",
            "low": 4030,
            "price": 4330,
            "jnilvolume": 100713,
            "value": 855,
            "hname": "삼성스팩4호",
            "open": 4100,
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


class TestT1427InBlock:
    def test_valid_minimal(self):
        block = T1427InBlock(
            qrygb="1", gubun="0", signgubun="1",
        )
        assert block.qrygb == "1"
        assert block.gubun == "0"
        assert block.signgubun == "1"
        assert block.diff == 0
        assert block.jc_num == 0
        assert block.sprice == 0
        assert block.eprice == 0
        assert block.volume == 0
        assert block.idx == 0
        assert block.jshex == ""

    def test_valid_full_filters(self):
        block = T1427InBlock(
            qrygb="1", gubun="1", signgubun="2",
            diff=5, jc_num=384, sprice=1000, eprice=100000,
            volume=10000, idx=20, jshex="c",
        )
        assert block.qrygb == "1"
        assert block.gubun == "1"
        assert block.signgubun == "2"
        assert block.diff == 5
        assert block.jc_num == 384
        assert block.sprice == 1000
        assert block.eprice == 100000
        assert block.volume == 10000
        assert block.idx == 20
        assert block.jshex == "c"

    def test_invalid_gubun_rejected(self):
        with pytest.raises(ValidationError):
            T1427InBlock(qrygb="1", gubun="9", signgubun="1")

    def test_invalid_signgubun_rejected(self):
        with pytest.raises(ValidationError):
            T1427InBlock(qrygb="1", gubun="0", signgubun="3")


class TestT1427OutBlock:
    def test_decodes_cnt_and_idx(self):
        out = T1427OutBlock.model_validate({"cnt": 2447, "idx": 20})
        assert out.cnt == 2447
        assert out.idx == 20

    def test_zero_idx_terminates_pagination(self):
        out = T1427OutBlock.model_validate({"cnt": 0, "idx": 0})
        assert out.cnt == 0
        assert out.idx == 0

    def test_idx_required(self):
        with pytest.raises(ValidationError):
            T1427OutBlock.model_validate({"cnt": 0})


class TestT1427OutBlock1:
    def test_decodes_ls_official_first_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1427OutBlock1"][0]
        out = T1427OutBlock1.model_validate(row)
        assert out.hname == "솔트웨어"
        assert out.shcode == "328380"
        assert out.price == 1530
        assert out.sign == "2"
        assert out.change == 319
        assert out.diff == pytest.approx(26.34)
        assert isinstance(out.diff, float)
        assert out.volume == 30556301
        assert out.diff_vol == pytest.approx(1456.56)
        assert isinstance(out.diff_vol, float)
        assert out.lmtprice == 1574
        assert out.rate == pytest.approx(-2.80)
        assert isinstance(out.rate, float)
        assert out.jnilvolume == 1963072
        assert out.open == 1251
        assert out.high == 1572
        assert out.low == 1251
        assert out.lmtdaycnt == 0
        assert out.value == 44062
        assert out.total == 524

    def test_decodes_ls_official_second_row(self):
        row = _LS_OFFICIAL_RESPONSE["t1427OutBlock1"][1]
        out = T1427OutBlock1.model_validate(row)
        assert out.hname == "삼성스팩4호"
        assert out.shcode == "377630"
        assert out.price == 4330
        assert out.sign == "2"
        assert out.change == 295
        assert out.diff == pytest.approx(7.31)
        assert out.diff_vol == pytest.approx(101.36)
        assert out.rate == pytest.approx(-17.37)
        assert out.lmtprice == 5240

    def test_change_accepts_negative(self):
        out = T1427OutBlock1.model_validate({"change": -319})
        assert out.change == -319

    def test_diff_accepts_negative_string(self):
        out = T1427OutBlock1.model_validate({"diff": "-026.34"})
        assert out.diff == pytest.approx(-26.34)

    def test_defaults_when_missing(self):
        out = T1427OutBlock1()
        assert out.hname == ""
        assert out.shcode == ""
        assert out.price == 0
        assert out.sign == ""
        assert out.change == 0
        assert out.diff == 0.0
        assert out.volume == 0
        assert out.diff_vol == 0.0
        assert out.lmtprice == 0
        assert out.rate == 0.0
        assert out.jnilvolume == 0
        assert out.open == 0
        assert out.high == 0
        assert out.low == 0
        assert out.lmtdaycnt == 0
        assert out.value == 0
        assert out.total == 0


class TestT1427LSExampleResponseRoundTrip:
    """Regression guard — full LS official example response must round-trip
    through the entire response envelope without ValidationError.
    """

    def test_full_envelope_validates(self):
        rows = _LS_OFFICIAL_RESPONSE["t1427OutBlock1"]
        cont = _LS_OFFICIAL_RESPONSE["t1427OutBlock"]

        resp = T1427Response(
            header=None,
            cont_block=T1427OutBlock.model_validate(cont),
            block=[T1427OutBlock1.model_validate(r) for r in rows],
            rsp_cd=_LS_OFFICIAL_RESPONSE["rsp_cd"],
            rsp_msg=_LS_OFFICIAL_RESPONSE["rsp_msg"],
            status_code=200,
            error_msg=None,
        )

        assert resp.cont_block is not None
        assert resp.cont_block.cnt == 2447
        assert resp.cont_block.idx == 20
        assert len(resp.block) == 2
        assert resp.block[0].shcode == "328380"
        assert resp.block[1].shcode == "377630"
        assert resp.rsp_cd == "00000"


# ---------------------------------------------------------------------------
# 3. TrT1427._build_response
# ---------------------------------------------------------------------------


class TestTrT1427BuildResponse:
    def _make_tr(self) -> TrT1427:
        return TrT1427(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1427",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, _LS_OFFICIAL_RESPONSE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.cont_block is not None
        assert result.cont_block.cnt == 2447
        assert result.cont_block.idx == 20
        assert len(result.block) == 2
        assert result.block[0].shcode == "328380"
        assert result.block[1].shcode == "377630"
        assert result.header is not None
        assert isinstance(result.header, T1427ResponseHeader)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1427"},
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
    def test_t1427_returns_tr_instance(self):
        tm = _make_token_manager()
        market = Market(token_manager=tm)
        body = T1427InBlock(
            qrygb="1", gubun="0", signgubun="1",
        )
        tr = market.t1427(body=body)
        assert isinstance(tr, TrT1427)
        assert tr.request_data.body["t1427InBlock"].qrygb == "1"
        assert tr.request_data.body["t1427InBlock"].signgubun == "1"

    def test_korean_alias_class_level(self):
        assert Market.t1427 is Market.상하한가직전

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
        body = T1427InBlock(
            qrygb="1", gubun="1", signgubun="2", jshex="c",
        )
        tr = ks.시세().상하한가직전(body=body)
        assert isinstance(tr, TrT1427)
        assert tr.request_data.body["t1427InBlock"].gubun == "1"
        assert tr.request_data.body["t1427InBlock"].signgubun == "2"
        assert tr.request_data.body["t1427InBlock"].jshex == "c"


# ---------------------------------------------------------------------------
# 6. occurs_req updater — idx propagation
# ---------------------------------------------------------------------------


class TestTrT1427OccursReqUpdater:
    """Verify that the occurs_req updater closure feeds ``idx`` from the
    previous response's cont_block back into the next request's
    ``T1427InBlock.idx``. Missing this would cause an infinite loop.
    """

    def test_updater_propagates_idx(self):
        tr = TrT1427(_make_request())

        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1427Response(
            header=T1427ResponseHeader(
                content_type="application/json",
                tr_cd="t1427",
                tr_cont="Y",
                tr_cont_key="next-key",
            ),
            cont_block=T1427OutBlock(cnt=2447, idx=20),
            block=[],
            rsp_cd="00000",
            rsp_msg="OK",
        )
        updater(tr.request_data, resp)

        assert tr.request_data.header.tr_cont_key == "next-key"
        assert tr.request_data.header.tr_cont == "Y"
        assert tr.request_data.body["t1427InBlock"].idx == 20

    def test_updater_raises_on_missing_continuation(self):
        tr = TrT1427(_make_request())
        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1427Response(
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
        [T1427InBlock, T1427OutBlock, T1427OutBlock1],
        ids=["T1427InBlock", "T1427OutBlock", "T1427OutBlock1"],
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
        [T1427InBlock, T1427OutBlock1],
        ids=["T1427InBlock", "T1427OutBlock1"],
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
        assert set(T1427InBlock.model_fields) == {
            "qrygb", "gubun", "signgubun", "diff", "jc_num",
            "sprice", "eprice", "volume", "idx", "jshex",
        }

    def test_outblock_fields(self):
        assert set(T1427OutBlock.model_fields) == {"cnt", "idx"}

    def test_outblock1_fields(self):
        expected = {
            "hname", "price", "sign", "change", "diff", "volume",
            "diff_vol", "lmtprice", "rate", "shcode", "jnilvolume",
            "open", "high", "low", "lmtdaycnt", "value", "total",
        }
        assert set(T1427OutBlock1.model_fields) == expected


# ---------------------------------------------------------------------------
# 9. LS-declared bitmap — jc_num description documents the published bits
# ---------------------------------------------------------------------------


class TestJcNumBitMapDocumented:
    """For t1427 LS publishes the ``jc_num`` exclusion bitmap
    (0x00000080 관리종목, 0x00000100 시장경보, etc.). The description must
    embed the bit constants so the AI chatbot can generate correct filters.
    """

    def test_jc_num_bits_present(self):
        desc = T1427InBlock.model_fields["jc_num"].description or ""
        for token in [
            "0x00000080", "관리종목",
            "0x00000100", "시장경보",
            "0x00000200", "거래정지",
            "0x00004000", "우선주",
            "0x01000000", "정리매매",
            "0x80000000", "불성실공시",
        ]:
            assert token in desc, (
                f"T1427InBlock.jc_num description missing LS-declared token "
                f"'{token}'. LS publishes the exclusion bitmap; description "
                f"must mirror it for AI chatbot accuracy."
            )


# ---------------------------------------------------------------------------
# 10. Anti-inference guard — fields LS did NOT declare
# ---------------------------------------------------------------------------


class TestOutputSignEnumDeclared:
    """For t1427 LS declares the OutBlock1.sign enum mapping
    (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락). The description must
    embed the mapping so the AI chatbot can interpret sign values.
    """

    def test_output_sign_enum_mapping_present(self):
        desc = T1427OutBlock1.model_fields["sign"].description or ""
        for token in [
            "'1' = upper limit", "상한",
            "'2' = up", "상승",
            "'3' = unchanged", "보합",
            "'4' = lower limit", "하한",
            "'5' = down", "하락",
        ]:
            assert token in desc, (
                f"T1427OutBlock1.sign description missing LS-declared "
                f"enum token '{token}'. LS publishes the 1~5 mapping; "
                f"description must mirror it for AI chatbot accuracy."
            )


class TestNoInferredUnitOrSemantics:
    """For t1427 LS does NOT declare:
        - Currency unit of price / lmtprice / change / open / high / low
        - Sign convention of change
        - ``lmtdaycnt`` (연속) counting window
        - ``rate`` (대비율) reference base
        - Row ordering within OutBlock1
    Descriptions must not assert these to avoid teaching the AI chatbot
    false certainty.
    """

    def test_price_no_inferred_currency(self):
        desc = T1427OutBlock1.model_fields["price"].description or ""
        assert "in KRW" not in desc, (
            "T1427OutBlock1.price: must not infer KRW unit — LS spec does "
            "not declare currency unit explicitly."
        )

    def test_change_no_inferred_sign_convention(self):
        desc = T1427OutBlock1.model_fields["change"].description or ""
        for forbidden in [
            "positive when up", "negative when down",
            "always positive", "always non-negative",
        ]:
            assert forbidden not in desc, (
                f"T1427OutBlock1.change: must not assert sign convention "
                f"'{forbidden}' — LS spec does not declare it."
            )

    def test_lmtdaycnt_no_inferred_counting_window(self):
        desc = T1427OutBlock1.model_fields["lmtdaycnt"].description or ""
        assert "not declared" in desc, (
            "T1427OutBlock1.lmtdaycnt: must keep the LS-no-declaration "
            "disclaimer for the consecutive-day counting window."
        )

    def test_rate_no_inferred_reference_base(self):
        desc = T1427OutBlock1.model_fields["rate"].description or ""
        assert "not declared" in desc, (
            "T1427OutBlock1.rate: must keep the LS-no-declaration "
            "disclaimer for the comparison-rate reference base."
        )

    def test_module_row_ordering_disclaimer(self):
        """LS does not declare row ordering within ``t1427OutBlock1``. The
        blocks.py module docstring must keep that disclaimer so the AI
        chatbot does not fabricate an ordering assumption.
        """
        from programgarden_finance.ls.korea_stock.market.t1427 import blocks
        doc = (blocks.__doc__ or "").lower()
        for token in ["row ordering", "not declared"]:
            assert token in doc, (
                f"blocks.py module docstring must mention '{token}' to keep "
                "the LS no-declaration disclaimer for row ordering within "
                "OutBlock1."
            )
