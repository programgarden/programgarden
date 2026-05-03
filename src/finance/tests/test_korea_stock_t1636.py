"""Unit tests for t1636 종목별 프로그램 매매동향 (Korea Stock Program Trading TR).

Covers:
    - blocks.py — Pydantic input/output validation, including the new
      `mkcap_cmpr_val` field added by LS on 2026-01-08.
    - TrT1636._build_response — happy / HTTP error / exception paths.
    - Program domain class — Korean alias bridge to TrT1636.
    - KoreaStock.program() entry point — Korean alias.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.program import Program
from programgarden_finance.ls.korea_stock.program.t1636 import TrT1636
from programgarden_finance.ls.korea_stock.program.t1636.blocks import (
    T1636InBlock,
    T1636OutBlock,
    T1636OutBlock1,
    T1636Request,
    T1636Response,
    T1636ResponseHeader,
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


def _make_request(**overrides: Any) -> T1636Request:
    body = T1636InBlock(
        gubun=overrides.pop("gubun", "0"),
        gubun1=overrides.pop("gubun1", "0"),
        gubun2=overrides.pop("gubun2", "0"),
        shcode=overrides.pop("shcode", "005930"),
        cts_idx=overrides.pop("cts_idx", 0),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1636Request(body={"t1636InBlock": body})


# ---------------------------------------------------------------------------
# 1. URL registration
# ---------------------------------------------------------------------------


class TestKOREAStockProgramURL:
    def test_program_url_exposed(self):
        assert URLS.KOREA_STOCK_PROGRAM_URL.endswith("/stock/program")
        assert URLS.KOREA_STOCK_PROGRAM_URL.startswith("https://")


# ---------------------------------------------------------------------------
# 2. blocks.py validation
# ---------------------------------------------------------------------------


class TestT1636InBlock:
    def test_valid_minimal(self):
        block = T1636InBlock(gubun="0", gubun1="0", gubun2="0", shcode="005930")
        assert block.gubun == "0"
        assert block.cts_idx == 0
        assert block.exchgubun == "K"

    @pytest.mark.parametrize("gubun", ["0", "1"])
    @pytest.mark.parametrize("gubun1", ["0", "1"])
    @pytest.mark.parametrize("gubun2", ["0", "1", "2", "3", "4"])
    @pytest.mark.parametrize("exchgubun", ["K", "N", "U"])
    def test_valid_literal_combos(self, gubun, gubun1, gubun2, exchgubun):
        block = T1636InBlock(
            gubun=gubun,
            gubun1=gubun1,
            gubun2=gubun2,
            shcode="005930",
            exchgubun=exchgubun,
        )
        assert block.gubun == gubun
        assert block.gubun1 == gubun1
        assert block.gubun2 == gubun2
        assert block.exchgubun == exchgubun

    @pytest.mark.parametrize(
        "field,bad_value",
        [
            ("gubun", "2"),
            ("gubun1", "X"),
            ("gubun2", "5"),
            ("exchgubun", "Z"),
        ],
    )
    def test_invalid_literal_rejected(self, field, bad_value):
        kwargs = dict(gubun="0", gubun1="0", gubun2="0", shcode="005930", exchgubun="K")
        kwargs[field] = bad_value
        with pytest.raises(ValidationError):
            T1636InBlock(**kwargs)


class TestT1636OutBlock1MkcapCmprVal:
    """Regression guard for the LS 2026-01-08 schema update."""

    def test_field_present_in_schema(self):
        assert "mkcap_cmpr_val" in T1636OutBlock1.model_fields

    def test_default_is_zero_float(self):
        out = T1636OutBlock1()
        assert out.mkcap_cmpr_val == 0.0
        assert isinstance(out.mkcap_cmpr_val, float)

    def test_decodes_provided_value(self):
        out = T1636OutBlock1.model_validate({
            "rank": 1,
            "hname": "삼성전자",
            "price": 70000,
            "diff": 1.23,
            "rate": 12.5,
            "shcode": "005930",
            "mkcap_cmpr_val": 4.56,
        })
        assert out.mkcap_cmpr_val == pytest.approx(4.56)
        assert out.diff == pytest.approx(1.23)
        assert out.rate == pytest.approx(12.5)


class TestT1636OutBlock:
    def test_cts_idx_default_zero(self):
        out = T1636OutBlock()
        assert out.cts_idx == 0

    def test_cts_idx_decodes(self):
        out = T1636OutBlock.model_validate({"cts_idx": 42})
        assert out.cts_idx == 42


class TestT1636Response:
    def test_full_response_validates(self):
        resp = T1636Response(
            header=None,
            cont_block=T1636OutBlock(cts_idx=10),
            block=[
                T1636OutBlock1(rank=1, hname="A", mkcap_cmpr_val=1.5),
                T1636OutBlock1(rank=2, hname="B", mkcap_cmpr_val=-2.0),
            ],
            rsp_cd="00000",
            rsp_msg="OK",
            status_code=200,
            error_msg=None,
        )
        assert resp.cont_block is not None
        assert resp.cont_block.cts_idx == 10
        assert len(resp.block) == 2
        assert resp.block[1].mkcap_cmpr_val == -2.0


# ---------------------------------------------------------------------------
# 3. TrT1636._build_response
# ---------------------------------------------------------------------------


class TestTrT1636BuildResponse:
    def _make_tr(self) -> TrT1636:
        return TrT1636(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_json: Dict[str, Any] = {
            "t1636OutBlock": {"cts_idx": 7},
            "t1636OutBlock1": [
                {
                    "rank": 1,
                    "hname": "삼성전자",
                    "price": 70000,
                    "sign": "2",
                    "change": 100,
                    "diff": 0.14,
                    "volume": 100000,
                    "svalue": 1000,
                    "offervalue": 800,
                    "stksvalue": 200,
                    "svolume": 10,
                    "offervolume": 8,
                    "stksvolume": 2,
                    "sgta": 99999999,
                    "rate": 12.34,
                    "shcode": "005930",
                    "ex_shcode": "005930",
                    "mkcap_cmpr_val": 5.67,
                }
            ],
            "rsp_cd": "00000",
            "rsp_msg": "정상처리",
        }
        resp_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1636",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, resp_json, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.cont_block is not None
        assert result.cont_block.cts_idx == 7
        assert len(result.block) == 1
        assert result.block[0].mkcap_cmpr_val == pytest.approx(5.67)
        assert result.block[0].hname == "삼성전자"
        assert result.header is not None
        assert isinstance(result.header, T1636ResponseHeader)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json; charset=utf-8", "tr_cd": "t1636"},
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
# 4. Program domain class
# ---------------------------------------------------------------------------


class TestProgramDomain:
    def test_t1636_returns_tr_instance(self):
        tm = _make_token_manager()
        program = Program(token_manager=tm)
        body = T1636InBlock(gubun="0", gubun1="0", gubun2="0", shcode="005930")
        tr = program.t1636(body=body)
        assert isinstance(tr, TrT1636)
        # body is wrapped in t1636InBlock
        assert tr.request_data.body["t1636InBlock"].shcode == "005930"

    def test_korean_alias_class_level(self):
        # Class-level: alias must reference the SAME function object (Korean alias contract).
        assert Program.t1636 is Program.종목별프로그램매매동향

    def test_token_manager_required(self):
        with pytest.raises(ValueError):
            Program(token_manager=None)


# ---------------------------------------------------------------------------
# 5. KoreaStock entry point
# ---------------------------------------------------------------------------


class TestKoreaStockProgramEntry:
    def test_program_returns_program_instance(self):
        tm = _make_token_manager()
        ks = KoreaStock(tm)
        assert isinstance(ks.program(), Program)

    def test_korean_alias_class_level(self):
        assert KoreaStock.program is KoreaStock.프로그램매매

    def test_chained_call_korean_alias(self):
        tm = _make_token_manager()
        ks = KoreaStock(tm)
        body = T1636InBlock(gubun="1", gubun1="1", gubun2="1", shcode="000660")
        tr = ks.프로그램매매().종목별프로그램매매동향(body=body)
        assert isinstance(tr, TrT1636)
        assert tr.request_data.body["t1636InBlock"].gubun == "1"
        assert tr.request_data.body["t1636InBlock"].shcode == "000660"


# ---------------------------------------------------------------------------
# 6. occurs_req cts_idx auto-paging (mocked GenericTR)
# ---------------------------------------------------------------------------


class TestTrT1636OccursReqUpdater:
    """Verify the cts_idx updater closure feeds the next request correctly.

    We don't drive a real GenericTR loop — we just call the inner _updater
    directly with a mock response and confirm the request body is mutated.
    """

    def test_updater_propagates_cts_idx(self):
        tr = TrT1636(_make_request())

        # capture _updater by intercepting GenericTR.occurs_req
        captured = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        # Build a fake response with a continuation cts_idx
        resp = T1636Response(
            header=T1636ResponseHeader(
                content_type="application/json",
                tr_cd="t1636",
                tr_cont="Y",
                tr_cont_key="next-key",
            ),
            cont_block=T1636OutBlock(cts_idx=99),
            block=[],
        )
        updater(tr.request_data, resp)

        assert tr.request_data.header.tr_cont_key == "next-key"
        assert tr.request_data.header.tr_cont == "Y"
        assert tr.request_data.body["t1636InBlock"].cts_idx == 99

    def test_updater_raises_on_missing_continuation(self):
        tr = TrT1636(_make_request())
        captured = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        updater = captured["updater"]

        resp = T1636Response(header=None, cont_block=None, block=[])
        with pytest.raises(ValueError, match="missing continuation"):
            updater(tr.request_data, resp)


# ---------------------------------------------------------------------------
# 7. Field(examples=[...]) regression guard
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
        [T1636InBlock, T1636OutBlock, T1636OutBlock1],
        ids=["T1636InBlock", "T1636OutBlock", "T1636OutBlock1"],
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
        [T1636InBlock, T1636OutBlock1],
        ids=["T1636InBlock", "T1636OutBlock1"],
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


# ===========================================================================
# Anti-inference guard (Phase A2 correction): description must NOT carry
# units (KRW / shares) or arithmetic identities not declared by xingAPI.
# ===========================================================================


class TestNoInferredUnits:
    """xingAPI FUNCTION_MAP does not declare currency/quantity units or
    arithmetic identities for these fields. The AI chatbot ingests
    description verbatim, so any inferred unit ("in KRW" / "in shares")
    or identity claim ("svalue = stksvalue - offervalue") would degrade
    workflow generation accuracy.
    """

    @pytest.mark.parametrize(
        "field_name",
        [
            "price", "change", "volume",
            "svalue", "offervalue", "stksvalue",
            "svolume", "offervolume", "stksvolume",
        ],
    )
    def test_t1636_no_inferred_unit_in_description(self, field_name: str):
        desc = T1636OutBlock1.model_fields[field_name].description or ""
        assert "in KRW" not in desc, (
            f"T1636OutBlock1.{field_name}: description must not infer KRW unit."
        )
        assert "in shares" not in desc, (
            f"T1636OutBlock1.{field_name}: description must not infer shares unit."
        )

    @pytest.mark.parametrize("field_name", ["svalue", "svolume"])
    def test_t1636_no_arithmetic_identity_in_description(self, field_name: str):
        desc = T1636OutBlock1.model_fields[field_name].description or ""
        assert "Identity:" not in desc, (
            f"T1636OutBlock1.{field_name}: description must not assert an "
            "arithmetic identity (xingAPI FUNCTION_MAP declares none)."
        )
        assert "stksvalue - offervalue" not in desc, (
            f"T1636OutBlock1.{field_name}: must not embed svalue identity."
        )
        assert "stksvolume - offervolume" not in desc, (
            f"T1636OutBlock1.{field_name}: must not embed svolume identity."
        )

    def test_t1636_outblock1_docstring_has_no_arithmetic_identity(self):
        doc = T1636OutBlock1.__doc__ or ""
        assert "stksvalue - offervalue" not in doc, (
            "T1636OutBlock1 docstring must not assert svalue arithmetic identity."
        )
        assert "Identity:" not in doc, (
            "T1636OutBlock1 docstring must not declare LS-undocumented identity."
        )


# ===========================================================================
# Phase A3 — sgta / mkcap_cmpr_val / sign anti-inference guards
# ===========================================================================


class TestNoInferredEnumOrUnit:
    """xingAPI FUNCTION_MAP declares no currency unit for ``sgta`` (long, 15),
    no arithmetic between ``mkcap_cmpr_val`` and (``svalue``, ``sgta``), and
    no enum mapping for ``sign`` (char, 1). The AI chatbot ingests the
    description verbatim, so embedding inferred '억 원' units, identity
    formulas, or sign enums (e.g., '1' = upper limit) would degrade workflow
    generation accuracy.
    """

    def test_t1636_sgta_no_inferred_unit(self):
        desc = T1636OutBlock1.model_fields["sgta"].description or ""
        assert "Empirically observed" not in desc, (
            "T1636OutBlock1.sgta: must not include 'Empirically observed' wording."
        )
        assert "억 원" not in desc, (
            "T1636OutBlock1.sgta: must not infer 억 원 unit."
        )
        assert "100M KRW" not in desc, (
            "T1636OutBlock1.sgta: must not infer 100M KRW unit."
        )

    def test_t1636_mkcap_cmpr_val_no_arithmetic_inference(self):
        desc = T1636OutBlock1.model_fields["mkcap_cmpr_val"].description or ""
        assert "svalue" not in desc, (
            "T1636OutBlock1.mkcap_cmpr_val: must not reference svalue identity."
        )
        assert "sgta" not in desc, (
            "T1636OutBlock1.mkcap_cmpr_val: must not reference sgta identity."
        )
        assert "in %" not in desc, (
            "T1636OutBlock1.mkcap_cmpr_val: must not infer % unit."
        )

    def test_t1636_sign_no_inferred_enum_mapping(self):
        desc = T1636OutBlock1.model_fields["sign"].description or ""
        for forbidden in [
            "limit-up", "limit-down",
            "upper limit", "lower limit",
            "상한", "하한", "상승", "하락",
        ]:
            assert forbidden not in desc, (
                f"T1636OutBlock1.sign: must not embed inferred enum token '{forbidden}'."
            )
