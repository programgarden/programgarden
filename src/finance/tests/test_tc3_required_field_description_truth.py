"""Regression guard against absence vocabulary on TC3's required field descriptions.

Why this test exists (2026-09-12 LS 브로커 필드 의미 확인 후속):
    Every field on ``TC3RealResponseBody`` is declared ``Field(...)`` —
    i.e. **required**. A required key is always present in a validated body;
    what varies is only its *value* (often the empty string ``''`` or
    ``'0'``). Descriptions that say a field is "not provided" / "제공되지
    않음" / "Conditionally provided" push consumers toward ``hasattr()`` or
    ``is None`` checks that can never fire on a validated body, so the real
    empty-value case (``== ''`` / ``== '0'``) silently goes unhandled.

    ``TC3RealResponse.body`` itself is ``Optional[...]`` (``real_base``
    passes ``body=None`` when the frame carries no body or validation
    fails), so ``None`` checks remain correct for the **body object** — but
    never for individual fields inside a body that validated.

The two existing metadata guards do not cover this:
    - ``test_field_metadata_coverage.py`` reads ``examples`` / ``title``,
      never ``description``.
    - ``test_literal_field_docstring_truth.py`` only scans
      ``Literal[...]``-typed fields (TC3's fields are all ``str``).

Run only this module:

    cd src/finance && pytest tests/test_tc3_required_field_description_truth.py -v
"""

from __future__ import annotations

import re
from typing import List, Tuple

import pytest

from programgarden_finance.ls.overseas_futureoption.real.TC3.blocks import (
    TC3RealResponseBody,
)


# Phrases that describe a *missing key*. On an all-required model they are
# false: the key is always there, only the value is empty.
_ABSENCE_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("미제공", re.compile("미제공")),
    ("제공되지 않", re.compile(r"제공되지\s*않")),
    ("not provided", re.compile(r"not\s+provided", re.IGNORECASE)),
    ("absent", re.compile(r"\babsent\b", re.IGNORECASE)),
    # The exact framing removed on 2026-09-12: "Conditionally provided:" reads
    # as "the key may be omitted"; the truthful wording is
    # "Conditionally populated" + "== '' / == '0'" guidance.
    ("conditionally provided", re.compile(r"conditionally\s+provided", re.IGNORECASE)),
)


def _offending_phrases(text: str) -> List[str]:
    return [label for label, pattern in _ABSENCE_PATTERNS if pattern.search(text)]


def _required_fields() -> List[Tuple[str, str]]:
    """[(field_name, description)] for every required field of the response body."""
    out: List[Tuple[str, str]] = []
    for name, info in TC3RealResponseBody.model_fields.items():
        if not info.is_required():
            continue
        out.append((name, info.description or ""))
    return out


def test_all_response_body_fields_are_required():
    """Premise of this guard: the TC3 push body has no optional field.

    If this ever fails, the "always present, only the value is empty"
    reasoning below no longer holds for the newly-optional field and the
    absence-vocabulary rule must be revisited for it (do not just delete
    this assertion).
    """
    optional = [
        name
        for name, info in TC3RealResponseBody.model_fields.items()
        if not info.is_required()
    ]
    assert optional == [], (
        f"TC3RealResponseBody gained optional field(s): {optional}. "
        "The required-field description rule assumes every key is always present."
    )
    # Upstream TC3 schema size, pinned so a silent field add/drop is reviewed.
    assert len(TC3RealResponseBody.model_fields) == 37, (
        "TC3RealResponseBody field count changed from 37 to "
        f"{len(TC3RealResponseBody.model_fields)} — review the schema change."
    )


@pytest.mark.parametrize(
    ("field_name", "description"),
    _required_fields(),
    ids=[name for name, _ in _required_fields()],
)
def test_required_field_description_has_no_absence_vocabulary(field_name, description):
    """A required field's description must not claim the key can be missing."""
    offending = _offending_phrases(description)
    assert not offending, (
        f"TC3RealResponseBody.{field_name} description uses absence vocabulary "
        f"{offending}, but the field is required (the key is always present on a "
        "validated body). Describe the empty *value* instead — e.g. "
        "\"Conditionally populated … 판별은 hasattr / is None 이 아니라 "
        "== '' / == '0' 으로 하라\".\n"
        f"      description: {description!r}"
    )


def test_detector_fires_on_known_bad_wording_as_positive_control():
    """Sanity: the scanner is not vacuous — it catches each banned phrasing."""
    samples = {
        "미제공": "신규 주문에서는 미제공.",
        "제공되지 않": "신규 주문에서는 제공되지 않는다.",
        "not provided": "Not provided on new orders.",
        "absent": "The key is absent for outright fills.",
        "conditionally provided": "Conditionally provided: blank on new orders.",
    }
    for expected_label, text in samples.items():
        assert expected_label in _offending_phrases(text), (
            f"detector missed {expected_label!r} in {text!r}"
        )
    # Negative control: the truthful replacement wording must pass.
    good = (
        "Conditionally populated: '' / '0' on new (신규) orders. 필드는 스키마상 "
        "항상 존재(required)하므로 판별은 hasattr / ``is None`` 이 아니라 "
        "``== ''`` / ``== '0'`` 으로 하라."
    )
    assert _offending_phrases(good) == [], (
        f"detector false-positive on truthful wording: {_offending_phrases(good)}"
    )
