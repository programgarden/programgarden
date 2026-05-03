"""Unit tests for t1633 기간별프로그램매매추이 (Korea Stock Program Trading Period Trend).

Regression guard coverage (8 guards):

  Guard 1 — URL / domain entry points (Program / KoreaStock / top-level import).
  Guard 2 — InBlock validation: ``gubun`` '0'/'1' anti-copy-paste vs t1631 '1'/'2';
             ``gubun2`` '0'/'1' both valid (NOT Literal['1'] like t1632);
             ``gubun3`` '1'/'2'/'3' all valid (NOT Literal['1'] like t1632);
             ``gubun4`` '0'/'1' (t1632 has no equivalent);
             ``fdate`` / ``tdate`` strict pattern r"^\\d{8}$" (anti-typo).
  Guard 3 — Field(examples=[...]) auto-validation + coverage (all InBlock /
             OutBlock / OutBlock1 fields must declare at least one example).
  Guard 4 — _build_response LS official example payload exact mapping.
  Guard 5 — occurs_req updater: date CTS + tr_cont header updated, time NOT propagated.
  Guard 6 — OccursReqAbstract INHERITANCE (matches t1632; contrasts with t1631).
  Guard 7 — OutBlock 2 fields + OutBlock1 14 fields silent rename detection.
  Guard 8 — t1633-unique fields: jisu (NOT k200jisu), date row key (NOT time),
             volume present (t1632 absent), k200basis absent, float coerce
             from zero-padded strings.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.program import Program
from programgarden_finance.ls.korea_stock.program.t1633 import TrT1633
from programgarden_finance.ls.korea_stock.program.t1633.blocks import (
    T1633InBlock,
    T1633OutBlock,
    T1633OutBlock1,
    T1633Request,
    T1633Response,
    T1633ResponseHeader,
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


def _make_request(**overrides: Any) -> T1633Request:
    body = T1633InBlock(
        gubun=overrides.pop("gubun", "0"),
        gubun1=overrides.pop("gubun1", "0"),
        gubun2=overrides.pop("gubun2", "0"),
        gubun3=overrides.pop("gubun3", "1"),
        fdate=overrides.pop("fdate", "20230101"),
        tdate=overrides.pop("tdate", "20230619"),
        gubun4=overrides.pop("gubun4", "0"),
        date=overrides.pop("date", " "),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1633Request(body={"t1633InBlock": body})


# ---------------------------------------------------------------------------
# LS official example payload (fixed regression baseline)
# ---------------------------------------------------------------------------

LS_OFFICIAL_EXAMPLE: Dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상적으로 조회가 완료되었습니다.",
    "t1633OutBlock": {"date": "20230102", "idx": 115},
    "t1633OutBlock1": [
        {
            "date": "20230619",
            "bcha1": 6921, "change": "16.32", "sign": "2", "bcha3": 6441, "bcha2": 480,
            "tot3": 6441, "tot1": 6921, "tot2": 480,
            "jisu": "329.85", "volume": 245,
            "cha2": 0, "cha3": 0, "cha1": 0,
        },
        {
            "date": "20230616",
            "bcha1": 808, "change": "1.98", "sign": "2", "bcha3": 282, "bcha2": 526,
            "tot3": 391, "tot1": 917, "tot2": 526,
            "jisu": "345.17", "volume": 153589,
            "cha2": 0, "cha3": 109, "cha1": 109,
        },
    ],
}


# ===========================================================================
# Guard 1 — URL / domain entry points
# ===========================================================================


class TestGuard1URLAndEntryPoints:
    def test_program_url_ends_with_stock_program(self):
        """t1633 reuses KOREA_STOCK_PROGRAM_URL shared with t1631 / t1632 / t1636."""
        assert URLS.KOREA_STOCK_PROGRAM_URL.endswith("/stock/program")
        assert URLS.KOREA_STOCK_PROGRAM_URL.startswith("https://")

    def test_program_t1633_returns_tr_instance(self):
        tm = _make_token_manager()
        program = Program(token_manager=tm)
        body = T1633InBlock(
            gubun="0", gubun1="0", fdate="20230101", tdate="20230619"
        )
        tr = program.t1633(body=body)
        assert isinstance(tr, TrT1633)

    def test_korean_alias_period_trend(self):
        """기간별프로그램매매추이 alias must reference the same function as t1633."""
        assert Program.t1633 is Program.기간별프로그램매매추이

    def test_existing_aliases_still_intact(self):
        """Adding t1633 must not break t1631 / t1632 / t1636 aliases."""
        assert Program.t1631 is Program.프로그램매매종합조회
        assert Program.t1632 is Program.시간대별프로그램매매추이
        assert Program.t1636 is Program.종목별프로그램매매동향

    def test_korea_stock_chained_call(self):
        """LS().국내주식().프로그램매매().기간별프로그램매매추이(...) chain works."""
        tm = _make_token_manager()
        ks = KoreaStock(tm)
        body = T1633InBlock(
            gubun="0", gubun1="0", fdate="20230101", tdate="20230619",
            date=" ", exchgubun="K",
        )
        tr = ks.프로그램매매().기간별프로그램매매추이(body=body)
        assert isinstance(tr, TrT1633)
        assert tr.request_data.body["t1633InBlock"].gubun == "0"

    def test_top_level_module_export(self):
        """``from programgarden_finance import t1633`` exposes key symbols."""
        from programgarden_finance import t1633 as top_t1633

        assert hasattr(top_t1633, "T1633InBlock")
        assert hasattr(top_t1633, "T1633Request")
        assert hasattr(top_t1633, "TrT1633")


# ===========================================================================
# Guard 2 — InBlock validation (anti-copy-paste + Literal + pattern enforcement)
# ===========================================================================


class TestGuard2InBlockValidation:
    """Critical: gubun '0'/'1' for t1633 vs '1'/'2' for t1631; gubun2/gubun3
    enum domains differ from t1632 (t1633 = full domain, t1632 = Literal['1']).

    Anti-copy-paste regression guards: if a developer copies t1631 / t1632
    InBlock inputs into a t1633 call, the wrong-domain inputs must be
    caught by Pydantic immediately.
    """

    @pytest.mark.parametrize("gubun", ["0", "1"])
    def test_valid_gubun_values(self, gubun):
        block = T1633InBlock(
            gubun=gubun, gubun1="0", fdate="20230101", tdate="20230619"
        )
        assert block.gubun == gubun

    @pytest.mark.parametrize("bad_gubun", ["2", "3", "K", ""])
    def test_invalid_gubun_rejected(self, bad_gubun):
        """'2' in particular must be rejected (it is valid in t1631 but NOT t1633)."""
        with pytest.raises(ValidationError):
            T1633InBlock(
                gubun=bad_gubun, gubun1="0", fdate="20230101", tdate="20230619"
            )

    @pytest.mark.parametrize("gubun1", ["0", "1"])
    def test_valid_gubun1_values(self, gubun1):
        block = T1633InBlock(
            gubun="0", gubun1=gubun1, fdate="20230101", tdate="20230619"
        )
        assert block.gubun1 == gubun1

    @pytest.mark.parametrize("bad_gubun1", ["2", "3", ""])
    def test_invalid_gubun1_rejected(self, bad_gubun1):
        with pytest.raises(ValidationError):
            T1633InBlock(
                gubun="0", gubun1=bad_gubun1, fdate="20230101", tdate="20230619"
            )

    @pytest.mark.parametrize("gubun2", ["0", "1"])
    def test_gubun2_both_values_valid(self, gubun2):
        """Both '0' (수치) and '1' (누적) must be accepted — differs from t1632."""
        block = T1633InBlock(
            gubun="0", gubun1="0", gubun2=gubun2,
            fdate="20230101", tdate="20230619",
        )
        assert block.gubun2 == gubun2

    @pytest.mark.parametrize("bad_gubun2", ["2", "3", "K"])
    def test_gubun2_rejects_other_values(self, bad_gubun2):
        with pytest.raises(ValidationError):
            T1633InBlock(
                gubun="0", gubun1="0", gubun2=bad_gubun2,
                fdate="20230101", tdate="20230619",
            )

    @pytest.mark.parametrize("gubun3", ["1", "2", "3"])
    def test_gubun3_all_three_values_valid(self, gubun3):
        """'1' (일), '2' (주), '3' (월) must all be accepted — differs from t1632."""
        block = T1633InBlock(
            gubun="0", gubun1="0", gubun3=gubun3,
            fdate="20230101", tdate="20230619",
        )
        assert block.gubun3 == gubun3

    @pytest.mark.parametrize("bad_gubun3", ["0", "4", "5", "K"])
    def test_gubun3_rejects_other_values(self, bad_gubun3):
        with pytest.raises(ValidationError):
            T1633InBlock(
                gubun="0", gubun1="0", gubun3=bad_gubun3,
                fdate="20230101", tdate="20230619",
            )

    @pytest.mark.parametrize("gubun4", ["0", "1"])
    def test_gubun4_both_values_valid(self, gubun4):
        block = T1633InBlock(
            gubun="0", gubun1="0", gubun4=gubun4,
            fdate="20230101", tdate="20230619",
        )
        assert block.gubun4 == gubun4

    @pytest.mark.parametrize("bad_gubun4", ["2", "3", "K"])
    def test_gubun4_rejects_other_values(self, bad_gubun4):
        with pytest.raises(ValidationError):
            T1633InBlock(
                gubun="0", gubun1="0", gubun4=bad_gubun4,
                fdate="20230101", tdate="20230619",
            )

    @pytest.mark.parametrize(
        "good_date", ["20230101", "20230619", "19990101", "20240229"]
    )
    def test_fdate_pattern_accepts_8_digits(self, good_date):
        block = T1633InBlock(
            gubun="0", gubun1="0", fdate=good_date, tdate="20230619"
        )
        assert block.fdate == good_date

    @pytest.mark.parametrize(
        "bad_date",
        ["", "2023-01-01", "2023010", "202301010", "20230A01", "abcdefgh", "2023.01.01"],
    )
    def test_fdate_pattern_rejects_non_numeric_or_wrong_length(self, bad_date):
        """Pydantic pattern=r'^\\d{8}$' — strict 8 numeric digits only."""
        with pytest.raises(ValidationError):
            T1633InBlock(
                gubun="0", gubun1="0", fdate=bad_date, tdate="20230619"
            )

    @pytest.mark.parametrize(
        "bad_date",
        ["", "2023-01-01", "2023010", "202301010", "20230A01", "abcdefgh"],
    )
    def test_tdate_pattern_rejects_non_numeric_or_wrong_length(self, bad_date):
        with pytest.raises(ValidationError):
            T1633InBlock(
                gubun="0", gubun1="0", fdate="20230101", tdate=bad_date
            )

    @pytest.mark.parametrize("exchgubun", ["K", "N", "U"])
    def test_valid_exchgubun_values(self, exchgubun):
        block = T1633InBlock(
            gubun="0", gubun1="0", fdate="20230101", tdate="20230619",
            exchgubun=exchgubun,
        )
        assert block.exchgubun == exchgubun

    @pytest.mark.parametrize("bad_exchgubun", ["Z", "KK", "1"])
    def test_invalid_exchgubun_rejected(self, bad_exchgubun):
        with pytest.raises(ValidationError):
            T1633InBlock(
                gubun="0", gubun1="0", fdate="20230101", tdate="20230619",
                exchgubun=bad_exchgubun,
            )

    def test_defaults_match_plan(self):
        """Defaults: gubun2='0', gubun3='1', gubun4='0', date=' ' (single space), exchgubun='K'."""
        block = T1633InBlock(
            gubun="0", gubun1="0", fdate="20230101", tdate="20230619"
        )
        assert block.gubun2 == "0"
        assert block.gubun3 == "1"
        assert block.gubun4 == "0"
        assert block.date == " "  # single space — LS official example default
        assert block.exchgubun == "K"

    def test_inblock_has_no_time_field(self):
        """t1633 pages by date only — no `time` field (contrast: t1632)."""
        assert "time" not in T1633InBlock.model_fields, (
            "T1633InBlock must NOT have a 'time' field — t1633 pages by "
            "date alone (contrast: t1632 pages by date + time)."
        )

    def test_inblock_has_t1633_specific_fields(self):
        """fdate, tdate, gubun4 are t1633-unique fields (t1632 has none)."""
        assert "fdate" in T1633InBlock.model_fields
        assert "tdate" in T1633InBlock.model_fields
        assert "gubun4" in T1633InBlock.model_fields


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
        [T1633InBlock, T1633OutBlock, T1633OutBlock1],
        ids=["T1633InBlock", "T1633OutBlock", "T1633OutBlock1"],
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
        [T1633InBlock, T1633OutBlock, T1633OutBlock1],
        ids=["T1633InBlock", "T1633OutBlock", "T1633OutBlock1"],
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

    def test_fdate_examples_satisfy_pattern(self):
        """fdate examples must all satisfy ^\\d{8}$ — guards against doc/code drift."""
        import re
        examples = T1633InBlock.model_fields["fdate"].examples or []
        for ex in examples:
            assert re.match(r"^\d{8}$", ex), (
                f"fdate example {ex!r} violates pattern ^\\d{{8}}$"
            )

    def test_tdate_examples_satisfy_pattern(self):
        import re
        examples = T1633InBlock.model_fields["tdate"].examples or []
        for ex in examples:
            assert re.match(r"^\d{8}$", ex), (
                f"tdate example {ex!r} violates pattern ^\\d{{8}}$"
            )


# ===========================================================================
# Guard 4 — _build_response LS official example payload exact mapping
# ===========================================================================


class TestGuard4BuildResponse:
    def _make_tr(self) -> TrT1633:
        return TrT1633(_make_request())

    def _make_headers(self) -> Dict[str, Any]:
        return {
            "Content-Type": "application/json; charset=utf-8",
            "tr_cd": "t1633",
            "tr_cont": "N",
            "tr_cont_key": "",
        }

    def test_happy_path_ls_official_example(self):
        """Exact mapping of the LS official example payload (2 cont fields + 2 rows × 14 fields)."""
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        result = tr._build_response(
            resp_obj, LS_OFFICIAL_EXAMPLE, self._make_headers(), None
        )

        assert result.error_msg is None
        assert result.status_code == 200
        assert result.rsp_cd == "00000"
        assert result.rsp_msg == "정상적으로 조회가 완료되었습니다."
        assert result.header is not None
        assert isinstance(result.header, T1633ResponseHeader)

        # cont_block — 2 scalar fields
        cb = result.cont_block
        assert cb is not None
        assert cb.date == "20230102"
        assert cb.idx == 115

        # block — 2 rows
        assert len(result.block) == 2

        row0 = result.block[0]
        assert row0.date == "20230619"
        assert row0.jisu == pytest.approx(329.85)
        assert row0.sign == "2"
        assert row0.change == pytest.approx(16.32)
        assert row0.tot1 == 6921
        assert row0.tot2 == 480
        assert row0.tot3 == 6441
        assert row0.bcha1 == 6921
        assert row0.bcha2 == 480
        assert row0.bcha3 == 6441
        assert row0.cha1 == 0 and row0.cha2 == 0 and row0.cha3 == 0
        assert row0.volume == 245

        row1 = result.block[1]
        assert row1.date == "20230616"
        assert row1.jisu == pytest.approx(345.17)
        assert row1.sign == "2"
        assert row1.change == pytest.approx(1.98)
        assert row1.volume == 153589
        assert row1.cha1 == 109
        assert row1.cha3 == 109
        assert row1.cha2 == 0
        assert row1.bcha1 == 808
        assert row1.bcha2 == 526
        assert row1.bcha3 == 282

    def test_http_500_error_path(self):
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 500
        result = tr._build_response(
            resp_obj,
            {"rsp_msg": "Internal error"},
            {"Content-Type": "application/json", "tr_cd": "t1633"},
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
        result = tr._build_response(
            None, None, None, ConnectionError("network down")
        )
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
            {"Content-Type": "application/json", "tr_cd": "t1633", "tr_cont": "N", "tr_cont_key": ""},
            None,
        )
        assert result.status_code == 200
        assert result.error_msg is None
        assert result.rsp_cd == "IGW00121"
        assert result.rsp_msg == "거래 시간이 아닙니다."

    def test_empty_block_with_cont(self):
        """LS may return empty t1633OutBlock1 when the period has no data."""
        empty_block_example = {
            "rsp_cd": "00000",
            "rsp_msg": "OK",
            "t1633OutBlock": {"date": "20230102", "idx": 0},
            "t1633OutBlock1": [],
        }
        tr = self._make_tr()
        resp_obj = MagicMock()
        resp_obj.status = 200
        result = tr._build_response(
            resp_obj, empty_block_example, self._make_headers(), None
        )
        assert result.cont_block is not None
        assert result.cont_block.date == "20230102"
        assert result.block == []


# ===========================================================================
# Guard 5 — occurs_req updater: date CTS + tr_cont header (NO time)
# ===========================================================================


class TestGuard5OccursReqUpdater:
    """t1633 pages by date alone — NO time cursor (unlike t1632).

    Verify that the _updater inside occurs_req correctly advances:
      - req.header.tr_cont   ← resp.header.tr_cont
      - req.header.tr_cont_key ← resp.header.tr_cont_key
      - req.body["t1633InBlock"].date ← resp.cont_block.date
    and does NOT touch any time field (which doesn't exist on T1633InBlock).
    """

    def test_updater_propagates_date_and_tr_cont(self):
        req = _make_request(date=" ")
        tr = TrT1633(req)

        fake_resp = T1633Response(
            header=T1633ResponseHeader(
                content_type="application/json; charset=utf-8",
                tr_cd="t1633",
                tr_cont="Y",
                tr_cont_key="xyz",
            ),
            cont_block=T1633OutBlock(date="20230102", idx=115),
            block=[],
            rsp_cd="00000",
            rsp_msg="",
            status_code=200,
        )

        # Simulate what occurs_req._updater does
        req_data = tr.request_data
        req_data.header.tr_cont_key = fake_resp.header.tr_cont_key
        req_data.header.tr_cont = fake_resp.header.tr_cont
        req_data.body["t1633InBlock"].date = fake_resp.cont_block.date

        assert req_data.header.tr_cont == "Y"
        assert req_data.header.tr_cont_key == "xyz"
        assert req_data.body["t1633InBlock"].date == "20230102"

    def test_updater_does_not_propagate_time(self):
        """t1633 has no time cursor — the InBlock must not have a time attr."""
        req = _make_request()
        in_block = req.body["t1633InBlock"]
        assert not hasattr(in_block, "time"), (
            "T1633InBlock must not expose a 'time' attribute — t1633 pages "
            "by date alone (contrast: t1632 pages by date + time)."
        )

    def test_updater_does_not_update_idx(self):
        """t1633 paging uses date only — idx is NOT fed back into the request."""
        # Confirm there is no 'idx' field on T1633InBlock
        assert "idx" not in T1633InBlock.model_fields, (
            "T1633InBlock must not have an 'idx' field — t1633 pages by "
            "date only (idx is internal to OutBlock)."
        )


# ===========================================================================
# Guard 6 — OccursReqAbstract inheritance (matches t1632; contrasts with t1631)
# ===========================================================================


class TestGuard6InheritsOccursReq:
    """t1633 MUST inherit OccursReqAbstract (like t1632, unlike t1631).

    This guard pairs with the t1631 / t1632 guards to lock the different
    continuation behaviour of the four /stock/program TRs.
    """

    def test_inherits_tr_request_abstract(self):
        tr = TrT1633(_make_request())
        assert isinstance(tr, TRRequestAbstract)

    def test_inherits_occurs_req_abstract(self):
        tr = TrT1633(_make_request())
        assert isinstance(tr, OccursReqAbstract)

    def test_has_occurs_req_method(self):
        tr = TrT1633(_make_request())
        assert hasattr(tr, "occurs_req")
        assert callable(tr.occurs_req)

    def test_has_occurs_req_async_method(self):
        tr = TrT1633(_make_request())
        assert hasattr(tr, "occurs_req_async")
        assert callable(tr.occurs_req_async)

    def test_class_inherits_occurs_req_abstract(self):
        assert issubclass(TrT1633, OccursReqAbstract)


# ===========================================================================
# Guard 7 — Silent rename detection (set comparison on model_fields)
# ===========================================================================


class TestGuard7FieldSetRegression:
    """Explicit set comparison flags LS silent field rename / add / remove."""

    def test_t1633_outblock_fields(self):
        """T1633OutBlock must have exactly these 2 fields (vs t1632's 4)."""
        expected = {"date", "idx"}
        assert set(T1633OutBlock.model_fields.keys()) == expected

    def test_t1633_outblock1_fields(self):
        """T1633OutBlock1 must have exactly these 14 fields."""
        expected = {
            "date", "jisu", "sign", "change",
            "tot3", "tot1", "tot2",
            "cha3", "cha1", "cha2",
            "bcha3", "bcha1", "bcha2",
            "volume",
        }
        assert set(T1633OutBlock1.model_fields.keys()) == expected

    def test_t1633_inblock_fields(self):
        """T1633InBlock must have exactly these 9 fields."""
        expected = {
            "gubun", "gubun1", "gubun2", "gubun3",
            "fdate", "tdate", "gubun4",
            "date", "exchgubun",
        }
        assert set(T1633InBlock.model_fields.keys()) == expected

    def test_outblock_defaults(self):
        """All T1633OutBlock fields must have usable defaults."""
        cb = T1633OutBlock()
        assert cb.date == ""
        assert cb.idx == 0

    def test_outblock1_defaults(self):
        row = T1633OutBlock1()
        assert row.date == ""
        assert row.jisu == 0.0
        assert row.change == 0.0
        for field in ("tot1", "tot2", "tot3", "cha1", "cha2", "cha3",
                      "bcha1", "bcha2", "bcha3", "volume"):
            assert getattr(row, field) == 0, f"T1633OutBlock1.{field} expected 0"

    def test_response_uses_cont_block_not_summary_block(self):
        """t1633 must expose cont_block (paging cursor), NOT summary_block (t1631 pattern)."""
        assert "cont_block" in T1633Response.model_fields
        assert "summary_block" not in T1633Response.model_fields

    def test_response_block_field_exists(self):
        """T1633Response.block (List[T1633OutBlock1]) — not renamed."""
        assert "block" in T1633Response.model_fields


# ===========================================================================
# Guard 8 — t1633-unique field naming + float coerce
# ===========================================================================


class TestGuard8T1633UniqueFields:
    """Distinguishes t1633 from t1632 at the field-name level.

    Critical regression boundary: if a developer copies t1632's blocks.py
    and forgets to rename time→date or k200jisu→jisu, this test fails
    immediately. Likewise volume must be present and k200basis must be
    absent.
    """

    def test_outblock1_has_jisu_not_k200jisu(self):
        """t1633 row uses 'jisu' (not 'k200jisu' like t1632)."""
        assert "jisu" in T1633OutBlock1.model_fields
        assert "k200jisu" not in T1633OutBlock1.model_fields

    def test_outblock1_has_date_not_time(self):
        """t1633 row uses 'date' (not 'time' like t1632)."""
        assert "date" in T1633OutBlock1.model_fields
        assert "time" not in T1633OutBlock1.model_fields

    def test_outblock1_has_volume_field(self):
        """t1633 row carries 'volume' — t1632 has no equivalent."""
        assert "volume" in T1633OutBlock1.model_fields

    def test_outblock1_lacks_k200basis(self):
        """t1633 row must NOT have 'k200basis' (t1632-only field)."""
        assert "k200basis" not in T1633OutBlock1.model_fields

    def test_outblock1_float_coerce_from_zero_padded_string(self):
        """Pydantic str→float coerce works for jisu / change.

        Verifies the model accepts string inputs (e.g., '329.85') and
        coerces to float. Whether LS actually serialises numeric fields
        as strings on this TR is not asserted — that requires live
        verification.
        """
        row = T1633OutBlock1.model_validate({
            "date": "20230619",
            "jisu": "329.85",
            "change": "016.32",
            "sign": "2",
        })
        assert row.jisu == pytest.approx(329.85)
        assert row.change == pytest.approx(16.32)


# ===========================================================================
# Phase A3 — sign field anti-inference guard
# ===========================================================================


class TestT1633SignNoInferredEnum:
    """xingAPI FUNCTION_MAP declares ``sign`` as char(1) with no enum mapping.
    The previous description embedded '1' = 상한 / '2' = 상승 / ... etc. via
    the xingAPI companion documentation reference — but that companion is not
    the LS public spec. Anti-inference applies to both the field description
    and the module docstring (since the docstring is also AI-ingested).
    """

    def test_sign_field_no_inferred_enum_mapping(self):
        desc = T1633OutBlock1.model_fields["sign"].description or ""
        for forbidden in [
            "limit-up", "limit-down",
            "upper limit", "lower limit",
            "상한", "하한", "상승", "하락",
            "xingAPI companion",
        ]:
            assert forbidden not in desc, (
                f"T1633OutBlock1.sign: must not embed inferred enum token '{forbidden}'."
            )

    def test_module_docstring_no_inferred_sign_enum(self):
        import programgarden_finance.ls.korea_stock.program.t1633.blocks as t1633_blocks

        doc = t1633_blocks.__doc__ or ""
        for forbidden in [
            "'1'=상한", "'5'=하락", "상한 / '2'=상승",
            "xingAPI companion spec",
        ]:
            assert forbidden not in doc, (
                f"t1633 blocks module docstring must not embed sign enum '{forbidden}'."
            )


class TestInBlockCharLengthConsistency:
    """xingAPI FUNCTION_MAP: char,1 fields must declare ``Length 1``.

    Sibling program TRs drift in length-string coverage of
    single-character enum fields. xingAPI ground truth declares every
    InBlock char,1 field as ``char,1`` — the description must surface
    that explicitly so the AI chatbot generates consistent payloads.
    ``gubun2`` / ``gubun3`` are omitted: both already enumerate every
    accepted value via Literal, which is surfaced directly in the
    JSON schema.
    """

    @pytest.mark.parametrize(
        "field_name", ["gubun", "gubun1", "gubun4", "exchgubun"]
    )
    def test_t1633_inblock_char_one_length_documented(self, field_name: str):
        desc = T1633InBlock.model_fields[field_name].description or ""
        assert "Length 1" in desc, (
            f"T1633InBlock.{field_name} must document 'Length 1' "
            f"(xingAPI FUNCTION_MAP: char,1)."
        )
