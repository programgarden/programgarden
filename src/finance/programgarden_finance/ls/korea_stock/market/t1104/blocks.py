"""Pydantic models for LS Securities OpenAPI t1104 (주식현재가시세메모 / Stock current-quote memo).

t1104 returns a per-row memo lookup for a single Korean stock symbol. The
request carries one or more memo lookup directives in ``t1104InBlock1``
(an occurs / Object Array input). Each directive specifies a memo
category (``gubn``: 시세 / 최고저가 / Pivot / 이동평균선) plus the
sub-key (``dat1`` / ``dat2``) to fetch. The response echoes the original
``indx`` / ``gubn`` of each directive and attaches the looked-up value
in ``vals``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
``feedback_tr_field_metadata``):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``gubn`` enum mapping IS declared by LS for t1104
      (1=시세 / 2=최고저가 / 3=Pivot / 4=이동평균선); the description
      embeds the mapping.
    - ``dat1`` enum mapping IS declared by LS for t1104
      (1=시가 / 2=고가 / 3=저가 / 4=가중평균가); the mapping is
      published as a directive selector under each ``gubn`` category, but
      LS does not document which (gubn, dat1) combinations are valid —
      consume the spec mapping verbatim without inferring cross-product
      semantics.
    - ``dat2`` enum mapping IS declared by LS for t1104
      (1=당일 / 2=전일); LS publishes Length 8 for this field but the
      enum values are single characters per the spec.
    - ``exchgubun`` ('K' = KRX, 'N' = NXT, 'U' = unified). Per LS source
      "그외 입력값은 KRX로 처리" — other inputs are coerced to KRX.
    - Unit, decimal scale, format (numeric string vs. raw integer), and
      validity-per-category semantics of the output ``vals`` field are
      NOT declared in available source — consume as returned by LS.
    - The interpretation of ``dat1`` when ``gubn`` selects Pivot (3) or
      이동평균선 (4) is NOT declared in available source.
    - ``nrec`` is serialized as a string by LS (Length 2); pass as a
      stringified integer (e.g., ``"04"``) or empty string when no
      occurs rows are supplied.
"""

from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1104RequestHeader(BlockRequestHeader):
    """t1104 request header. Inherits the standard LS request header schema."""
    pass


class T1104ResponseHeader(BlockResponseHeader):
    """t1104 response header. Inherits the standard LS response header schema."""
    pass


class T1104InBlock(BaseModel):
    """t1104InBlock — input header for the current-quote memo query."""

    code: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code. Length 6.",
        examples=["005930", "000660", "078020"],
    )
    nrec: str = Field(
        default="",
        title="건수 (Occurs record count)",
        description=(
            "Number of memo lookup directives in the accompanying "
            "``t1104InBlock1`` list, serialized as a string of Length 2 "
            "(e.g., '04'). Empty string is allowed when no directives "
            "are supplied."
        ),
        examples=["", "01", "04"],
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


class T1104InBlock1(BaseModel):
    """t1104InBlock1 — per-directive memo lookup row (Object Array input)."""

    indx: str = Field(
        ...,
        title="인덱스 (Occurs index)",
        description=(
            "Occurs index for this directive, starting from 0. Length 1. "
            "The response's ``t1104OutBlock1.indx`` echoes this value so "
            "callers can re-correlate responses to the original input row."
        ),
        examples=["0", "1", "2"],
    )
    gubn: Literal["1", "2", "3", "4"] = Field(
        ...,
        title="조건구분 (Memo category)",
        description=(
            "Memo category selector. Length 1. "
            "'1' = quote (시세), "
            "'2' = period high/low (최고저가), "
            "'3' = Pivot (피봇), "
            "'4' = moving average (이동평균선)."
        ),
        examples=["1", "2", "3", "4"],
    )
    dat1: Literal["1", "2", "3", "4"] = Field(
        ...,
        title="데이타1 (Sub-key 1)",
        description=(
            "Sub-key 1 selector. Length 1. "
            "'1' = open (시가), "
            "'2' = high (고가), "
            "'3' = low (저가), "
            "'4' = weighted average (가중평균가). "
            "Interpretation under ``gubn`` = 3 (Pivot) or 4 (이동평균선) "
            "is not declared in available source."
        ),
        examples=["1", "2", "3", "4"],
    )
    dat2: Literal["1", "2"] = Field(
        ...,
        title="데이타2 (Sub-key 2)",
        description=(
            "Sub-key 2 selector. LS spec lists Length 8 but only publishes "
            "single-character enum values. "
            "'1' = today (당일), "
            "'2' = previous day (전일)."
        ),
        examples=["1", "2"],
    )


class T1104Request(BaseModel):
    """t1104 request envelope (header + body + setup options).

    The body is a combined dict with two keys: ``t1104InBlock`` (header
    fields) and ``t1104InBlock1`` (occurs list of memo lookup directives).
    Pattern mirrors o3127.
    """

    header: T1104RequestHeader = T1104RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1104",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: Dict[
        Literal["t1104InBlock", "t1104InBlock1"],
        Union[T1104InBlock, Optional[List[T1104InBlock1]]],
    ] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description=(
            "Combined input body with 't1104InBlock' (header) and "
            "'t1104InBlock1' (per-directive list)."
        ),
    )
    options: SetupOptions = SetupOptions(
        rate_limit_count=3,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1104",
    )


class T1104OutBlock(BaseModel):
    """t1104OutBlock — output header echoing the count of returned rows."""

    nrec: str = Field(
        default="",
        title="출력건수 (Output record count)",
        description=(
            "Number of rows returned in ``t1104OutBlock1``, serialized "
            "as a string of Length 2."
        ),
        examples=["00", "01", "04"],
    )


class T1104OutBlock1(BaseModel):
    """t1104OutBlock1 — one returned memo row.

    Each row echoes ``indx`` / ``gubn`` from the corresponding input
    directive and attaches the looked-up value in ``vals``. Row ordering
    within the response list is NOT declared in available source.
    """

    indx: str = Field(
        default="",
        title="인덱스 (Occurs index echo)",
        description=(
            "Echo of the input directive's ``t1104InBlock1.indx``. "
            "Length 1."
        ),
        examples=["0", "1", "2"],
    )
    gubn: Literal["1", "2", "3", "4"] = Field(
        default="1",
        title="조건구분 (Memo category echo)",
        description=(
            "Echo of the input directive's ``t1104InBlock1.gubn``. "
            "Length 1. "
            "'1' = quote (시세), "
            "'2' = period high/low (최고저가), "
            "'3' = Pivot (피봇), "
            "'4' = moving average (이동평균선)."
        ),
        examples=["1", "2", "3", "4"],
    )
    vals: str = Field(
        default="",
        title="출력값 (Memo value)",
        description=(
            "Memo value for this row as returned by LS. Length 8. "
            "Unit, decimal scale, and serialization format are not "
            "declared in available source — consume as returned by LS."
        ),
        examples=["", "00079800", "00078900"],
    )


class T1104Response(BaseModel):
    """t1104 response envelope."""

    header: Optional[T1104ResponseHeader]
    summary_block: Optional[T1104OutBlock] = Field(
        None,
        title="출력 헤더 (Summary block)",
        description=(
            "Summary block echoing the count of returned memo rows. "
            "t1104 does not support pagination."
        ),
    )
    block: List[T1104OutBlock1] = Field(
        default_factory=list,
        title="시세메모 리스트 (Memo rows)",
        description=(
            "List of returned memo rows. Row ordering is not declared "
            "in available source."
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
