"""Unit tests for t1640 프로그램매매종합조회미니 (Korea Stock Program Trading Mini Snapshot).

Covers:
    - blocks.py — Pydantic input/output validation. Crucial regressions:
      ``gubun`` Literal is the unique 2-digit encoding
      ``"11"/"12"/"13"/"21"/"22"/"23"`` (NOT ``"0"/"1"`` like
      t1632/t1633/t1636/t1637 nor ``"1"/"2"`` like t1631).
    - TrT1640._build_response — happy / HTTP error / exception paths,
      verified against the LS official example payload.
    - TestT1640InBlockGubunAntiCopyPaste — anti-copy-paste guard rejecting
      every sibling-TR ``gubun`` value.
    - TestT1640OutBlockTypeAnnotations — xingAPI FUNCTION_MAP type-mapping
      regression guard. The six ``*value`` / ``*valdiff`` fields are
      ``double`` (float) per xingAPI; t1631 / t1636 sibling TRs declare
      the same Korean labels as ``long`` (int) and copy-paste would
      silently mismatch the LS spec.
    - TestFieldExamplesValidate — every ``Field(examples=[...])`` value
      must validate through ``TypeAdapter(field_info.annotation)``, and
      every InBlock / OutBlock field must declare at least one example.
    - OccursReqAbstract NON-inheritance guard — t1640 has no continuation
      paging, so this is a hard regression boundary.
    - Program domain class + KoreaStock entry point — Korean alias bridge
      (프로그램매매종합조회미니) and chained call.
    - Top-level export — ``from programgarden_finance import t1640`` and
      ``t1640.T1640InBlock`` must remain accessible.
"""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.korea_stock import KoreaStock
from programgarden_finance.ls.korea_stock.program import Program
from programgarden_finance.ls.korea_stock.program.t1640 import TrT1640
from programgarden_finance.ls.korea_stock.program.t1640.blocks import (
    T1640InBlock,
    T1640OutBlock,
    T1640Request,
    T1640Response,
    T1640ResponseHeader,
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


def _make_request(**overrides: Any) -> T1640Request:
    body = T1640InBlock(
        gubun=overrides.pop("gubun", "11"),
        exchgubun=overrides.pop("exchgubun", "K"),
    )
    return T1640Request(body={"t1640InBlock": body})


def _make_response_headers(**overrides: Any) -> Dict[str, Any]:
    headers: Dict[str, Any] = {
        "Content-Type": "application/json; charset=utf-8",
        "tr_cd": "t1640",
        "tr_cont": "N",
        "tr_cont_key": "",
    }
    headers.update(overrides)
    return headers


# LS official example response payload (mix of raw int and zero-padded string)
LS_EXAMPLE_OUTBLOCK: Dict[str, Any] = {
    "sundiff": 6,
    "bidvaldiff": "000000000250",
    "bidvalue": "000000786684",
    "offervalue": "000000758788",
    "basis": "000.01",
    "offervolume": 36452,
    "offerdiff": 10,
    "bidvolume": 39833,
    "volume": 3381,
    "sunvaldiff": "-00000000100",
    "biddiff": 16,
    "value": "000000027896",
    "offervaldiff": "000000000350",
}


# ---------------------------------------------------------------------------
# 1. URL registration
# ---------------------------------------------------------------------------


class TestKOREAStockProgramURL:
    """t1640 reuses the existing ``/stock/program`` URL alongside its siblings."""

    def test_korea_stock_program_url_exposed(self):
        assert hasattr(URLS, "KOREA_STOCK_PROGRAM_URL")
        assert URLS.KOREA_STOCK_PROGRAM_URL.endswith("/stock/program")


# ---------------------------------------------------------------------------
# 2. T1640InBlock — Literal + default
# ---------------------------------------------------------------------------


class TestT1640InBlock:
    @pytest.mark.parametrize("gubun", ["11", "12", "13", "21", "22", "23"])
    def test_accepts_all_valid_gubun(self, gubun: str):
        block = T1640InBlock(gubun=gubun)
        assert block.gubun == gubun

    def test_default_exchgubun_is_K(self):
        block = T1640InBlock(gubun="11")
        assert block.exchgubun == "K"

    @pytest.mark.parametrize("exchgubun", ["K", "N", "U"])
    def test_accepts_all_valid_exchgubun(self, exchgubun: str):
        block = T1640InBlock(gubun="11", exchgubun=exchgubun)
        assert block.exchgubun == exchgubun

    def test_gubun_is_required(self):
        with pytest.raises(ValidationError):
            T1640InBlock()  # type: ignore[call-arg]

    @pytest.mark.parametrize("bad_exch", ["K1", "X", "", "k"])
    def test_rejects_invalid_exchgubun(self, bad_exch: str):
        with pytest.raises(ValidationError):
            T1640InBlock(gubun="11", exchgubun=bad_exch)


# ---------------------------------------------------------------------------
# 3. CRITICAL — anti-copy-paste guard for ``gubun``
# ---------------------------------------------------------------------------


class TestT1640InBlockGubunAntiCopyPaste:
    """t1640 ``gubun`` MUST reject every sibling-TR ``gubun`` value.

    sibling TR domains:
        - t1631 → '1' (거래소) / '2' (코스닥)
        - t1632 / t1633 / t1636 / t1637 → '0' (거래소) / '1' (코스닥)

    Accidentally pasting any of these instead of t1640's 2-digit
    encoding would either be silently rejected by Pydantic (current
    behaviour, guarded here) or worse: silently accepted by LS server-side
    with unspecified semantics. The Pydantic Literal stops the bug at
    request build time.
    """

    @pytest.mark.parametrize("bad_gubun", ["0", "1", "2", "3", "10", "30", ""])
    def test_rejects_sibling_tr_gubun_values(self, bad_gubun: str):
        with pytest.raises(ValidationError):
            T1640InBlock(gubun=bad_gubun, exchgubun="K")


# ---------------------------------------------------------------------------
# 4. T1640OutBlock — LS payload decode + string coerce
# ---------------------------------------------------------------------------


class TestT1640OutBlock:
    LS_EXAMPLE_PAYLOAD = LS_EXAMPLE_OUTBLOCK

    def test_decodes_ls_example_payload(self):
        block = T1640OutBlock.model_validate(self.LS_EXAMPLE_PAYLOAD)
        assert block.basis == 0.01
        assert block.bidvalue == 786684
        assert block.value == 27896
        assert block.sunvaldiff == -100
        assert block.offervaldiff == 350
        assert block.bidvaldiff == 250
        assert block.offervalue == 758788
        assert block.sundiff == 6
        assert block.volume == 3381

    def test_sundiff_and_sunvaldiff_are_distinct_fields(self):
        """LS shares the Korean label '순매수증감' between two distinct fields."""
        block = T1640OutBlock.model_validate(self.LS_EXAMPLE_PAYLOAD)
        # sundiff: long, 8 → int
        assert block.sundiff == 6
        # sunvaldiff: double, 12.0 → float
        assert block.sunvaldiff == -100.0
        assert block.sundiff != block.sunvaldiff

    def test_double_fields_decode_as_float(self):
        """xingAPI declares 6 *value/*valdiff fields as double, 12.0 → Pydantic float."""
        block = T1640OutBlock.model_validate(self.LS_EXAMPLE_PAYLOAD)
        for field in (
            "offervalue",
            "bidvalue",
            "value",
            "offervaldiff",
            "bidvaldiff",
            "sunvaldiff",
        ):
            assert isinstance(getattr(block, field), float), (
                f"{field} must decode as float (xingAPI: double, 12.0)"
            )

    def test_long_fields_decode_as_int(self):
        block = T1640OutBlock.model_validate(self.LS_EXAMPLE_PAYLOAD)
        for field in (
            "offervolume",
            "bidvolume",
            "volume",
            "offerdiff",
            "biddiff",
            "sundiff",
        ):
            assert isinstance(getattr(block, field), int), (
                f"{field} must decode as int (xingAPI: long, 8)"
            )

    def test_basis_decodes_as_float(self):
        block = T1640OutBlock.model_validate(self.LS_EXAMPLE_PAYLOAD)
        assert isinstance(block.basis, float)
        assert block.basis == 0.01

    def test_negative_zero_padded_string_decodes(self):
        """LS encodes negatives as '-00000000100'."""
        block = T1640OutBlock.model_validate(self.LS_EXAMPLE_PAYLOAD)
        assert block.sunvaldiff == -100.0

    def test_default_values_when_fields_absent(self):
        block = T1640OutBlock.model_validate({})
        assert block.offervolume == 0
        assert block.value == 0.0
        assert block.basis == 0.0

    def test_basis_negative_decodes(self):
        payload = {**self.LS_EXAMPLE_PAYLOAD, "basis": "-001.20"}
        block = T1640OutBlock.model_validate(payload)
        assert block.basis == -1.20


# ---------------------------------------------------------------------------
# 5. T1640Response — full envelope + empty block
# ---------------------------------------------------------------------------


class TestT1640Response:
    def test_full_response_validates(self):
        response = T1640Response.model_validate(
            {
                "header": _make_response_headers(),
                "block": LS_EXAMPLE_OUTBLOCK,
                "rsp_cd": "00000",
                "rsp_msg": "OK",
                "status_code": 200,
            }
        )
        assert response.block is not None
        assert response.block.value == 27896
        assert response.rsp_cd == "00000"

    def test_block_is_optional_single_object(self):
        """Empty-data response — block must default to None, not an empty list."""
        response = T1640Response.model_validate(
            {
                "rsp_cd": "00000",
                "rsp_msg": "no data",
                "status_code": 200,
            }
        )
        assert response.block is None

    def test_block_field_is_not_a_list(self):
        """Anti-copy-paste guard against t1631/t1636/t1637 ``List[OutBlock1]``."""
        info = T1640Response.model_fields["block"]
        annotation = info.annotation
        annotation_str = str(annotation)
        assert "List" not in annotation_str and "list" not in annotation_str, (
            f"T1640Response.block must be Optional[T1640OutBlock] (single object), "
            f"got {annotation_str}"
        )


# ---------------------------------------------------------------------------
# 6. TrT1640._build_response — happy / HTTP error / exception
# ---------------------------------------------------------------------------


class _FakeResp:
    def __init__(self, status: int):
        self.status_code = status
        self.status = status


class TestTrT1640BuildResponse:
    def test_happy_path(self):
        tr = TrT1640(_make_request())
        result = tr._build_response(
            _FakeResp(200),
            {
                "t1640OutBlock": LS_EXAMPLE_OUTBLOCK,
                "rsp_cd": "00000",
                "rsp_msg": "OK",
            },
            _make_response_headers(),
            None,
        )
        assert isinstance(result, T1640Response)
        assert result.status_code == 200
        assert result.block is not None
        assert result.block.value == 27896
        assert result.rsp_cd == "00000"
        assert result.error_msg is None

    def test_http_4xx_returns_error(self):
        tr = TrT1640(_make_request())
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
        # Header NOT parsed on error status.
        assert result.header is None
        assert result.block is None

    def test_http_5xx_returns_error(self):
        tr = TrT1640(_make_request())
        result = tr._build_response(
            _FakeResp(503),
            {},
            _make_response_headers(),
            None,
        )
        assert result.status_code == 503
        assert result.error_msg is not None
        assert "503" in result.error_msg
        assert result.block is None

    def test_exception_path_sets_error_msg(self):
        tr = TrT1640(_make_request())
        exc = RuntimeError("boom")
        result = tr._build_response(None, {}, None, exc)
        assert result.error_msg is not None
        assert "boom" in result.error_msg
        assert result.block is None
        assert result.header is None


# ---------------------------------------------------------------------------
# 7. CRITICAL — TrT1640 must NOT expose continuation paging
# ---------------------------------------------------------------------------


class TestTrT1640NoOccursReq:
    """t1640 has no IDXCTS / cursor continuation. Inheriting OccursReqAbstract
    or defining occurs_req would create a bogus paging surface that would
    silently never advance.
    """

    def test_inherits_tr_request_abstract(self):
        tr = TrT1640(_make_request())
        assert isinstance(tr, TRRequestAbstract)

    def test_does_not_inherit_occurs_req_abstract(self):
        tr = TrT1640(_make_request())
        assert not isinstance(tr, OccursReqAbstract)

    def test_no_occurs_req_method(self):
        tr = TrT1640(_make_request())
        assert not hasattr(tr, "occurs_req")
        assert not hasattr(tr, "occurs_req_async")

    def test_class_does_not_inherit_occurs_req(self):
        assert not issubclass(TrT1640, OccursReqAbstract)


# ---------------------------------------------------------------------------
# 8. Program domain class — Korean alias bridge
# ---------------------------------------------------------------------------


class TestProgramDomain:
    def test_program_t1640_alias_is_korean_alias(self):
        """class-level identity contract."""
        assert Program.t1640 is Program.프로그램매매종합조회미니

    def test_program_t1640_returns_tr_instance(self):
        prog = Program(token_manager=_make_token_manager())
        tr = prog.t1640(body=T1640InBlock(gubun="11"))
        assert isinstance(tr, TrT1640)

    def test_program_requires_token_manager(self):
        with pytest.raises(ValueError):
            Program(token_manager=None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 9. KoreaStock entry point — chain via Korean aliases
# ---------------------------------------------------------------------------


class TestKoreaStockProgramEntry:
    def test_entry_chain_returns_tr(self):
        ks = KoreaStock(token_manager=_make_token_manager())
        tr = ks.프로그램매매().프로그램매매종합조회미니(body=T1640InBlock(gubun="21"))
        assert isinstance(tr, TrT1640)

    def test_entry_chain_via_english_attrs(self):
        ks = KoreaStock(token_manager=_make_token_manager())
        tr = ks.program().t1640(body=T1640InBlock(gubun="11"))
        assert isinstance(tr, TrT1640)

    def test_entry_chain_default_exchgubun(self):
        ks = KoreaStock(token_manager=_make_token_manager())
        tr = ks.프로그램매매().프로그램매매종합조회미니(body=T1640InBlock(gubun="13"))
        # Default exchgubun is 'K'.
        body = tr.request_data.body["t1640InBlock"]
        assert body.exchgubun == "K"
        assert body.gubun == "13"


# ---------------------------------------------------------------------------
# 10. Top-level export
# ---------------------------------------------------------------------------


class TestTopLevelExport:
    def test_top_level_t1640_module_import(self):
        from programgarden_finance import t1640 as t1640_module

        assert t1640_module is not None

    def test_top_level_t1640_exposes_inblock(self):
        from programgarden_finance import t1640 as t1640_module

        # ``t1640`` here is the package module — accessing its ``blocks`` submodule
        # must yield the same T1640InBlock class as direct import.
        from programgarden_finance.ls.korea_stock.program.t1640 import (
            T1640InBlock as T1640InBlockDirect,
        )

        assert t1640_module.T1640InBlock is T1640InBlockDirect


# ---------------------------------------------------------------------------
# 11. Field(examples=[...]) — TypeAdapter validation + non-empty guard
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
        list(_iter_field_examples.__func__(T1640InBlock))
        + list(_iter_field_examples.__func__(T1640OutBlock)),
    )
    def test_examples_validate_through_type_adapter(
        self, klass_name: str, field: str, annotation: Any, example: Any
    ):
        adapter = TypeAdapter(annotation)
        adapter.validate_python(example)

    def test_t1640_inblock_all_fields_have_examples(self):
        for name, info in T1640InBlock.model_fields.items():
            assert info.examples, f"T1640InBlock.{name} missing examples"

    def test_t1640_outblock_all_fields_have_examples(self):
        for name, info in T1640OutBlock.model_fields.items():
            assert info.examples, f"T1640OutBlock.{name} missing examples"


# ---------------------------------------------------------------------------
# 12. ModelFields regression — silent rename / removal guard
# ---------------------------------------------------------------------------


T1640_OUTBLOCK_FIELDS = [
    "offervolume",
    "bidvolume",
    "volume",
    "offerdiff",
    "biddiff",
    "sundiff",
    "basis",
    "offervalue",
    "bidvalue",
    "value",
    "offervaldiff",
    "bidvaldiff",
    "sunvaldiff",
]


class TestModelFieldsRegression:
    @pytest.mark.parametrize("field_name", T1640_OUTBLOCK_FIELDS)
    def test_outblock_field_present(self, field_name: str):
        assert field_name in T1640OutBlock.model_fields

    def test_outblock_field_count(self):
        """Exactly 13 fields per LS public spec — silent additions / removals fail here."""
        assert len(T1640OutBlock.model_fields) == 13

    def test_inblock_field_count(self):
        """Exactly 2 fields: gubun + exchgubun."""
        assert set(T1640InBlock.model_fields.keys()) == {"gubun", "exchgubun"}


# ---------------------------------------------------------------------------
# 13. CRITICAL — xingAPI FUNCTION_MAP type-mapping regression guard
# ---------------------------------------------------------------------------


class TestT1640OutBlockTypeAnnotations:
    """xingAPI FUNCTION_MAP ground-truth regression guard.

    Sibling TRs (t1631 / t1636) declare the same Korean labels (매도금액 /
    매수금액 / 순매수금액) as ``long`` (int). t1640 declares them as
    ``double`` (float). Silent type drift if someone copy-pastes from a
    sibling — this guard fails immediately.
    """

    LONG_FIELDS = [
        "offervolume",
        "bidvolume",
        "volume",
        "offerdiff",
        "biddiff",
        "sundiff",
    ]
    DOUBLE_FIELDS = [
        "offervalue",
        "bidvalue",
        "value",
        "offervaldiff",
        "bidvaldiff",
        "sunvaldiff",
    ]

    @pytest.mark.parametrize("field_name", LONG_FIELDS)
    def test_long_fields_annotated_as_int(self, field_name: str):
        """xingAPI: long, 8 → Pydantic int."""
        info = T1640OutBlock.model_fields[field_name]
        assert info.annotation is int, (
            f"{field_name} must be int (xingAPI: long, 8)"
        )

    @pytest.mark.parametrize("field_name", DOUBLE_FIELDS)
    def test_double_fields_annotated_as_float(self, field_name: str):
        """xingAPI: double, 12.0 → Pydantic float.

        WARNING: t1631 / t1636 sibling TRs use ``long`` (int) for the same
        Korean labels. Anti-copy-paste guard.
        """
        info = T1640OutBlock.model_fields[field_name]
        assert info.annotation is float, (
            f"{field_name} must be float (xingAPI: double, 12.0). "
            f"Do NOT copy from t1631 / t1636 *value fields (which are long)."
        )

    def test_basis_annotated_as_float(self):
        """xingAPI: float, 6.2 → Pydantic float."""
        info = T1640OutBlock.model_fields["basis"]
        assert info.annotation is float
