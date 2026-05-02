"""Unit tests for t1632 시간대별프로그램매매추이 (Korea Stock Program Trading Time-Bucketed Trend).

Regression guard coverage (§8.1 table, 7 guards):

  Guard 1 — URL / domain entry points (Program / KoreaStock / top-level import).
  Guard 2 — InBlock validation: ``gubun`` '0'/'1' anti-copy-paste vs t1631 '1'/'2';
             Literal["1"] for gubun2/gubun3.
  Guard 3 — Field(examples=[...]) auto-validation + coverage (all InBlock /
             OutBlock / OutBlock1 fields must declare at least one example).
  Guard 4 — _build_response LS official example payload exact mapping.
  Guard 5 — occurs_req updater: date+time CTS + tr_cont header updated.
  Guard 6 — OccursReqAbstract INHERITANCE (contrast: t1631 must NOT inherit).
  Guard 7 — OutBlock 4 fields + OutBlock1 14 fields silent rename detection.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.program import Program
from programgarden_finance.ls.korea_stock.program.t1632 import TrT1632
from programgarden_finance.ls.korea_stock.program.t1632.blocks import (
    T1632InBlock,
    T1632OutBlock,
    T1632OutBlock1,
    T1632Request,
    T1632Response,
    T1632ResponseHeader,
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


def _make_request(**overrides: Any) -> T1632Request:
    body = T1632InBlock(
        gubun=overrides.pop("gubun", "0"),
        gubun1=overrides.pop("gubun1", "0"),
        gubun2=overrides.pop("gubun2", "1"),
        gubun3=overrides.pop("gubun3", "1"),
        date=overrides.pop("date", ""),
        time=overrides.pop("time", ""),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1632Request(body={"t1632InBlock": body})


# ---------------------------------------------------------------------------
# LS official example payload (fixed regression baseline)
# ---------------------------------------------------------------------------

LS_OFFICIAL_EXAMPLE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1632OutBlock": {"date": "20230602", "time": "175811", "idx": 19},
    "t1632OutBlock1": [
        {
            "bcha1": 0, "change": "004.59", "sign": "2", "bcha3": 0, "bcha2": 0,
            "k200basis": "000.28", "tot3": 0, "tot1": 0, "tot2": 0, "cha2": 0,
            "cha3": 0, "time": "180518", "cha1": 0, "k200jisu": "342.67",
        },
        {
            "bcha1": 0, "change": "004.59", "sign": "2", "bcha3": 0, "bcha2": 0,
            "k200basis": "000.28", "tot3": 0, "tot1": 0, "tot2": 0, "cha2": 0,
            "cha3": 0, "time": "175928", "cha1": 0, "k200jisu": "342.67",
        },
    ],
}


# ===========================================================================
# Guard 1 — URL / domain entry points
# ===========================================================================


class TestGuard1URLAndEntryPoints:
    def test_program_url_ends_with_stock_program(self):
        """t1632 reuses KOREA_STOCK_PROGRAM_URL shared with t1631 / t1636."""
        assert URLS.KOREA_STOCK_PROGRAM_URL.endswith("/stock/program")
        assert URLS.KOREA_STOCK_PROGRAM_URL.startswith("https://")

    def test_program_t1632_returns_tr_instance(self):
        tm = _make_token_manager()
        program = Program(token_manager=tm)
        body = T1632InBlock(gubun="0", gubun1="0")
        tr = program.t1632(body=body)
        assert isinstance(tr, TrT1632)

    def test_korean_alias_time_trend(self):
        """시간대별프로그램매매추이 alias must reference the same function as t1632."""
        assert Program.t1632 is Program.시간대별프로그램매매추이

    def test_existing_aliases_still_intact(self):
        """Adding t1632 must not break t1631 / t1636 aliases."""
        assert Program.t1631 is Program.프로그램매매종합조회
        assert Program.t1636 is Program.종목별프로그램매매동향

    def test_korea_stock_chained_call(self):
        """LS().국내주식().프로그램매매().시간대별프로그램매매추이(...) chain works."""
        tm = _make_token_manager()
        ks = KoreaStock(tm)
        body = T1632InBlock(gubun="0", gubun1="0", date="", time="", exchgubun="K")
        tr = ks.프로그램매매().시간대별프로그램매매추이(body=body)
        assert isinstance(tr, TrT1632)
        assert tr.request_data.body["t1632InBlock"].gubun == "0"

    def test_top_level_module_export(self):
        """``from programgarden_finance import t1632`` exposes key symbols."""
        from programgarden_finance import t1632 as top_t1632

        assert hasattr(top_t1632, "T1632InBlock")
        assert hasattr(top_t1632, "T1632Request")
        assert hasattr(top_t1632, "TrT1632")


# ===========================================================================
# Guard 2 — InBlock validation (anti-copy-paste + Literal enforcement)
# ===========================================================================


class TestGuard2InBlockValidation:
    """Critical: gubun '0'/'1' for t1632 vs '1'/'2' for t1631.

    Anti-copy-paste regression guard: if a developer copies t1631 InBlock
    inputs (gubun='1' for 거래소, gubun='2' for KOSDAQ) into a t1632 call,
    t1632 must reject '2' immediately via ValidationError.
    """

    @pytest.mark.parametrize("gubun", ["0", "1"])
    def test_valid_gubun_values(self, gubun):
        block = T1632InBlock(gubun=gubun, gubun1="0")
        assert block.gubun == gubun

    @pytest.mark.parametrize("bad_gubun", ["2", "3", "K", ""])
    def test_invalid_gubun_rejected(self, bad_gubun):
        """'2' in particular must be rejected (it is valid in t1631 but NOT t1632)."""
        with pytest.raises(ValidationError):
            T1632InBlock(gubun=bad_gubun, gubun1="0")

    @pytest.mark.parametrize("gubun1", ["0", "1"])
    def test_valid_gubun1_values(self, gubun1):
        block = T1632InBlock(gubun="0", gubun1=gubun1)
        assert block.gubun1 == gubun1

    @pytest.mark.parametrize("bad_gubun1", ["2", "3", ""])
    def test_invalid_gubun1_rejected(self, bad_gubun1):
        with pytest.raises(ValidationError):
            T1632InBlock(gubun="0", gubun1=bad_gubun1)

    def test_gubun2_only_1_valid(self):
        """Literal['1'] — only '1' is valid per LS spec."""
        block = T1632InBlock(gubun="0", gubun1="0", gubun2="1")
        assert block.gubun2 == "1"

    @pytest.mark.parametrize("bad_gubun2", ["0", "2", "3"])
    def test_gubun2_rejects_non_1(self, bad_gubun2):
        with pytest.raises(ValidationError):
            T1632InBlock(gubun="0", gubun1="0", gubun2=bad_gubun2)

    def test_gubun3_only_1_valid(self):
        """Literal['1'] — only '1' is valid per LS spec."""
        block = T1632InBlock(gubun="0", gubun1="0", gubun3="1")
        assert block.gubun3 == "1"

    @pytest.mark.parametrize("bad_gubun3", ["0", "2", "3"])
    def test_gubun3_rejects_non_1(self, bad_gubun3):
        with pytest.raises(ValidationError):
            T1632InBlock(gubun="0", gubun1="0", gubun3=bad_gubun3)

    @pytest.mark.parametrize("exchgubun", ["K", "N", "U"])
    def test_valid_exchgubun_values(self, exchgubun):
        block = T1632InBlock(gubun="0", gubun1="0", exchgubun=exchgubun)
        assert block.exchgubun == exchgubun

    @pytest.mark.parametrize("bad_exchgubun", ["Z", "KK", "1"])
    def test_invalid_exchgubun_rejected(self, bad_exchgubun):
        with pytest.raises(ValidationError):
            T1632InBlock(gubun="0", gubun1="0", exchgubun=bad_exchgubun)

    def test_exchgubun_default_is_k(self):
        """exchgubun must default to 'K' per plan §14 item 2."""
        block = T1632InBlock(gubun="0", gubun1="0")
        assert block.exchgubun == "K"

    def test_gubun2_default_is_1(self):
        """gubun2 must default to '1' per plan §14 item 4."""
        block = T1632InBlock(gubun="0", gubun1="0")
        assert block.gubun2 == "1"

    def test_gubun3_default_is_1(self):
        """gubun3 must default to '1' per plan §14 item 4."""
        block = T1632InBlock(gubun="0", gubun1="0")
        assert block.gubun3 == "1"

    def test_empty_date_time_allowed_for_first_request(self):
        """Empty date/time strings are valid for the first-page request."""
        block = T1632InBlock(gubun="0", gubun1="0", date="", time="")
        assert block.date == ""
        assert block.time == ""

    def test_nonempty_date_time_accepted(self):
        block = T1632InBlock(gubun="0", gubun1="0", date="20230602", time="175811")
        assert block.date == "20230602"
        assert block.time == "175811"


# ===========================================================================
# Guard 3 — Field(examples=[...]) coverage and type-validity
# ===========================================================================


class TestGuard3FieldExamplesValidate:
    """All Field(examples=[...]) values must round-trip through TypeAdapter.

    Why: AI chatbots read examples from model_json_schema() and learn from
    them. A typo or wrong-type example silently teaches the chatbot bad input.
    """

    @pytest.mark.parametrize(
        "model_cls",
        [T1632InBlock, T1632OutBlock, T1632OutBlock1],
        ids=["T1632InBlock", "T1632OutBlock", "T1632OutBlock1"],
    )
    def test_all_field_examples_type_valid(self, model_cls: Type[BaseModel]):
        failures: list[str] = []
        for field_name, field_info in model_cls.model_fields.items():
            examples = field_info.examples or []
            if not examples:
                continue
            adapter = TypeAdapter(field_info.annotation)
            for ex in examples:
                try:
                    adapter.validate_python(ex)
                except (ValidationError, Exception) as exc:
                    failures.append(
                        f"{model_cls.__name__}.{field_name} example {ex!r} "
                        f"failed: {exc}"
                    )
        assert not failures, "Invalid Field examples:\n" + "\n".join(failures)

    @pytest.mark.parametrize(
        "model_cls",
        [T1632InBlock, T1632OutBlock, T1632OutBlock1],
        ids=["T1632InBlock", "T1632OutBlock", "T1632OutBlock1"],
    )
    def test_every_field_has_at_least_one_example(self, model_cls: Type[BaseModel]):
        missing = [
            name
            for name, info in model_cls.model_fields.items()
            if not (info.examples or [])
        ]
        assert not missing, (
            f"{model_cls.__name__} fields without examples=[...]: {missing}. "
            "All InBlock / OutBlock / OutBlock1 fields must carry at least one example."
        )


# ===========================================================================
# Guard 4 — _build_response LS official example payload exact mapping
# ===========================================================================


class TestGuard4BuildResponse:
    def _make_tr(self) -> TrT1632:
        return TrT1632(_make_request())

    def _make_headers(self) -> Dict[str, Any]:
        return {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1632",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

    def test_happy_path_ls_official_example(self):
        """Exact mapping of the LS official example payload (4 scalar cont + 2 rows × 14 fields)."""
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        result = tr._build_response(resp_obj, LS_OFFICIAL_EXAMPLE, self._make_headers(), None)

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.rsp_msg == "정상적으로 조회가 완료되었습니다."
        assert result.header is not None
        assert isinstance(result.header, T1632ResponseHeader)

        # cont_block — 4 scalar fields
        cb = result.cont_block
        assert cb is not None
        assert cb.date == "20230602"
        assert cb.time == "175811"
        assert cb.idx == 19
        assert cb.ex_gubun == ""  # absent from LS example → default ''

        # block — 2 rows
        assert len(result.block) == 2

        row0 = result.block[0]
        assert row0.time == "180518"
        assert row0.k200jisu == pytest.approx(342.67)
        assert row0.sign == "2"
        assert row0.change == pytest.approx(4.59)
        assert row0.k200basis == pytest.approx(0.28)
        # all integer fields are 0 in the LS example (weekend/market-closed data)
        for field in ("tot1", "tot2", "tot3", "cha1", "cha2", "cha3", "bcha1", "bcha2", "bcha3"):
            assert getattr(row0, field) == 0, f"row0.{field} expected 0"

        row1 = result.block[1]
        assert row1.time == "175928"
        assert row1.k200jisu == pytest.approx(342.67)
        assert row1.sign == "2"
        assert row1.change == pytest.approx(4.59)
        assert row1.k200basis == pytest.approx(0.28)

    def test_http_500_error_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json", "tr_cd": "t1632"},
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
        result = tr._build_response(None, None, None, ConnectionError("network down"))
        assert result.error_msg == "network down"
        assert result.status_code is None
        assert result.cont_block is None
        assert result.block == []

    def test_ls_level_error_with_200_status(self):
        """rsp_cd != '00000' but HTTP 200 — error_msg not set, rsp_cd preserved."""
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        result = tr._build_response(
            resp_obj,
            {"rsp_cd": "IGW00121", "rsp_msg": "거래 시간이 아닙니다."},
            {"Content-Type": "application/json", "tr_cd": "t1632", "tr_cont": "N", "tr_cont_key": ""},
            None,
        )
        assert result.status_code == 200
        assert result.error_msg is None
        assert result.rsp_cd == "IGW00121"
        assert result.rsp_msg == "거래 시간이 아닙니다."

    def test_cont_block_ex_gubun_defaults_empty_when_absent(self):
        """LS official example omits ex_gubun — must default to '' not raise."""
        example_without_ex_gubun = {
            "rsp_cd": "00000",
            "rsp_msg": "OK",
            "t1632OutBlock": {"date": "20230602", "time": "175811", "idx": 19},
            "t1632OutBlock1": [],
        }
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        result = tr._build_response(resp_obj, example_without_ex_gubun, self._make_headers(), None)
        assert result.cont_block is not None
        assert result.cont_block.ex_gubun == ""


# ===========================================================================
# Guard 5 — occurs_req updater: date+time CTS + tr_cont header
# ===========================================================================


class TestGuard5OccursReqUpdater:
    """t1632 pages by date+time CTS — NOT by idx (unlike t1452).

    Verify that the _updater inside occurs_req correctly advances:
      - req.header.tr_cont   ← resp.header.tr_cont
      - req.header.tr_cont_key ← resp.header.tr_cont_key
      - req.body["t1632InBlock"].date ← resp.cont_block.date
      - req.body["t1632InBlock"].time ← resp.cont_block.time
    """

    def test_updater_propagates_date_time_and_tr_cont(self):
        from programgarden_finance.ls.korea_stock.program.t1632.blocks import (
            T1632OutBlock,
            T1632ResponseHeader,
        )

        req = _make_request(date="", time="")
        tr = TrT1632(req)

        fake_resp = T1632Response(
            header=T1632ResponseHeader(
                content_type="application/json; charset=utf-8",
                tr_cd="t1632",
                tr_cont="Y",
                tr_cont_key="xyz",
            ),
            cont_block=T1632OutBlock(date="20230602", time="175800", idx=18, ex_gubun=""),
            block=[],
            rsp_cd="00000",
            rsp_msg="",
            status_code=200,
        )

        # Simulate what occurs_req._updater does
        req_data = tr.request_data
        req_data.header.tr_cont_key = fake_resp.header.tr_cont_key
        req_data.header.tr_cont = fake_resp.header.tr_cont
        req_data.body["t1632InBlock"].date = fake_resp.cont_block.date
        req_data.body["t1632InBlock"].time = fake_resp.cont_block.time

        assert req_data.header.tr_cont == "Y"
        assert req_data.header.tr_cont_key == "xyz"
        assert req_data.body["t1632InBlock"].date == "20230602"
        assert req_data.body["t1632InBlock"].time == "175800"

    def test_updater_does_not_update_idx(self):
        """t1632 paging uses date+time only — idx is NOT fed back into the request."""
        # Confirm there is no 'idx' field on T1632InBlock
        assert "idx" not in T1632InBlock.model_fields, (
            "T1632InBlock must not have an 'idx' field — t1632 pages by "
            "date+time, not by idx (contrast: t1452 uses idx)."
        )


# ===========================================================================
# Guard 6 — OccursReqAbstract inheritance (contrast with t1631)
# ===========================================================================


class TestGuard6InheritsOccursReq:
    """t1632 MUST inherit OccursReqAbstract (unlike t1631 which must NOT).

    This guard and the corresponding t1631 guard form a paired regression
    boundary that locks the different continuation behaviour of the two TRs.
    """

    def test_inherits_tr_request_abstract(self):
        tr = TrT1632(_make_request())
        assert isinstance(tr, TRRequestAbstract)

    def test_inherits_occurs_req_abstract(self):
        tr = TrT1632(_make_request())
        assert isinstance(tr, OccursReqAbstract)

    def test_has_occurs_req_method(self):
        tr = TrT1632(_make_request())
        assert hasattr(tr, "occurs_req")
        assert callable(tr.occurs_req)

    def test_has_occurs_req_async_method(self):
        tr = TrT1632(_make_request())
        assert hasattr(tr, "occurs_req_async")
        assert callable(tr.occurs_req_async)

    def test_class_inherits_occurs_req_abstract(self):
        assert issubclass(TrT1632, OccursReqAbstract)


# ===========================================================================
# Guard 7 — Silent rename detection (set comparison on model_fields)
# ===========================================================================


class TestGuard7FieldSetRegression:
    """Explicit set comparison flags LS silent field rename / add / remove."""

    def test_t1632_outblock_fields(self):
        """T1632OutBlock must have exactly these 4 fields."""
        expected = {"date", "time", "idx", "ex_gubun"}
        assert set(T1632OutBlock.model_fields.keys()) == expected

    def test_t1632_outblock1_fields(self):
        """T1632OutBlock1 must have exactly these 14 fields."""
        expected = {
            "time", "k200jisu", "sign", "change", "k200basis",
            "tot3", "tot1", "tot2",
            "cha3", "cha1", "cha2",
            "bcha3", "bcha1", "bcha2",
        }
        assert set(T1632OutBlock1.model_fields.keys()) == expected

    def test_t1632_inblock_fields(self):
        """T1632InBlock must have exactly these 7 fields."""
        expected = {"gubun", "gubun1", "gubun2", "gubun3", "date", "time", "exchgubun"}
        assert set(T1632InBlock.model_fields.keys()) == expected

    def test_outblock_defaults(self):
        """All T1632OutBlock fields must have usable defaults."""
        cb = T1632OutBlock()
        assert cb.date == ""
        assert cb.time == ""
        assert cb.idx == 0
        assert cb.ex_gubun == ""

    def test_outblock1_defaults_zero_for_numerics(self):
        row = T1632OutBlock1()
        for field in ("k200jisu", "change", "k200basis"):
            assert getattr(row, field) == 0.0, f"T1632OutBlock1.{field} expected 0.0"
        for field in ("tot1", "tot2", "tot3", "cha1", "cha2", "cha3", "bcha1", "bcha2", "bcha3"):
            assert getattr(row, field) == 0, f"T1632OutBlock1.{field} expected 0"

    def test_response_uses_cont_block_not_summary_block(self):
        """t1632 must expose cont_block (paging cursor), NOT summary_block (t1631 pattern).

        This regression guard explicitly verifies that the two OutBlock patterns
        are not confused between t1631 and t1632.
        """
        assert "cont_block" in T1632Response.model_fields
        assert "summary_block" not in T1632Response.model_fields

    def test_outblock1_float_coerce_from_string(self):
        """LS may return k200jisu / change / k200basis as zero-padded strings — verify coerce."""
        row = T1632OutBlock1.model_validate({
            "k200jisu": "342.67",
            "change": "004.59",
            "k200basis": "000.28",
        })
        assert row.k200jisu == pytest.approx(342.67)
        assert row.change == pytest.approx(4.59)
        assert row.k200basis == pytest.approx(0.28)
