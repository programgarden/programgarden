"""Pydantic models for LS Securities OpenAPI t1105 (주식피봇/디마크조회 / Pivot & Demark levels).

t1105 returns a single block of Pivot-style support / resistance levels and
Demark-style support / resistance levels for one Korean stock symbol. The
response is a single-shot snapshot — the LS spec available to this codebase
exposes no continuation cursor (``cts_*`` / ``idx``) and no row-count input
— so ``occurs_req`` is intentionally not implemented.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
``feedback_tr_field_metadata``):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``exchgubun`` enum mapping IS declared by LS for t1105
      ('K' = KRX, 'N' = NXT, 'U' = unified); description embeds the
      mapping. Per LS source "그외 입력값은 KRX로 처리" — other inputs
      are coerced to KRX.
    - The following are NOT declared in the source available to this
      codebase and must NOT be asserted in descriptions:
        * The exact mathematical formula used to compute ``pbot`` (피봇),
          ``offer1`` / ``supp1`` (1st resistance / support),
          ``offer2`` / ``supp2`` (2nd resistance / support),
          ``offerd`` / ``suppd`` (Demark resistance / support).
          LS publishes only the field labels — the underlying pivot /
          Demark formulas are vendor-specific and not declared.
        * The reference base used by ``stdprc`` (기준가격) — whether it
          reflects today's reference price, previous close, or another
          base.
        * Decimal scale and currency unit of all price fields.
        * Whether values are reported in KRW only or vary by exchange
          when ``exchgubun`` is ``'N'`` or ``'U'``.
    - All output price fields are LS spec ``long, 8``; consume as raw
      integers returned by LS.
"""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1105RequestHeader(BlockRequestHeader):
    """t1105 request header. Inherits the standard LS request header schema."""
    pass


class T1105ResponseHeader(BlockResponseHeader):
    """t1105 response header. Inherits the standard LS response header schema."""
    pass


class T1105InBlock(BaseModel):
    """t1105InBlock — input block for the pivot / Demark levels query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code. Length 6.",
        examples=["001200", "005930", "000660"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange division. Length 1. "
            "'K' = KRX (한국거래소), "
            "'N' = NXT (넥스트레이드), "
            "'U' = unified (통합). "
            "Pydantic validates strictly — only these three are accepted; empty string and other values are rejected. Omit the field to use the 'K' default."
        ),
        examples=["K", "N", "U"],
    )


class T1105Request(BaseModel):
    """t1105 request envelope."""

    header: T1105RequestHeader = T1105RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1105",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: Dict[Literal["t1105InBlock"], T1105InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=3,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1105",
    )


class T1105OutBlock(BaseModel):
    """t1105OutBlock — single block of pivot / Demark support & resistance levels.

    The exact mathematical formula used to compute each level (Pivot
    classical method, Demark variant, weighting, reference window) is
    NOT declared in the LS source available to this codebase. Consume
    values as returned by LS without asserting a derivation.
    """

    shcode: str = Field(
        default="",
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code echoed for the issue. Length 6.",
        examples=["001200", "005930"],
    )
    pbot: int = Field(
        default=0,
        title="피봇 (Pivot)",
        description=(
            "Pivot level (피봇) as returned by LS. Length 8. The exact "
            "pivot formula is not declared in available source — consume "
            "as returned by LS. Decimal scale and currency unit not "
            "declared in available source."
        ),
        examples=[0, 3563],
    )
    offer1: int = Field(
        default=0,
        title="1차저항 (1st resistance)",
        description=(
            "1st resistance level (1차저항) as returned by LS. Length 8. "
            "The derivation from ``pbot`` is not declared in available "
            "source — consume as returned by LS."
        ),
        examples=[0, 3771],
    )
    supp1: int = Field(
        default=0,
        title="1차지지 (1st support)",
        description=(
            "1st support level (1차지지) as returned by LS. Length 8. "
            "The derivation from ``pbot`` is not declared in available "
            "source — consume as returned by LS."
        ),
        examples=[0, 3451],
    )
    offer2: int = Field(
        default=0,
        title="2차저항 (2nd resistance)",
        description=(
            "2nd resistance level (2차저항) as returned by LS. Length 8. "
            "The derivation from ``pbot`` is not declared in available "
            "source — consume as returned by LS."
        ),
        examples=[0, 3883],
    )
    supp2: int = Field(
        default=0,
        title="2차지지 (2nd support)",
        description=(
            "2nd support level (2차지지) as returned by LS. Length 8. "
            "The derivation from ``pbot`` is not declared in available "
            "source — consume as returned by LS."
        ),
        examples=[0, 3243],
    )
    stdprc: int = Field(
        default=0,
        title="기준가격 (Reference price)",
        description=(
            "Reference price (기준가격) as returned by LS. Length 8. "
            "The reference base (today's reference price, previous close, "
            "or another) is not declared in available source — consume "
            "as returned by LS."
        ),
        examples=[0, 7182],
    )
    offerd: int = Field(
        default=0,
        title="D저항 (Demark resistance)",
        description=(
            "Demark-style resistance level (D저항) as returned by LS. "
            "Length 8. The exact Demark formula is not declared in "
            "available source — consume as returned by LS."
        ),
        examples=[0, 3827],
    )
    suppd: int = Field(
        default=0,
        title="D지지 (Demark support)",
        description=(
            "Demark-style support level (D지지) as returned by LS. "
            "Length 8. The exact Demark formula is not declared in "
            "available source — consume as returned by LS."
        ),
        examples=[0, 3507],
    )


class T1105Response(BaseModel):
    """t1105 response envelope."""

    header: Optional[T1105ResponseHeader]
    block: Optional[T1105OutBlock] = Field(
        None,
        title="피봇/디마크 블록 (Pivot / Demark block)",
        description=(
            "Single block of pivot and Demark support / resistance levels "
            "for the queried issue."
        ),
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code returned for the request.",
    )
    rsp_cd: str
    rsp_msg: str
    error_msg: Optional[str] = Field(
        None,
        title="오류메시지 (Error message)",
        description="Error message when the request failed; ``None`` on success.",
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
