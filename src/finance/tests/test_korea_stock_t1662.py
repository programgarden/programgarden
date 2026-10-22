"""Unit tests for t1662 시간대별프로그램매매추이차트 (Korea Stock Program Trading Time-Chart).

Covers:
    - blocks.py — Pydantic input/output validation. Crucial regressions:
      ``gubun`` Literal is ``"0"/"1"`` (matches t1632 / t1633 / t1636 /
      t1637; does NOT match t1631 ``"1"/"2"`` nor t1640 2-digit codes).
    - InBlock policy: every input field is Required (no inferred defaults).
      ``exchgubun`` differs from t1640 here — t1662 makes it Required to
      avoid silently sending an unverified server-side default.
    - OutBlock policy: defensive defaults for parsing LS responses that may
      omit fields. ``sign`` uses ``Optional[Literal[...]] = None`` instead
      of ``default="3"`` to avoid silently inferring "보합" / unchanged.
    - TrT1662._build_response — happy / HTTP error / exception paths,
      verified against the LS official example payload (Object Array).
    - TestT1662InBlockGubunAntiCopyPaste — anti-copy-paste guard rejecting
      every sibling-TR ``gubun`` value.
    - TestT1662ResponseBlockIsList — anti-copy-paste guard against t1640's
      ``Optional[T1640OutBlock]`` single-object pattern. t1662 returns an
      Object Array.
    - TestProgramAliasNoCollision — Korean alias must NOT collide with
      t1632's ``시간대별프로그램매매추이`` alias (no '차트' suffix).
    - OccursReqAbstract NON-inheritance guard — t1662 has no continuation
      paging (single response covers the chart).
    - Program domain class + KoreaStock entry point — Korean alias bridge
      (시간대별프로그램매매추이차트) and chained call.
    - Top-level export — ``from programgarden_finance import t1662`` and
      ``t1662.T1662InBlock`` must remain accessible.
"""

from __future__ import annotations

from typing import Any, Dict, List, Type, get_args, get_origin

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.program import Program
from programgarden_finance.ls.korea_stock.program.t1662 import TrT1662
from programgarden_finance.ls.korea_stock.program.t1662.blocks import (
    T1662InBlock,
    T1662OutBlock,
    T1662Request,
    T1662Response,
    T1662ResponseHeader,
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


def _make_request(**overrides: Any) -> T1662Request:
    body = T1662InBlock(
        gubun=overrides.pop("gubun", "0"),
        gubun1=overrides.pop("gubun1", "0"),
        gubun3=overrides.pop("gubun3", "0"),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1662Request(body={"t1662InBlock": body})


def _make_response_headers(**overrides: Any) -> Dict[str, Any]:
    headers: Dict[str, Any] = {
        "Content-Type": "application/json; charset=utf-8",
        "tr_cd": "t1662",
        "tr_cont": "N",
        "tr_cont_key": "",
    }
    headers.update(overrides)
    return headers


# LS official example response payload — Object Array of two rows.
# Mix of raw int and zero-padded string per LS serialisation patterns.
LS_EXAMPLE_OUTBLOCK_ROWS: List[Dict[str, Any]] = [
    {
        "time": "102600",
        "k200jisu": "343.75",
        "sign": "2",
        "change": "001.08",
        "k200basis": "000.27",
        "tot3": 27896,
        "tot1": 786684,
        "tot2": 758788,
        "cha3": 12081,
        "cha1": 17718,
        "cha2": 5637,
        "bcha3": 15815,
        "bcha1": 768966,
        "bcha2": 753151,
        "volume": 24,
    },
    {
        "time": "090000",
        "k200jisu": "342.67",
        "sign": "3",
        "change": "000.00",
        "k200basis": "002.08",
        "tot3": -7637,
        "tot1": 12327,
        "tot2": 19964,
        "cha3": 0,
        "cha1": 0,
        "cha2": 0,
        "bcha3": -7637,
        "bcha1": 12327,
        "bcha2": 19964,
        "volume": 0,
    },
]


# ---------------------------------------------------------------------------
# 1. URL registration
# ---------------------------------------------------------------------------


class TestKOREAStockProgramURL:
    """t1662 reuses the existing ``/stock/program`` URL alongside its siblings."""

    def test_korea_stock_program_url_exposed(self):
        assert hasattr(URLS, "KOREA_STOCK_PROGRAM_URL")
        assert URLS.KOREA_STOCK_PROGRAM_URL.endswith("/stock/program")


# ---------------------------------------------------------------------------
# 2. T1662InBlock — 4 enum + every field Required (no inferred defaults)
# ---------------------------------------------------------------------------


class TestT1662InBlock:
    @pytest.mark.parametrize("gubun", ["0", "1"])
    def test_accepts_valid_gubun(self, gubun: str):
        block = T1662InBlock(gubun=gubun, gubun1="0", gubun3="0", exchgubun="K")
        assert block.gubun == gubun

    @pytest.mark.parametrize("gubun1", ["0", "1"])
    def test_accepts_valid_gubun1(self, gubun1: str):
        block = T1662InBlock(gubun="0", gubun1=gubun1, gubun3="0", exchgubun="K")
        assert block.gubun1 == gubun1

    @pytest.mark.parametrize("gubun3", ["0", "1"])
    def test_accepts_valid_gubun3(self, gubun3: str):
        block = T1662InBlock(gubun="0", gubun1="0", gubun3=gubun3, exchgubun="K")
        assert block.gubun3 == gubun3

    @pytest.mark.parametrize("exchgubun", ["K", "N", "U"])
    def test_accepts_valid_exchgubun(self, exchgubun: str):
        block = T1662InBlock(gubun="0", gubun1="0", gubun3="0", exchgubun=exchgubun)
        assert block.exchgubun == exchgubun

    def test_gubun_is_required(self):
        with pytest.raises(ValidationError):
            T1662InBlock(gubun1="0", gubun3="0", exchgubun="K")  # type: ignore[call-arg]

    def test_gubun1_is_required(self):
        with pytest.raises(ValidationError):
            T1662InBlock(gubun="0", gubun3="0", exchgubun="K")  # type: ignore[call-arg]

    def test_gubun3_is_required(self):
        with pytest.raises(ValidationError):
            T1662InBlock(gubun="0", gubun1="0", exchgubun="K")  # type: ignore[call-arg]

    def test_exchgubun_is_required_no_inferred_default(self):
        """Policy: t1662 InBlock has no inferred defaults — every field must be
        provided explicitly. exchgubun differs from t1640 (which defaults to 'K')
        because the LS spec does not publish a default value for this field."""
        with pytest.raises(ValidationError):
            T1662InBlock(gubun="0", gubun1="0", gubun3="0")  # type: ignore[call-arg]

    @pytest.mark.parametrize("bad_exch", ["K1", "X", "", "k", "n"])
    def test_rejects_invalid_exchgubun(self, bad_exch: str):
        with pytest.raises(ValidationError):
            T1662InBlock(gubun="0", gubun1="0", gubun3="0", exchgubun=bad_exch)


# ---------------------------------------------------------------------------
# 3. CRITICAL — anti-copy-paste guard for ``gubun``
# ---------------------------------------------------------------------------


class TestT1662InBlockGubunAntiCopyPaste:
    """t1662 ``gubun`` MUST reject every sibling-TR ``gubun`` value that is
    not part of t1662's domain ('0' / '1').

    sibling TR domains:
        - t1631 → '1' / '2' (KOSPI / KOSDAQ; '2' is not a t1662 value)
        - t1640 → '11' / '12' / '13' / '21' / '22' / '23' (2-digit combined)

    Note: '1' is shared between t1631 (KOSDAQ) and t1662 (KOSDAQ) — the
    semantic happens to align so it is accepted. We guard the values that
    would silently mismatch.
    """

    @pytest.mark.parametrize(
        "bad_gubun",
        ["2", "3", "11", "12", "13", "21", "22", "23", "10", "30", ""],
    )
    def test_rejects_sibling_tr_gubun_values(self, bad_gubun: str):
        with pytest.raises(ValidationError):
            T1662InBlock(gubun=bad_gubun, gubun1="0", gubun3="0", exchgubun="K")


# ---------------------------------------------------------------------------
# 4. T1662OutBlock — LS payload decode + zero-padded string + defaults
# ---------------------------------------------------------------------------


class TestT1662OutBlock:
    LS_EXAMPLE_ROW = LS_EXAMPLE_OUTBLOCK_ROWS[0]

    def test_decodes_ls_example_row_full(self):
        row = T1662OutBlock.model_validate(self.LS_EXAMPLE_ROW)
        assert row.time == "102600"
        assert row.k200jisu == 343.75
        assert row.sign == "2"
        assert row.change == 1.08
        assert row.k200basis == 0.27
        assert row.tot3 == 27896
        assert row.tot1 == 786684
        assert row.tot2 == 758788
        assert row.cha3 == 12081
        assert row.cha1 == 17718
        assert row.cha2 == 5637
        assert row.bcha3 == 15815
        assert row.bcha1 == 768966
        assert row.bcha2 == 753151
        assert row.volume == 24

    def test_decodes_negative_zero_padded_basis(self):
        payload = {**self.LS_EXAMPLE_ROW, "k200basis": "-001.20"}
        row = T1662OutBlock.model_validate(payload)
        assert row.k200basis == -1.20

    def test_decodes_negative_tot3_int(self):
        row = T1662OutBlock.model_validate(LS_EXAMPLE_OUTBLOCK_ROWS[1])
        assert row.tot3 == -7637
        assert row.bcha3 == -7637

    def test_zero_padded_string_int_coerces(self):
        payload = {**self.LS_EXAMPLE_ROW, "tot1": "000000786684"}
        row = T1662OutBlock.model_validate(payload)
        assert row.tot1 == 786684
        assert isinstance(row.tot1, int)

    def test_defaults_when_fields_absent(self):
        """Defensive defaults — LS may omit fields. Defaults are zero values
        (NOT inferred from LS spec; explicit defensive parsing only)."""
        row = T1662OutBlock.model_validate({})
        assert row.time == ""
        assert row.k200jisu == 0.0
        assert row.change == 0.0
        assert row.k200basis == 0.0
        assert row.tot3 == 0
        assert row.tot1 == 0
        assert row.tot2 == 0
        assert row.cha3 == 0
        assert row.cha1 == 0
        assert row.cha2 == 0
        assert row.bcha3 == 0
        assert row.bcha1 == 0
        assert row.bcha2 == 0
        assert row.volume == 0


# ---------------------------------------------------------------------------
# 5. CRITICAL — sign field is Optional[Literal[...]] = None (no inferred '3')
# ---------------------------------------------------------------------------


class TestT1662OutBlockSignField:
    """``sign`` MUST be ``Optional[Literal["1","2","3","4","5"]] = None``.

    Defaulting to '3' (보합 / unchanged) silently infers a market state that
    LS did not publish. Defaulting to None is an unambiguous "LS did not
    report sign for this row" sentinel that is NOT one of the five
    LS-published values.
    """

    @pytest.mark.parametrize("sign", ["1", "2", "3", "4", "5"])
    def test_accepts_all_five_published_sign_values(self, sign: str):
        row = T1662OutBlock.model_validate({"sign": sign})
        assert row.sign == sign

    def test_default_sign_is_None_not_3(self):
        row = T1662OutBlock.model_validate({})
        assert row.sign is None, (
            "sign default MUST be None (LS-omitted sentinel), "
            "NOT '3' (which would silently infer 보합 / unchanged)"
        )

    def test_None_is_NOT_a_published_sign_value(self):
        """Sanity guard — None is the absence sentinel, not a member of the
        five LS-published values."""
        info = T1662OutBlock.model_fields["sign"]
        ann_args = get_args(info.annotation)
        # Optional[Literal[...]] → Union[Literal[...], None]
        # The Literal subargs:
        literal_args: tuple = ()
        for a in ann_args:
            if get_origin(a) is None and a is type(None):
                continue
            literal_args = get_args(a) or literal_args
        assert set(literal_args) == {"1", "2", "3", "4", "5"}

    @pytest.mark.parametrize("bad_sign", ["0", "6", "9", "A", " ", "11"])
    def test_rejects_invalid_sign_values(self, bad_sign: str):
        with pytest.raises(ValidationError):
            T1662OutBlock.model_validate({"sign": bad_sign})

    def test_empty_string_is_rejected_not_treated_as_None(self):
        """LS may emit ``""`` for missing sign — but per Pydantic Literal
        validation '' is NOT one of the published values. The defensive
        path is to OMIT the field (→ None). This guards against silently
        accepting ''."""
        with pytest.raises(ValidationError):
            T1662OutBlock.model_validate({"sign": ""})


# ---------------------------------------------------------------------------
# 6. CRITICAL — type annotation regression guard (int vs float)
# ---------------------------------------------------------------------------


class TestT1662OutBlockTypeAnnotations:
    """Field type annotations follow LS public spec lengths.

    LS scale 6.2 fields → Pydantic float
    Length-12 long fields → Pydantic int
    sign (length 1, enum) → Optional[Literal[...]]
    """

    INT_FIELDS = [
        "tot3", "tot1", "tot2",
        "cha3", "cha1", "cha2",
        "bcha3", "bcha1", "bcha2",
        "volume",
    ]
    FLOAT_FIELDS = ["k200jisu", "change", "k200basis"]

    @pytest.mark.parametrize("field_name", INT_FIELDS)
    def test_long_fields_annotated_as_int(self, field_name: str):
        info = T1662OutBlock.model_fields[field_name]
        assert info.annotation is int, (
            f"{field_name} must be int (LS length 12)"
        )

    @pytest.mark.parametrize("field_name", FLOAT_FIELDS)
    def test_float_fields_annotated_as_float(self, field_name: str):
        info = T1662OutBlock.model_fields[field_name]
        assert info.annotation is float, (
            f"{field_name} must be float (LS scale 6.2)"
        )

    def test_time_annotated_as_str(self):
        info = T1662OutBlock.model_fields["time"]
        assert info.annotation is str

    def test_sign_annotated_as_optional_literal(self):
        info = T1662OutBlock.model_fields["sign"]
        # Optional[Literal[...]] resolves to Union[Literal[...], None]
        ann_args = get_args(info.annotation)
        assert type(None) in ann_args, "sign must be Optional (None permitted)"


# ---------------------------------------------------------------------------
# 7. T1662Response — Object Array envelope
# ---------------------------------------------------------------------------


class TestT1662Response:
    def test_full_response_with_object_array_block(self):
        response = T1662Response.model_validate(
            {
                "header": _make_response_headers(),
                "block": LS_EXAMPLE_OUTBLOCK_ROWS,
                "rsp_cd": "00000",
                "rsp_msg": "OK",
                "status_code": 200,
            }
        )
        assert isinstance(response.block, list)
        assert len(response.block) == 2
        assert response.block[0].time == "102600"
        assert response.block[1].time == "090000"

    def test_empty_block_defaults_to_empty_list(self):
        response = T1662Response.model_validate(
            {"rsp_cd": "00000", "rsp_msg": "no data"}
        )
        assert response.block == []
        assert isinstance(response.block, list)

    def test_block_is_NOT_optional_single_object(self):
        """Anti-copy-paste guard against t1640's ``Optional[T1640OutBlock]``
        single-object pattern."""
        info = T1662Response.model_fields["block"]
        # Object Array → default_factory=list (not None)
        assert info.is_required() is False
        # Default must be an empty list, NOT None.
        assert info.default is not None or info.default_factory is list


# ---------------------------------------------------------------------------
# 8. CRITICAL — Response.block annotation is List (not single object)
# ---------------------------------------------------------------------------


class TestT1662ResponseBlockIsList:
    """T1662Response.block annotation MUST be ``List[T1662OutBlock]``.

    Anti-copy-paste guard against t1640's ``Optional[T1640OutBlock]`` pattern
    — copy-pasting that pattern here would silently lose all rows after
    the first one.
    """

    def test_block_annotation_is_list_origin(self):
        info = T1662Response.model_fields["block"]
        origin = get_origin(info.annotation)
        assert origin is list, (
            f"T1662Response.block must be List[T1662OutBlock], "
            f"got origin={origin}"
        )

    def test_block_inner_type_is_outblock(self):
        info = T1662Response.model_fields["block"]
        args = get_args(info.annotation)
        assert args == (T1662OutBlock,), (
            f"T1662Response.block inner type must be T1662OutBlock, got {args}"
        )


# ---------------------------------------------------------------------------
# 9. TrT1662._build_response — happy / HTTP error / exception
# ---------------------------------------------------------------------------


class _FakeResp:
    def __init__(self, status: int):
        self.status_code = status
        self.status = status


class TestTrT1662BuildResponse:
    def test_happy_path_with_object_array(self):
        tr = TrT1662(_make_request())
        result = tr._build_response(
            _FakeResp(200),
            {
                "t1662OutBlock": LS_EXAMPLE_OUTBLOCK_ROWS,
                "rsp_cd": "00000",
                "rsp_msg": "OK",
            },
            _make_response_headers(),
            None,
        )
        assert isinstance(result, T1662Response)
        assert result.status_code == 200
        assert isinstance(result.block, list)
        assert len(result.block) == 2
        assert result.block[0].volume == 24
        assert result.rsp_cd == "00000"
        assert result.error_msg is None

    def test_happy_path_empty_block(self):
        tr = TrT1662(_make_request())
        result = tr._build_response(
            _FakeResp(200),
            {"t1662OutBlock": [], "rsp_cd": "00000", "rsp_msg": "no data"},
            _make_response_headers(),
            None,
        )
        assert result.block == []
        assert result.error_msg is None

    def test_http_4xx_returns_error(self):
        tr = TrT1662(_make_request())
        result = tr._build_response(
            _FakeResp(401),
            {"rsp_cd": "9001", "rsp_msg": "unauthorized"},
            _make_response_headers(),
            None,
        )
        assert result.status_code == 401
        assert result.error_msg is not None
        assert "401" in result.error_msg
        assert "unauthorized" in result.error_msg
        # Header NOT parsed on error status; block remains empty list.
        assert result.header is None
        assert result.block == []

    def test_http_5xx_returns_error(self):
        tr = TrT1662(_make_request())
        result = tr._build_response(
            _FakeResp(503),
            {},
            _make_response_headers(),
            None,
        )
        assert result.status_code == 503
        assert result.error_msg is not None
        assert "503" in result.error_msg
        assert result.block == []

    def test_exception_path_sets_error_msg(self):
        tr = TrT1662(_make_request())
        exc = RuntimeError("boom")
        result = tr._build_response(None, {}, None, exc)
        assert result.error_msg is not None
        assert "boom" in result.error_msg
        assert result.block == []
        assert result.header is None


# ---------------------------------------------------------------------------
# 10. CRITICAL — TrT1662 must NOT expose continuation paging
# ---------------------------------------------------------------------------


class TestTrT1662NoOccursReq:
    """t1662 returns the entire chart in a single response (no cursor).
    Inheriting OccursReqAbstract or defining occurs_req would create a
    bogus paging surface that would silently never advance.
    """

    def test_inherits_tr_request_abstract(self):
        tr = TrT1662(_make_request())
        assert isinstance(tr, TRRequestAbstract)

    def test_does_not_inherit_occurs_req_abstract(self):
        tr = TrT1662(_make_request())
        assert not isinstance(tr, OccursReqAbstract)

    def test_no_occurs_req_method(self):
        tr = TrT1662(_make_request())
        assert not hasattr(tr, "occurs_req")
        assert not hasattr(tr, "occurs_req_async")

    def test_class_does_not_inherit_occurs_req(self):
        assert not issubclass(TrT1662, OccursReqAbstract)


# ---------------------------------------------------------------------------
# 11. Program domain class — Korean alias bridge
# ---------------------------------------------------------------------------


class TestProgramDomain:
    def test_program_t1662_alias_is_korean_alias(self):
        """Class-level identity contract."""
        assert Program.t1662 is Program.시간대별프로그램매매추이차트

    def test_program_t1662_returns_tr_instance(self):
        prog = Program(token_manager=_make_token_manager())
        body = T1662InBlock(gubun="0", gubun1="0", gubun3="0", exchgubun="K")
        tr = prog.t1662(body=body)
        assert isinstance(tr, TrT1662)

    def test_program_requires_token_manager(self):
        with pytest.raises(ValueError):
            Program(token_manager=None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 12. CRITICAL — Korean alias must NOT collide with t1632
# ---------------------------------------------------------------------------


class TestProgramAliasNoCollision:
    """t1632 already uses the alias ``시간대별프로그램매매추이`` (no '차트' suffix).
    t1662's alias MUST end with '차트' to avoid silently overwriting t1632.
    """

    def test_t1632_and_t1662_aliases_are_distinct_functions(self):
        assert Program.시간대별프로그램매매추이 is not Program.시간대별프로그램매매추이차트

    def test_t1632_alias_resolves_to_t1632(self):
        assert Program.시간대별프로그램매매추이 is Program.t1632

    def test_t1662_alias_resolves_to_t1662(self):
        assert Program.시간대별프로그램매매추이차트 is Program.t1662


# ---------------------------------------------------------------------------
# 13. KoreaStock entry point — chain via Korean / English aliases
# ---------------------------------------------------------------------------


class TestKoreaStockProgramEntry:
    def test_entry_chain_via_korean_aliases(self):
        ks = KoreaStock(token_manager=_make_token_manager())
        body = T1662InBlock(gubun="0", gubun1="0", gubun3="0", exchgubun="K")
        tr = ks.프로그램매매().시간대별프로그램매매추이차트(body=body)
        assert isinstance(tr, TrT1662)

    def test_entry_chain_via_english_attrs(self):
        ks = KoreaStock(token_manager=_make_token_manager())
        body = T1662InBlock(gubun="1", gubun1="1", gubun3="0", exchgubun="K")
        tr = ks.program().t1662(body=body)
        assert isinstance(tr, TrT1662)


# ---------------------------------------------------------------------------
# 14. Top-level export
# ---------------------------------------------------------------------------


class TestTopLevelExport:
    def test_top_level_t1662_module_import(self):
        from programgarden_finance import t1662 as t1662_module

        assert t1662_module is not None

    def test_top_level_t1662_exposes_inblock(self):
        from programgarden_finance import t1662 as t1662_module
        from programgarden_finance.ls.korea_stock.program.t1662 import (
            T1662InBlock as T1662InBlockDirect,
        )

        assert t1662_module.T1662InBlock is T1662InBlockDirect


# ---------------------------------------------------------------------------
# 15. Field(examples=[...]) — TypeAdapter validation + non-empty guard
# ---------------------------------------------------------------------------


class TestFieldExamplesValidate:
    """Every Field(examples=[...]) value must pass through TypeAdapter and
    every InBlock / OutBlock field must declare at least one example.
    """

    @staticmethod
    def _iter_field_examples(klass: Type[BaseModel]):
        for name, info in klass.model_fields.items():
            for ex in info.examples or []:
                yield klass.__name__, name, info.annotation, ex

    @pytest.mark.parametrize(
        "klass_name,field,annotation,example",
        list(_iter_field_examples.__func__(T1662InBlock))
        + list(_iter_field_examples.__func__(T1662OutBlock)),
    )
    def test_examples_validate_through_type_adapter(
        self, klass_name: str, field: str, annotation: Any, example: Any
    ):
        adapter = TypeAdapter(annotation)
        adapter.validate_python(example)

    def test_t1662_inblock_all_fields_have_examples(self):
        for name, info in T1662InBlock.model_fields.items():
            assert info.examples, f"T1662InBlock.{name} missing examples"

    def test_t1662_outblock_all_fields_have_examples(self):
        for name, info in T1662OutBlock.model_fields.items():
            assert info.examples, f"T1662OutBlock.{name} missing examples"


# ---------------------------------------------------------------------------
# 16. ModelFields regression — silent rename / removal guard
# ---------------------------------------------------------------------------


T1662_INBLOCK_FIELDS = ["gubun", "gubun1", "gubun3", "exchgubun"]
T1662_OUTBLOCK_FIELDS = [
    "time",
    "k200jisu",
    "sign",
    "change",
    "k200basis",
    "tot3",
    "tot1",
    "tot2",
    "cha3",
    "cha1",
    "cha2",
    "bcha3",
    "bcha1",
    "bcha2",
    "volume",
]


class TestModelFieldsRegression:
    @pytest.mark.parametrize("field_name", T1662_INBLOCK_FIELDS)
    def test_inblock_field_present(self, field_name: str):
        assert field_name in T1662InBlock.model_fields

    @pytest.mark.parametrize("field_name", T1662_OUTBLOCK_FIELDS)
    def test_outblock_field_present(self, field_name: str):
        assert field_name in T1662OutBlock.model_fields

    def test_inblock_field_count_exactly_4(self):
        """4 fields per LS public spec: gubun / gubun1 / gubun3 / exchgubun."""
        assert set(T1662InBlock.model_fields.keys()) == set(T1662_INBLOCK_FIELDS)
        assert len(T1662InBlock.model_fields) == 4

    def test_outblock_field_count_exactly_15(self):
        """15 fields per LS public spec — silent additions / removals fail here."""
        assert set(T1662OutBlock.model_fields.keys()) == set(T1662_OUTBLOCK_FIELDS)
        assert len(T1662OutBlock.model_fields) == 15

    def test_all_inblock_fields_required_no_inferred_defaults(self):
        """Policy: every InBlock field is Required (no inferred defaults)."""
        for name, info in T1662InBlock.model_fields.items():
            assert info.is_required(), (
                f"T1662InBlock.{name} must be Required (no inferred defaults policy)"
            )

    def test_outblock_sign_default_is_None_not_inferred_string(self):
        """sign default MUST be None (LS-omitted sentinel), NOT '3' (which
        would silently infer 보합)."""
        info = T1662OutBlock.model_fields["sign"]
        assert info.default is None
