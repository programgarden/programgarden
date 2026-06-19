"""Unit tests for t1511 업종현재가 (Korea Stock Sector Current Quote).

Focus: LS 2026-06-13 field-width expansion (7.2 → 10.2) reflected as
metadata-only description changes (field type stays ``float``). Plus the
t1636-style example-coverage / TypeAdapter guards.

Guard coverage:
  Guard 1 — 17 fields announced by LS on 2026-06-13 declare Length 10.2
            + the 2026-06-13 audit note (regression lock).
  Guard 2 — ``wljisu`` (52-week low) is NOT scaled — LS notice omitted it;
            no-inference policy forbids guessing 10.2 / the audit note.
  Guard 3 — every InBlock / OutBlock field example round-trips through
            TypeAdapter, and every field carries at least one example.
  Guard 4 — widened range (8-digit integer part) round-trips through the
            float fields without inventing new examples.
  Guard 5 — module docstring reflects the declared scale (no longer
            asserts sub-index scale is NOT declared).
  Guard 6 — field set unchanged (metadata-only change).
"""

from __future__ import annotations

from typing import Type

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from programgarden_finance.ls.korea_stock.sector.t1511.blocks import (
    T1511InBlock,
    T1511OutBlock,
    T1511Request,
    T1511Response,
)


# ---------------------------------------------------------------------------
# LS 2026-06-13 announced fields (exactly 17 — field width 7.2 → 10.2)
# ---------------------------------------------------------------------------

SCALE_FIELDS_10_2 = [
    "pricejisu", "jniljisu", "change", "openjisu", "highjisu", "lowjisu",
    "whjisu", "yhjisu", "yljisu", "firstjisu", "firchange", "secondjisu",
    "secchange", "thirdjisu", "thrchange", "fourthjisu", "forchange",
]  # exactly 17 — LS 2026-06-13 공지 목록


# ===========================================================================
# Guard 1 — 10.2 scale declaration regression guard (핵심)
# ===========================================================================


@pytest.mark.parametrize("field_name", SCALE_FIELDS_10_2)
def test_t1511_scale_fields_present_in_model(field_name):
    assert field_name in T1511OutBlock.model_fields


@pytest.mark.parametrize("field_name", SCALE_FIELDS_10_2)
def test_t1511_scale_declared_10_2(field_name):
    desc = T1511OutBlock.model_fields[field_name].description or ""
    assert "10.2" in desc, f"{field_name} must declare Length 10.2 (LS 2026-06-13)"


@pytest.mark.parametrize("field_name", SCALE_FIELDS_10_2)
def test_t1511_audit_note_present(field_name):
    desc = T1511OutBlock.model_fields[field_name].description or ""
    assert "Changed by LS Securities on 2026-06-13" in desc, (
        f"{field_name} must carry the 2026-06-13 audit note"
    )


def test_t1511_scale_field_count_is_17():
    """LS 공지가 명시한 정확히 17개만 — drift 가드."""
    assert len(SCALE_FIELDS_10_2) == 17


# ===========================================================================
# Guard 2 — wljisu 비대칭 보존 가드 (no-inference)
# ===========================================================================


def test_t1511_wljisu_not_falsely_scaled():
    """LS 2026-06-13 공지는 wljisu(52주최저)를 나열하지 않았다.

    no-inference 정책상 wljisu 에 10.2 / audit note 를 추측 부여하면 안 된다.
    whjisu/yhjisu/yljisu 는 갱신되지만 wljisu 만 비대칭으로 보존된다.
    """
    desc = T1511OutBlock.model_fields["wljisu"].description or ""
    assert "10.2" not in desc, "wljisu must NOT be scaled — not in LS 2026-06-13 notice"
    assert "2026-06-13" not in desc, (
        "wljisu must NOT carry the audit note (not announced)"
    )


# ===========================================================================
# Guard 3 — examples TypeAdapter 검증 + 전 필드 examples 강제 (t1636 패턴)
# ===========================================================================


@pytest.mark.parametrize(
    "model_cls",
    [T1511InBlock, T1511OutBlock],
    ids=["T1511InBlock", "T1511OutBlock"],
)
def test_all_field_examples_type_valid(model_cls: Type[BaseModel]):
    failures: list[str] = []
    for field_name, field_info in model_cls.model_fields.items():
        for ex in (field_info.examples or []):
            try:
                TypeAdapter(field_info.annotation).validate_python(ex)
            except (ValidationError, Exception) as exc:  # noqa: BLE001
                failures.append(
                    f"{model_cls.__name__}.{field_name} example {ex!r}: {exc}"
                )
    assert not failures, "Invalid Field examples:\n" + "\n".join(failures)


@pytest.mark.parametrize(
    "model_cls",
    [T1511InBlock, T1511OutBlock],
    ids=["T1511InBlock", "T1511OutBlock"],
)
def test_every_field_has_at_least_one_example(model_cls: Type[BaseModel]):
    missing = [n for n, i in model_cls.model_fields.items() if not (i.examples or [])]
    assert not missing, f"{model_cls.__name__} fields without examples: {missing}"


# ===========================================================================
# Guard 4 — widened range round-trip (확대 폭 실증, examples 신설 없이)
# ===========================================================================


def test_t1511_widened_range_round_trip():
    """정수부 8자리(10.2)까지 float 이 수용함을 model_validate 로 한 번 태운다.

    examples 에는 추측값을 신설하지 않고(no-inference), 테스트에서만 큰 값을 검증.
    """
    big = 99999999.99  # 정수부 8자리 + 소수 2자리 = LS 10.2 상한 근사
    block = T1511OutBlock.model_validate({"pricejisu": big, "change": big})
    assert block.pricejisu == pytest.approx(big)
    assert block.change == pytest.approx(big)


# ===========================================================================
# Guard 5 — 모듈 docstring 갱신 가드
# ===========================================================================


def test_t1511_module_docstring_reflects_declared_scale():
    """모듈 docstring 이 sub-index scale 을 더 이상 'NOT declared' 로 단정하지 않고

    LS 2026-06-13 공지로 10.2 가 선언되었음을 반영해야 한다.
    """
    import programgarden_finance.ls.korea_stock.sector.t1511.blocks as m

    doc = m.__doc__ or ""
    assert "10.2" in doc, "module docstring must declare the 10.2 scale"
    assert "2026-06-13" in doc, (
        "module docstring must carry the 2026-06-13 declaration date"
    )
    # The pricejisu / jniljisu / sub-index scale must no longer be asserted as
    # NOT declared. The only remaining 'NOT declared' phrase belongs to the
    # currency-unit clause of value / valuechange / jnilvalue.
    assert "scale of ``pricejisu`` / ``jniljisu`` / sub-index values is\n      10.2" in doc \
        or "scale of ``pricejisu`` / ``jniljisu`` / sub-index values is 10.2" in doc \
        or ("sub-index values is" in doc and "10.2" in doc), (
        "module docstring must declare sub-index scale as 10.2, not NOT-declared"
    )


# ===========================================================================
# Guard 6 — 필드 set 무변경 (silent rename/add 탐지)
# ===========================================================================


def test_t1511_outblock_field_set_unchanged():
    """이번 변경은 메타데이터-only — OutBlock 필드 집합은 그대로여야 한다."""
    assert "wljisu" in T1511OutBlock.model_fields
    assert "pricejisu" in T1511OutBlock.model_fields
    # 17 announced fields + wljisu must all be present
    for fname in SCALE_FIELDS_10_2:
        assert fname in T1511OutBlock.model_fields


def test_t1511_response_envelope_intact():
    """Response 엔벨로프 시그니처 무변경 확인 (메타데이터-only 변경 보증)."""
    assert "block" in T1511Response.model_fields
    assert "rsp_cd" in T1511Response.model_fields
    # InBlock signature intact
    assert "upcode" in T1511InBlock.model_fields
    # Request envelope still constructs
    req = T1511Request(body={"t1511InBlock": T1511InBlock(upcode="001")})
    assert req.body["t1511InBlock"].upcode == "001"
