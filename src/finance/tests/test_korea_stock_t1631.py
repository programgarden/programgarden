"""Unit tests for t1631 프로그램매매종합조회 (Korea Stock Program Trading Comprehensive Query).

Covers:
    - blocks.py — Pydantic input/output validation. Crucial regression:
      ``gubun`` Literal is ``"1"/"2"`` (not ``"0"/"1"`` like t1636).
    - TrT1631._build_response — happy / HTTP error / exception paths,
      verified against the LS official example payload.
    - Field(examples=[...]) regression guards — all example values must
      validate through ``TypeAdapter(field_info.annotation)`` and every
      InBlock/OutBlock/OutBlock1 field must declare at least one example.
    - OccursReqAbstract NON-inheritance guard — t1631 has no IDXCTS
      continuation, so this is a hard regression boundary against t1636.
    - Field-set silent rename guard — explicit set comparison on
      ``model_fields.keys()`` flags any LS schema drift.
    - Program domain class + KoreaStock entry point — Korean alias bridge
      and chained call.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.program import Program
from programgarden_finance.ls.korea_stock.program.t1631 import TrT1631
from programgarden_finance.ls.korea_stock.program.t1631.blocks import (
    T1631InBlock,
    T1631OutBlock,
    T1631OutBlock1,
    T1631Request,
    T1631Response,
    T1631ResponseHeader,
)
from programgarden_finance.ls.token_manager import TokenManager
from programgarden_finance.ls.tr_base import OccursReqAbstract, TRRequestAbstract


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_token_manager() -> TokenManager:
    tm = TokenManager()
    tm.access_token = "stub-access-token"
    tm.token_type = "Bearer"
    return tm


def _make_request(**overrides: Any) -> T1631Request:
    body = T1631InBlock(
        gubun=overrides.pop("gubun", "1"),
        dgubun=overrides.pop("dgubun", "1"),
        sdate=overrides.pop("sdate", ""),
        edate=overrides.pop("edate", ""),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1631Request(body={"t1631InBlock": body})


# ---------------------------------------------------------------------------
# LS official example payload (used as fixed regression baseline)
# ---------------------------------------------------------------------------


LS_OFFICIAL_EXAMPLE: Dict[str, Any] = {
    "t1631OutBlock1": [
        {"bidvolume": 102, "volume": 99, "bidvalue": 6919, "offervalue": 479, "value": 6440, "offervolume": 3},
        {"bidvolume": 0, "volume": 0, "bidvalue": 1, "offervalue": 1, "value": 1, "offervolume": 0},
        {"bidvolume": 102, "volume": 99, "bidvalue": 6921, "offervalue": 480, "value": 6441, "offervolume": 3},
    ],
    "t1631OutBlock": {
        "tcdrem": 0,
        "cdhrem": 0,
        "tbdrem": 5,
        "bshrem": 149,
        "cshrem": 0,
        "tbsrem": 251,
        "bdhrem": 2,
        "tcsrem": 0,
    },
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
}


# ---------------------------------------------------------------------------
# 1. URL registration
# ---------------------------------------------------------------------------


class TestKoreaStockProgramURL:
    def test_program_url_shared_with_t1636(self):
        # Both t1631 and t1636 live under /stock/program — verify the
        # constant is reused (no duplicate URL constant).
        assert URLS.KOREA_STOCK_PROGRAM_URL.endswith("/stock/program")
        assert URLS.KOREA_STOCK_PROGRAM_URL.startswith("https://")


# ---------------------------------------------------------------------------
# 2. T1631InBlock validation — Critical regression: gubun "1"/"2" vs t1636 "0"/"1"
# ---------------------------------------------------------------------------


class TestT1631InBlock:
    def test_valid_minimal(self):
        block = T1631InBlock(gubun="1", dgubun="1")
        assert block.gubun == "1"
        assert block.dgubun == "1"
        assert block.sdate == ""
        assert block.edate == ""
        assert block.exchgubun == "K"  # default

    @pytest.mark.parametrize("gubun", ["1", "2"])
    @pytest.mark.parametrize("dgubun", ["1", "2"])
    @pytest.mark.parametrize("exchgubun", ["K", "N", "U"])
    def test_valid_literal_combos(self, gubun, dgubun, exchgubun):
        block = T1631InBlock(
            gubun=gubun,
            dgubun=dgubun,
            sdate="20260415",
            edate="20260502",
            exchgubun=exchgubun,
        )
        assert block.gubun == gubun
        assert block.dgubun == dgubun
        assert block.exchgubun == exchgubun

    @pytest.mark.parametrize(
        "field,bad_value",
        [
            # gubun "0" rejected — t1636 accepts "0" for the same market
            # dimension but t1631 does not. Critical anti-copy-paste
            # regression: the gubun encodings differ between the two TRs.
            ("gubun", "0"),
            ("gubun", "3"),
            ("dgubun", "0"),
            ("dgubun", "3"),
            ("exchgubun", "Z"),
            ("exchgubun", "K1"),
        ],
    )
    def test_invalid_literal_rejected(self, field, bad_value):
        kwargs = dict(gubun="1", dgubun="1", sdate="", edate="", exchgubun="K")
        kwargs[field] = bad_value
        with pytest.raises(ValidationError):
            T1631InBlock(**kwargs)

    def test_empty_dates_allowed_for_same_day(self):
        """LS official example uses empty sdate/edate when dgubun='1' (same-day)."""
        block = T1631InBlock(gubun="1", dgubun="1", sdate="", edate="", exchgubun="K")
        assert block.sdate == ""
        assert block.edate == ""

    def test_period_dates_accepted(self):
        block = T1631InBlock(
            gubun="2", dgubun="2", sdate="20260101", edate="20260502", exchgubun="U"
        )
        assert block.sdate == "20260101"
        assert block.edate == "20260502"


# ---------------------------------------------------------------------------
# 3. OutBlock / OutBlock1 — silent rename regression guards
# ---------------------------------------------------------------------------


class TestT1631OutBlockFields:
    """Explicit set comparison — flags LS silent field rename / add / remove."""

    def test_outblock_required_fields(self):
        expected = {
            "cdhrem", "bdhrem", "tcdrem", "tbdrem",
            "cshrem", "bshrem", "tcsrem", "tbsrem",
        }
        assert set(T1631OutBlock.model_fields.keys()) == expected

    def test_outblock1_required_fields(self):
        expected = {"offervolume", "offervalue", "bidvolume", "bidvalue", "volume", "value"}
        assert set(T1631OutBlock1.model_fields.keys()) == expected

    def test_outblock_defaults_zero(self):
        out = T1631OutBlock()
        for name in T1631OutBlock.model_fields:
            assert getattr(out, name) == 0

    def test_outblock1_defaults_zero(self):
        out = T1631OutBlock1()
        for name in T1631OutBlock1.model_fields:
            assert getattr(out, name) == 0

    def test_outblock_decodes_ls_example(self):
        out = T1631OutBlock.model_validate(LS_OFFICIAL_EXAMPLE["t1631OutBlock"])
        assert out.cdhrem == 0
        assert out.bdhrem == 2
        assert out.tcdrem == 0
        assert out.tbdrem == 5
        assert out.cshrem == 0
        assert out.bshrem == 149
        assert out.tcsrem == 0
        assert out.tbsrem == 251

    def test_outblock1_decodes_ls_example_row0(self):
        row = T1631OutBlock1.model_validate(LS_OFFICIAL_EXAMPLE["t1631OutBlock1"][0])
        assert row.offervolume == 3
        assert row.offervalue == 479
        assert row.bidvolume == 102
        assert row.bidvalue == 6919
        assert row.volume == 99
        assert row.value == 6440

    def test_outblock1_row1_exact_ls_example_mapping(self):
        """Regression guard: lock LS official example row1 dict mapping exactly.

        The LS public spec does not document a server-side computation
        formula for ``value`` / ``volume`` — every field is consumed as
        reported by LS. This test pins the LS official example values
        for row1 verbatim so any LS schema drift fails immediately.
        """
        row = T1631OutBlock1.model_validate(LS_OFFICIAL_EXAMPLE["t1631OutBlock1"][1])
        assert row.offervolume == 0
        assert row.offervalue == 1
        assert row.bidvolume == 0
        assert row.bidvalue == 1
        assert row.volume == 0
        assert row.value == 1


# ---------------------------------------------------------------------------
# 4. T1631Response shape (summary_block + block)
# ---------------------------------------------------------------------------


class TestT1631Response:
    def test_full_response_validates(self):
        resp = T1631Response(
            header=None,
            summary_block=T1631OutBlock(cdhrem=10, bdhrem=20),
            block=[
                T1631OutBlock1(volume=100, value=200_000),
                T1631OutBlock1(volume=-50, value=-25_000),
            ],
            rsp_cd="00000",
            rsp_msg="OK",
            status_code=200,
            error_msg=None,
        )
        assert resp.summary_block is not None
        assert resp.summary_block.cdhrem == 10
        assert len(resp.block) == 2
        assert resp.block[1].value == -25_000

    def test_response_uses_summary_block_not_cont_block(self):
        """Regression: t1631 must expose ``summary_block``, NOT ``cont_block``.

        Unlike t1636, the t1631 OutBlock carries actual data (market-wide
        order/remainder aggregates) — it is not a continuation marker. Mis-naming
        this field would mislead downstream consumers.
        """
        assert "summary_block" in T1631Response.model_fields
        assert "cont_block" not in T1631Response.model_fields


# ---------------------------------------------------------------------------
# 5. TrT1631._build_response — happy path against LS official example
# ---------------------------------------------------------------------------


class TestTrT1631BuildResponse:
    def _make_tr(self) -> TrT1631:
        return TrT1631(_make_request())

    def test_happy_path_matches_ls_official_example(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1631",
            "tr_cont": "N",
            "tr_cont_key": "",
        }
        result = tr._build_response(resp_obj, LS_OFFICIAL_EXAMPLE, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.rsp_msg == "정상적으로 조회가 완료되었습니다."
        assert result.header is not None
        assert isinstance(result.header, T1631ResponseHeader)

        # summary_block exact mapping (8 scalar fields)
        s = result.summary_block
        assert s is not None
        assert (s.cdhrem, s.bdhrem, s.tcdrem, s.tbdrem) == (0, 2, 0, 5)
        assert (s.cshrem, s.bshrem, s.tcsrem, s.tbsrem) == (0, 149, 0, 251)

        # block: 3 rows, exact LS-reported mapping
        assert len(result.block) == 3
        row0, row1, row2 = result.block

        assert (row0.offervolume, row0.offervalue) == (3, 479)
        assert (row0.bidvolume, row0.bidvalue) == (102, 6919)
        assert (row0.volume, row0.value) == (99, 6440)

        assert (row1.offervolume, row1.offervalue) == (0, 1)
        assert (row1.bidvolume, row1.bidvalue) == (0, 1)
        assert (row1.volume, row1.value) == (0, 1)  # NOT 0 — LS reports 1

        assert (row2.offervolume, row2.offervalue) == (3, 480)
        assert (row2.bidvolume, row2.bidvalue) == (102, 6921)
        assert (row2.volume, row2.value) == (99, 6441)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json", "tr_cd": "t1631"},
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

    def test_ls_level_error_with_200_status(self):
        """rsp_cd != '00000' but HTTP 200 — error message preserved without overwriting status."""
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        result = tr._build_response(
            resp_obj,
            {"rsp_cd": "IGW00121", "rsp_msg": "거래 시간이 아닙니다."},
            {"Content-Type": "application/json", "tr_cd": "t1631", "tr_cont": "N", "tr_cont_key": ""},
            None,
        )
        assert result.status_code == 200
        assert result.error_msg is None  # build_response only sets error_msg on HTTP >= 400 or exception
        assert result.rsp_cd == "IGW00121"
        assert result.rsp_msg == "거래 시간이 아닙니다."


# ---------------------------------------------------------------------------
# 6. OccursReqAbstract non-inheritance — t1631 has NO continuation
# ---------------------------------------------------------------------------


class TestTrT1631NoOccursReq:
    """Critical regression: t1631 must not expose continuation paging.

    LS spec for t1631 has no IDXCTS / cts_idx field. Accidentally inheriting
    OccursReqAbstract or defining occurs_req would create a bogus paging
    surface that would silently never advance.
    """

    def test_inherits_tr_request_abstract(self):
        tr = TrT1631(_make_request())
        assert isinstance(tr, TRRequestAbstract)

    def test_does_not_inherit_occurs_req_abstract(self):
        tr = TrT1631(_make_request())
        assert not isinstance(tr, OccursReqAbstract)

    def test_no_occurs_req_method(self):
        tr = TrT1631(_make_request())
        assert not hasattr(tr, "occurs_req")
        assert not hasattr(tr, "occurs_req_async")

    def test_class_does_not_inherit_occurs_req(self):
        # Verify the inheritance is declared correctly at the class level too.
        assert not issubclass(TrT1631, OccursReqAbstract)


# ---------------------------------------------------------------------------
# 7. Program domain class — Korean alias bridge
# ---------------------------------------------------------------------------


class TestProgramDomain:
    def test_t1631_returns_tr_instance(self):
        tm = _make_token_manager()
        program = Program(token_manager=tm)
        body = T1631InBlock(gubun="1", dgubun="1")
        tr = program.t1631(body=body)
        assert isinstance(tr, TrT1631)
        assert tr.request_data.body["t1631InBlock"].gubun == "1"

    def test_korean_alias_class_level(self):
        # Class-level: alias must reference the SAME function object.
        assert Program.t1631 is Program.프로그램매매종합조회

    def test_t1636_alias_still_intact(self):
        """Adding t1631 must not break the existing t1636 alias."""
        assert Program.t1636 is Program.종목별프로그램매매동향


# ---------------------------------------------------------------------------
# 8. KoreaStock entry point — full chained call
# ---------------------------------------------------------------------------


class TestKoreaStockProgramEntry:
    def test_chained_call_korean_alias(self):
        tm = _make_token_manager()
        ks = KoreaStock(tm)
        body = T1631InBlock(gubun="2", dgubun="2", sdate="20260415", edate="20260502", exchgubun="K")
        tr = ks.프로그램매매().프로그램매매종합조회(body=body)
        assert isinstance(tr, TrT1631)
        b = tr.request_data.body["t1631InBlock"]
        assert b.gubun == "2"
        assert b.dgubun == "2"
        assert b.sdate == "20260415"
        assert b.edate == "20260502"

    def test_top_level_module_export(self):
        """``from programgarden_finance import t1631`` exposes the InBlock."""
        from programgarden_finance import t1631 as top_t1631

        assert hasattr(top_t1631, "T1631InBlock")
        assert hasattr(top_t1631, "T1631Request")
        assert hasattr(top_t1631, "TrT1631")


# ---------------------------------------------------------------------------
# 9. Field(examples=[...]) regression guards (CLAUDE.md AI-chatbot policy)
# ---------------------------------------------------------------------------


class TestFieldExamplesValidate:
    """Each value declared in ``Field(examples=[...])`` must round-trip through
    ``TypeAdapter(<annotation>).validate_python(value)``.

    Why: AI chatbots read these examples from ``model_json_schema()`` and
    learn from them. A typo or wrong type in an example silently teaches the
    chatbot bad input. This guard fails fast if any example value diverges
    from its field's declared type / Literal set.
    """

    @pytest.mark.parametrize(
        "model_cls",
        [T1631InBlock, T1631OutBlock, T1631OutBlock1],
        ids=["T1631InBlock", "T1631OutBlock", "T1631OutBlock1"],
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
        [T1631InBlock, T1631OutBlock, T1631OutBlock1],
        ids=["T1631InBlock", "T1631OutBlock", "T1631OutBlock1"],
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
            "All InBlock / OutBlock / OutBlock1 fields must carry AI-readable examples."
        )


class TestInBlockCharLengthConsistency:
    """xingAPI FUNCTION_MAP: char,1 fields must declare ``Length 1``.

    AI chatbot consumes the description verbatim. Inconsistent length
    documentation across sibling program TRs (some declare ``Length 8``
    for date fields, some omit ``Length 1`` for char,1 enums) produces
    drift in workflow JSON generation. xingAPI ground truth declares
    every InBlock char,1 field as ``char,1`` — the description must
    surface that explicitly.
    """

    @pytest.mark.parametrize("field_name", ["gubun", "dgubun", "exchgubun"])
    def test_t1631_inblock_char_one_length_documented(self, field_name: str):
        desc = T1631InBlock.model_fields[field_name].description or ""
        assert "Length 1" in desc, (
            f"T1631InBlock.{field_name} must document 'Length 1' "
            f"(xingAPI FUNCTION_MAP: char,1)."
        )
