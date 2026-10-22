"""Pydantic models for LS Securities OpenAPI t1109 (시간외체결량 / Off-hours execution volume).

t1109 returns off-hours per-trade rows for a Korean stock symbol — the
single-price (시간외 단일가) and after-hours close (시간외 종가) tape.
Each row carries the trade time, last price, previous-day direction code,
percent change, trade strength, and quantity / cumulative volume.
Pagination is via the ``dan_chetime`` + ``idx`` pair echoed back in
``T1109OutBlock``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, sign convention, ``dan_sign`` enum
      mapping, ``chdegree`` formula, and time ordering of ``OutBlock1``
      rows are NOT declared in the source available to this codebase;
      consume values as returned by LS.
    - ``dan_chetime`` and ``idx`` together form an opaque LS-defined
      continuation cursor; pass back verbatim on follow-up requests.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1109RequestHeader(BlockRequestHeader):
    """t1109 request header. Inherits the standard LS request header schema."""
    pass


class T1109ResponseHeader(BlockResponseHeader):
    """t1109 response header. Inherits the standard LS response header schema."""
    pass


class T1109InBlock(BaseModel):
    """t1109InBlock — input block for the off-hours execution-volume query."""

    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code. Length 6.",
        examples=["005930", "000660", "001200"],
    )
    dan_chetime: str = Field(
        default="",
        title="체결CTS (Trade time continuation cursor)",
        description=(
            "Continuation cursor — pass back ``dan_chetime`` from the previous "
            "response's ``T1109OutBlock.ctschetime``. Empty on the first "
            "request. Treat as opaque LS-defined token. Length 10."
        ),
        examples=["", "1640306509"],
    )
    idx: int = Field(
        default=0,
        title="IDX (Continuation index)",
        description=(
            "IDXCTS continuation index (Number, length 4). Pass 0 on the "
            "first request; on subsequent calls reuse the ``idx`` returned "
            "in ``T1109OutBlock`` to fetch the next page."
        ),
        examples=[0, 312],
    )


class T1109Request(BaseModel):
    """t1109 request envelope."""

    header: T1109RequestHeader = T1109RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1109",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1109InBlock"], T1109InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1109"
    )


class T1109OutBlock(BaseModel):
    """t1109OutBlock — continuation block (echoes ``dan_chetime`` + ``idx``)."""

    ctsshcode: str = Field(
        default="",
        title="종목CTS (Stock code continuation cursor)",
        description="Echo of the requested short code for paging context. Length 6.",
        examples=["", "005930"],
    )
    ctschetime: str = Field(
        default="",
        title="체결CTS (Trade time continuation cursor)",
        description=(
            "Continuation cursor for the next paged request. Empty when no "
            "further rows are available. Treat as opaque LS-defined token. "
            "Length 10."
        ),
        examples=["", "1610309356"],
    )
    idx: int = Field(
        default=0,
        title="IDX (Continuation index)",
        description=(
            "Continuation index for paging. Feed back into "
            "``T1109InBlock.idx`` for the next page. A value of 0 indicates "
            "no further pages."
        ),
        examples=[0, 312],
    )


class T1109OutBlock1(BaseModel):
    """t1109OutBlock1 — off-hours per-trade row.

    Time ordering of rows is NOT declared in the source available to this
    codebase; consume as returned by LS.
    """

    dan_chetime: str = Field(
        default="",
        title="시간 (Off-hours trade time)",
        description=(
            "Off-hours trade time as reported by LS. Length 10, observed "
            "structure ``HHMMSS`` (first 6 chars) + 4-digit suffix. The "
            "suffix is either a sub-second component (0000~9999, finer than "
            "standard millisecond) or a per-second trade-sequence counter — "
            "the precise unit is not formally declared in available LS "
            "source, so consume as an opaque ordering key. String "
            "lexicographic order matches chronological order."
        ),
        examples=["1800300943", "1640306509", "1610309356"],
    )
    dan_price: int = Field(
        default=0,
        title="현재가 (Off-hours trade price)",
        description=(
            "Off-hours trade price for this row. Decimal scale and currency "
            "unit not declared in available source — consume as returned by "
            "LS. Length 8."
        ),
        examples=[3660, 3665, 3675],
    )
    dan_sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Direction code versus previous close. Length 1. The LS spec for "
            "t1109 does not publish an enum mapping for this field — consume "
            "the raw value as reported by LS without assuming any symbol "
            "mapping."
        ),
        examples=["2", "3", "5"],
    )
    dan_change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description=(
            "Magnitude of change versus previous close. Sign convention not "
            "declared in available source. Length 8."
        ),
        examples=[0, 5, 15],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Percent change)",
        description=(
            "Percent change versus previous close in % (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '000.14' or "
            "'-00.41'); Pydantic auto-coerces to float."
        ),
        examples=[0.0, 0.14, -0.41],
    )
    dan_cvolume: int = Field(
        default=0,
        title="체결량 (Off-hours trade quantity)",
        description="Off-hours trade quantity in shares for this row. Length 8.",
        examples=[1, 27, 500, 1002],
    )
    chdegree: float = Field(
        default=0.0,
        title="체결강도 (Trade strength)",
        description=(
            "LS-defined trade strength indicator in % (LS scale 9.2). "
            "Formula not declared in available source. LS may serialize this "
            "value as a string (e.g., '000000.00'); Pydantic auto-coerces to "
            "float."
        ),
        examples=[0.0, 105.32, 98.74],
    )
    dan_volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares as of this row. Length 12.",
        examples=[2, 141, 1791],
    )


class T1109Response(BaseModel):
    """t1109 response envelope."""

    header: Optional[T1109ResponseHeader]
    cont_block: Optional[T1109OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1109OutBlock1] = Field(
        default_factory=list,
        title="시간외 체결 리스트 (Off-hours per-trade rows)",
        description=(
            "List of off-hours per-trade rows. Time ordering not declared in "
            "available source."
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
