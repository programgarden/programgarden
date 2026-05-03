"""Unit tests for t1637 종목별프로그램매매추이 (Per-Symbol Program-Trading Time Series TR).

Covers:
    - blocks.py — Pydantic input/output validation, including the gubun2-aware
      cursor-mode signaling and the cts_idx=9999 chart-marker default.
    - TrT1637._build_response — happy / HTTP error / exception paths.
    - TrT1637.occurs_req — gubun2-aware cursor branching (time vs date),
      empty block guard, missing header guard.
    - Program domain class — Korean alias bridge to TrT1637.
    - KoreaStock.program() entry point — Korean alias.
    - Field(examples=[...]) regression guard.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.program import Program
from programgarden_finance.ls.korea_stock.program.t1637 import TrT1637
from programgarden_finance.ls.korea_stock.program.t1637.blocks import (
    T1637InBlock,
    T1637OutBlock,
    T1637OutBlock1,
    T1637Request,
    T1637Response,
    T1637ResponseHeader,
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


def _make_request(**overrides: Any) -> T1637Request:
    body = T1637InBlock(
        gubun1=overrides.pop("gubun1", "0"),
        gubun2=overrides.pop("gubun2", "0"),
        shcode=overrides.pop("shcode", "005930"),
        date=overrides.pop("date", ""),
        time=overrides.pop("time", ""),
        cts_idx=overrides.pop("cts_idx", 9999),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1637Request(body={"t1637InBlock": body})


# ---------------------------------------------------------------------------
# 1. URL registration (sanity check — same endpoint as t1636)
# ---------------------------------------------------------------------------


class TestKOREAStockProgramURL:
    def test_program_url_exposed(self):
        assert URLS.KOREA_STOCK_PROGRAM_URL.endswith("/stock/program")
        assert URLS.KOREA_STOCK_PROGRAM_URL.startswith("https://")


# ---------------------------------------------------------------------------
# 2. blocks.py — InBlock validation
# ---------------------------------------------------------------------------


class TestT1637InBlock:
    def test_valid_minimal(self):
        block = T1637InBlock(gubun1="0", gubun2="0", shcode="005930")
        assert block.gubun1 == "0"
        assert block.gubun2 == "0"
        assert block.shcode == "005930"
        assert block.date == ""
        assert block.time == ""
        assert block.cts_idx == 9999
        assert block.exchgubun == "K"

    def test_cts_idx_default_is_9999(self):
        """User-confirmed: cts_idx default is 9999 (chart marker, fixed by spec)."""
        block = T1637InBlock(gubun1="0", gubun2="0", shcode="005930")
        assert block.cts_idx == 9999

    def test_exchgubun_default_is_K(self):
        block = T1637InBlock(gubun1="0", gubun2="0", shcode="005930")
        assert block.exchgubun == "K"

    @pytest.mark.parametrize("gubun1", ["0", "1"])
    @pytest.mark.parametrize("gubun2", ["0", "1"])
    @pytest.mark.parametrize("exchgubun", ["K", "N", "U"])
    def test_valid_literal_combos(self, gubun1, gubun2, exchgubun):
        block = T1637InBlock(
            gubun1=gubun1,
            gubun2=gubun2,
            shcode="005930",
            exchgubun=exchgubun,
        )
        assert block.gubun1 == gubun1
        assert block.gubun2 == gubun2
        assert block.exchgubun == exchgubun

    @pytest.mark.parametrize(
        "field,bad_value",
        [
            ("gubun1", "2"),
            ("gubun2", "2"),
            ("exchgubun", "Z"),
        ],
    )
    def test_invalid_literal_rejected(self, field, bad_value):
        kwargs = dict(gubun1="0", gubun2="0", shcode="005930", exchgubun="K")
        kwargs[field] = bad_value
        with pytest.raises(ValidationError):
            T1637InBlock(**kwargs)


# ---------------------------------------------------------------------------
# 3. blocks.py — OutBlock (cts_idx echo) validation
# ---------------------------------------------------------------------------


class TestT1637OutBlockEcho:
    def test_cts_idx_default_zero(self):
        out = T1637OutBlock()
        assert out.cts_idx == 0

    def test_cts_idx_decodes_chart_marker(self):
        out = T1637OutBlock.model_validate({"cts_idx": 9999})
        assert out.cts_idx == 9999

    def test_cts_idx_decodes_zero_echo(self):
        """LS official example response shows cts_idx=0 in OutBlock even when
        request used 9999 (echo behavior is not strict per LS spec)."""
        out = T1637OutBlock.model_validate({"cts_idx": 0})
        assert out.cts_idx == 0


# ---------------------------------------------------------------------------
# 4. blocks.py — OutBlock1 row decode (LS official example payload)
# ---------------------------------------------------------------------------


class TestT1637OutBlock1:
    def test_decodes_ls_example_response_row(self):
        """Verify decode of the LS official example response row (positive svalue)."""
        row = T1637OutBlock1.model_validate({
            "date": "20230605",
            "time": "102700",
            "price": 3685,
            "sign": "",
            "change": 0,
            "diff": "0",
            "volume": 0,
            "svalue": 188914,
            "offervalue": 0,
            "stksvalue": 0,
            "svolume": 49935,
            "offervolume": 0,
            "stksvolume": 0,
            "shcode": "A00120",
            "ex_shcode": "",
        })
        assert row.date == "20230605"
        assert row.time == "102700"
        assert row.price == 3685
        assert row.svalue == 188914
        assert row.svolume == 49935
        assert row.diff == pytest.approx(0.0)
        assert isinstance(row.diff, float)
        assert row.shcode == "A00120"

    def test_decodes_negative_net_buy_row(self):
        """LS example response second row has negative svalue (net sell)."""
        row = T1637OutBlock1.model_validate({
            "date": "20230605",
            "time": "090100",
            "price": 3645,
            "svalue": -74311,
            "svolume": -20307,
            "diff": "0",
        })
        assert row.svalue == -74311
        assert row.svolume == -20307

    def test_diff_string_coerces_to_float(self):
        row = T1637OutBlock1.model_validate({"diff": "-0.27"})
        assert row.diff == pytest.approx(-0.27)
        assert isinstance(row.diff, float)


# ---------------------------------------------------------------------------
# 5. blocks.py — Response envelope
# ---------------------------------------------------------------------------


class TestT1637Response:
    def test_full_response_validates(self):
        resp = T1637Response(
            header=None,
            cont_block=T1637OutBlock(cts_idx=0),
            block=[
                T1637OutBlock1(date="20230605", time="102700", svalue=188914),
                T1637OutBlock1(date="20230605", time="090100", svalue=-74311),
            ],
            rsp_cd="00000",
            rsp_msg="조회완료",
            status_code=200,
            error_msg=None,
        )
        assert resp.cont_block is not None
        assert resp.cont_block.cts_idx == 0
        assert len(resp.block) == 2
        assert resp.block[0].svalue == 188914
        assert resp.block[1].svalue == -74311


# ---------------------------------------------------------------------------
# 6. TrT1637._build_response
# ---------------------------------------------------------------------------


class TestTrT1637BuildResponse:
    def _make_tr(self) -> TrT1637:
        return TrT1637(_make_request())

    def test_happy_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        resp_json: Dict[str, Any] = {
            "t1637OutBlock": {"cts_idx": 0},
            "t1637OutBlock1": [
                {
                    "date": "20230605",
                    "time": "102700",
                    "price": 3685,
                    "sign": "",
                    "change": 0,
                    "diff": "0",
                    "volume": 0,
                    "svalue": 188914,
                    "offervalue": 0,
                    "stksvalue": 0,
                    "svolume": 49935,
                    "offervolume": 0,
                    "stksvolume": 0,
                    "shcode": "A00120",
                    "ex_shcode": "",
                }
            ],
            "rsp_cd": "00000",
            "rsp_msg": "조회완료",
        }
        resp_headers = {
            "content_type": "application/json; charset=utf-8",
            "tr_cd": "t1637",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

        result = tr._build_response(resp_obj, resp_json, resp_headers, None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.cont_block is not None
        assert result.cont_block.cts_idx == 0
        assert len(result.block) == 1
        assert result.block[0].svalue == 188914
        assert result.block[0].svolume == 49935
        assert result.header is not None
        assert isinstance(result.header, T1637ResponseHeader)

    def test_http_error_status(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"content_type": "application/json; charset=utf-8", "tr_cd": "t1637"},
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
# 7. Program domain class
# ---------------------------------------------------------------------------


class TestProgramDomain:
    def test_t1637_returns_tr_instance(self):
        tm = _make_token_manager()
        program = Program(token_manager=tm)
        body = T1637InBlock(gubun1="0", gubun2="0", shcode="005930")
        tr = program.t1637(body=body)
        assert isinstance(tr, TrT1637)
        assert tr.request_data.body["t1637InBlock"].shcode == "005930"
        assert tr.request_data.body["t1637InBlock"].cts_idx == 9999

    def test_korean_alias_class_level(self):
        assert Program.t1637 is Program.종목별프로그램매매추이

    def test_alias_does_not_collide_with_t1636(self):
        """t1636 alias = 종목별프로그램매매동향, t1637 alias = 종목별프로그램매매추이.
        Distinct LS-spec Korean names — must remain distinct attributes."""
        assert Program.종목별프로그램매매동향 is not Program.종목별프로그램매매추이


# ---------------------------------------------------------------------------
# 8. KoreaStock entry point
# ---------------------------------------------------------------------------


class TestKoreaStockProgramEntry:
    def test_chained_call_korean_alias(self):
        tm = _make_token_manager()
        ks = KoreaStock(tm)
        body = T1637InBlock(gubun1="1", gubun2="1", shcode="000660", date="20260502")
        tr = ks.프로그램매매().종목별프로그램매매추이(body=body)
        assert isinstance(tr, TrT1637)
        assert tr.request_data.body["t1637InBlock"].gubun2 == "1"
        assert tr.request_data.body["t1637InBlock"].shcode == "000660"
        assert tr.request_data.body["t1637InBlock"].date == "20260502"


# ---------------------------------------------------------------------------
# 9. occurs_req gubun2-aware cursor (CRITICAL — t1637 novel logic)
# ---------------------------------------------------------------------------


class TestTrT1637OccursReqUpdater:
    """Verify the gubun2-aware cursor updater closure feeds the next request.

    Per LS spec: gubun2='0' (time mode) advances InBlock.time; gubun2='1'
    (daily mode) advances InBlock.date — both from the LAST row of the
    previous response's OutBlock1.

    We don't drive a real GenericTR loop — we just call the inner _updater
    directly with a mock response and confirm the request body is mutated
    correctly per the gubun2 mode.
    """

    @staticmethod
    def _capture_updater(tr: TrT1637):
        captured: Dict[str, Any] = {}

        def fake_occurs_req(updater, callback=None, delay=1):
            captured["updater"] = updater
            return []

        tr._generic.occurs_req = fake_occurs_req  # type: ignore[assignment]
        tr.occurs_req()
        return captured["updater"]

    def test_updater_uses_time_cursor_when_gubun2_is_0(self):
        """gubun2='0' (time mode) → InBlock.time advances from last row's time;
        InBlock.date is left unchanged."""
        tr = TrT1637(_make_request(gubun2="0"))
        updater = self._capture_updater(tr)

        resp = T1637Response(
            header=T1637ResponseHeader(
                content_type="application/json",
                tr_cd="t1637",
                tr_cont="Y",
                tr_cont_key="next-key",
            ),
            cont_block=T1637OutBlock(cts_idx=0),
            block=[
                T1637OutBlock1(date="20260503", time="093000"),
                T1637OutBlock1(date="20260503", time="091500"),
            ],
        )
        updater(tr.request_data, resp)

        in_block = tr.request_data.body["t1637InBlock"]
        assert in_block.time == "091500"  # last row's time
        assert in_block.date == ""  # unchanged
        assert tr.request_data.header.tr_cont_key == "next-key"
        assert tr.request_data.header.tr_cont == "Y"

    def test_updater_uses_date_cursor_when_gubun2_is_1(self):
        """gubun2='1' (daily mode) → InBlock.date advances from last row's date;
        InBlock.time is left unchanged."""
        tr = TrT1637(_make_request(gubun2="1"))
        updater = self._capture_updater(tr)

        resp = T1637Response(
            header=T1637ResponseHeader(
                content_type="application/json",
                tr_cd="t1637",
                tr_cont="Y",
                tr_cont_key="next-key",
            ),
            cont_block=T1637OutBlock(cts_idx=0),
            block=[
                T1637OutBlock1(date="20260503", time="093000"),
                T1637OutBlock1(date="20260502", time="153000"),
            ],
        )
        updater(tr.request_data, resp)

        in_block = tr.request_data.body["t1637InBlock"]
        assert in_block.date == "20260502"  # last row's date
        assert in_block.time == ""  # unchanged
        assert tr.request_data.header.tr_cont_key == "next-key"
        assert tr.request_data.header.tr_cont == "Y"

    def test_updater_raises_on_empty_block(self):
        """Empty OutBlock1 list → ValueError (cannot extract cursor seed)."""
        tr = TrT1637(_make_request(gubun2="0"))
        updater = self._capture_updater(tr)

        resp = T1637Response(
            header=T1637ResponseHeader(
                content_type="application/json",
                tr_cd="t1637",
                tr_cont="Y",
                tr_cont_key="next-key",
            ),
            cont_block=T1637OutBlock(cts_idx=0),
            block=[],
        )
        with pytest.raises(ValueError, match="OutBlock1 rows"):
            updater(tr.request_data, resp)

    def test_updater_raises_on_missing_header(self):
        """Missing response header → ValueError (cannot propagate tr_cont)."""
        tr = TrT1637(_make_request(gubun2="0"))
        updater = self._capture_updater(tr)

        resp = T1637Response(header=None, cont_block=None, block=[])
        with pytest.raises(ValueError, match="continuation header"):
            updater(tr.request_data, resp)


# ---------------------------------------------------------------------------
# 10. Field(examples=[...]) regression guard
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
        [T1637InBlock, T1637OutBlock, T1637OutBlock1],
        ids=["T1637InBlock", "T1637OutBlock", "T1637OutBlock1"],
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
        [T1637InBlock, T1637OutBlock1],
        ids=["T1637InBlock", "T1637OutBlock1"],
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
# units (KRW / shares) or sibling-TR identity references not declared by xingAPI.
# ===========================================================================


class TestNoInferredUnits:
    """xingAPI FUNCTION_MAP does not declare currency/quantity units, and
    cross-referencing the t1636 sibling TR for an identity claim is itself
    inference. The AI chatbot ingests description verbatim — any inferred
    unit ("in KRW" / "in shares") or sibling-TR hedge would degrade
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
    def test_t1637_no_inferred_unit_in_description(self, field_name: str):
        desc = T1637OutBlock1.model_fields[field_name].description or ""
        assert "in KRW" not in desc, (
            f"T1637OutBlock1.{field_name}: description must not infer KRW unit."
        )
        assert "in shares" not in desc, (
            f"T1637OutBlock1.{field_name}: description must not infer shares unit."
        )

    @pytest.mark.parametrize("field_name", ["svalue", "svolume"])
    def test_t1637_no_sibling_tr_identity_reference(self, field_name: str):
        desc = T1637OutBlock1.model_fields[field_name].description or ""
        assert "Per the t1636 sibling TR" not in desc, (
            f"T1637OutBlock1.{field_name}: must not hedge via sibling TR reference."
        )
        assert "t1636 sibling TR" not in desc, (
            f"T1637OutBlock1.{field_name}: must not reference sibling TR identity."
        )
        assert "Identity:" not in desc, (
            f"T1637OutBlock1.{field_name}: must not assert an identity claim."
        )

    def test_t1637_outblock1_docstring_has_no_sibling_tr_identity(self):
        doc = T1637OutBlock1.__doc__ or ""
        assert "t1636 sibling TR" not in doc, (
            "T1637OutBlock1 docstring must not hedge via sibling TR identity."
        )
        assert "stksvalue - offervalue" not in doc, (
            "T1637OutBlock1 docstring must not embed svalue arithmetic identity."
        )


# ===========================================================================
# Phase A3 — sign field anti-inference guard
# ===========================================================================


class TestT1637SignNoInferredEnum:
    """xingAPI FUNCTION_MAP declares ``sign`` as char(1) with no enum mapping.
    Embedding '1' = upper limit / '5' = down would teach the AI chatbot a
    semantic mapping that LS does not publish.
    """

    def test_sign_no_inferred_enum_mapping(self):
        desc = T1637OutBlock1.model_fields["sign"].description or ""
        for forbidden in [
            "limit-up", "limit-down",
            "upper limit", "lower limit",
            "상한", "하한", "상승", "하락",
        ]:
            assert forbidden not in desc, (
                f"T1637OutBlock1.sign: must not embed inferred enum token '{forbidden}'."
            )
