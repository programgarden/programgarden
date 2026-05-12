"""Pydantic models for LS Securities OpenAPI t1486 (시간별예상체결가 / Stock time-bucket expected-conclusion price).

t1486 returns the per-time-bucket expected conclusion (auction-anticipated)
price stream for a Korean stock symbol. Each row carries the expected
conclusion price, the previous-day direction code (LS-mapped enum),
percent change, expected conclusion volume, top-of-book ask/bid prices and
remaining quantities, and the originating exchange name. Pagination uses
the ``cts_time`` cursor echoed back in ``T1486OutBlock``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
``feedback_tr_field_metadata``):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``sign`` enum mapping IS declared by LS for t1486
      (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락) and is documented inline.
    - Time ordering of ``OutBlock1`` rows, sign convention of ``change``
      magnitude, the precise structure of the ``cts_time`` cursor, the
      exact session window the expected-conclusion stream covers (pre-open
      / closing auction / both), and currency unit of price fields are
      NOT declared in the source available to this codebase; consume as
      returned by LS.
    - ``diff`` (LS scale 6.2) is serialized as a JSON string by LS in
      example responses (e.g., ``"0.00"``, ``"0.55"``); Pydantic coerces
      to float.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1486RequestHeader(BlockRequestHeader):
    """t1486 request header. Inherits the standard LS request header schema."""
    pass


class T1486ResponseHeader(BlockResponseHeader):
    """t1486 response header. Inherits the standard LS response header schema."""
    pass


class T1486InBlock(BaseModel):
    """t1486InBlock — input block for the time-bucket expected-conclusion price query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code. Length 6.",
        examples=["005930", "000660", "001200"],
    )
    cts_time: str = Field(
        default="",
        title="시간CTS (Time continuation cursor)",
        description=(
            "Continuation cursor — empty (or a single space) on the first "
            "request, then echo back ``T1486OutBlock.cts_time`` from the "
            "previous response. Treat as opaque LS-defined token. Length 10."
        ),
        examples=["", "08594423", "08594423 0"],
    )
    cnt: int = Field(
        ...,
        title="조회건수 (Row count)",
        description=(
            "Number of rows to fetch per request (Number, length 4). "
            "LS example uses 20. Required."
        ),
        examples=[20, 50, 100],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        ...,
        title="거래소구분코드 (Exchange code)",
        description=(
            "Exchange selector. Length 1. "
            "'K' = KRX, "
            "'N' = NXT (next-trade), "
            "'U' = unified (통합). "
            "Pydantic validates strictly — only these three are accepted; empty string and other values are rejected. Required."
        ),
        examples=["K", "N", "U"],
    )


class T1486Request(BaseModel):
    """t1486 request envelope."""

    header: T1486RequestHeader = T1486RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1486",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1486InBlock"], T1486InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1486"
    )


class T1486OutBlock(BaseModel):
    """t1486OutBlock — continuation block carrying the ``cts_time`` cursor and exchange-keyed code."""

    cts_time: str = Field(
        default="",
        title="시간CTS (Time continuation cursor)",
        description=(
            "Continuation cursor for the next paged request. Pass back as "
            "``T1486InBlock.cts_time``. Empty when no further rows are "
            "available. Treat as opaque LS-defined token. Length 10."
        ),
        examples=["", "08594423", "08594423 0"],
    )
    ex_shcode: str = Field(
        default="",
        title="거래소별단축코드 (Exchange-keyed short code)",
        description=(
            "Exchange-prefixed short code for the queried symbol as returned "
            "by LS. Format not formally declared in available source; "
            "consume as returned by LS. Length 10."
        ),
        examples=["", "001200", "K001200"],
    )


class T1486OutBlock1(BaseModel):
    """t1486OutBlock1 — one expected-conclusion bucket row.

    Time ordering of rows is NOT declared in the source available to this
    codebase; consume as returned by LS.
    """

    chetime: str = Field(
        default="",
        title="시간 (Bucket time)",
        description=(
            "Bucket boundary time as reported by LS, observed structure "
            "``HHMMSSss`` (8 digits, last two appear to be a sub-second "
            "fraction). Whether the value marks the bucket start or end "
            "is not formally declared in available LS source — consume as "
            "returned by LS. Length 8."
        ),
        examples=["09000854", "08594423", "08593715"],
    )
    price: int = Field(
        default=0,
        title="예상체결가 (Expected conclusion price)",
        description=(
            "Expected conclusion (auction-anticipated) price for the "
            "bucket. Decimal scale and currency unit not declared in "
            "available source — consume as returned by LS. Length 8."
        ),
        examples=[3660, 3680, 3665],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Direction code versus previous close. Length 1. "
            "'1' = upper limit (상한), "
            "'2' = up (상승), "
            "'3' = unchanged (보합), "
            "'4' = lower limit (하한), "
            "'5' = down (하락). Enum mapping is declared by LS for t1486."
        ),
        examples=["1", "2", "3", "4", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description=(
            "Magnitude of expected change versus previous close. Sign "
            "convention is not declared in available LS source — consume "
            "as returned by LS. Length 8."
        ),
        examples=[0, 20, -25],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Percent change)",
        description=(
            "Percent change versus previous close in % (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '0.00' or "
            "'0.55'); Pydantic auto-coerces to float."
        ),
        examples=[0.0, 0.55, -1.20],
    )
    cvolume: int = Field(
        default=0,
        title="예상체결량 (Expected conclusion volume)",
        description=(
            "Expected conclusion (auction-anticipated) volume for the "
            "bucket in shares. Length 12."
        ),
        examples=[0, 1552, 6062],
    )
    offerho1: int = Field(
        default=0,
        title="매도호가 (Top-of-book ask price)",
        description=(
            "Best (level-1) ask price at the bucket boundary. Decimal "
            "scale and currency unit not declared in available source. "
            "Length 8."
        ),
        examples=[0, 3665, 3680],
    )
    bidho1: int = Field(
        default=0,
        title="매수호가 (Top-of-book bid price)",
        description=(
            "Best (level-1) bid price at the bucket boundary. Decimal "
            "scale and currency unit not declared in available source. "
            "Length 8."
        ),
        examples=[0, 3660, 3665],
    )
    offerrem1: int = Field(
        default=0,
        title="매도잔량 (Top-of-book ask remaining quantity)",
        description=(
            "Remaining ask (sell) quantity at the level-1 ask price in "
            "shares. Length 12."
        ),
        examples=[0, 191, 956],
    )
    bidrem1: int = Field(
        default=0,
        title="매수잔량 (Top-of-book bid remaining quantity)",
        description=(
            "Remaining bid (buy) quantity at the level-1 bid price in "
            "shares. Length 12."
        ),
        examples=[0, 1270, 8713],
    )
    exchname: str = Field(
        default="",
        title="거래소명 (Exchange name)",
        description=(
            "Originating exchange name string as returned by LS (e.g., "
            "'KRX', 'NXT'). Format not formally declared in available "
            "source; consume as returned by LS. Length 3."
        ),
        examples=["", "KRX", "NXT"],
    )


class T1486Response(BaseModel):
    """t1486 response envelope."""

    header: Optional[T1486ResponseHeader]
    cont_block: Optional[T1486OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1486OutBlock1] = Field(
        default_factory=list,
        title="시간별 예상체결가 리스트 (Per-bucket expected-conclusion rows)",
        description=(
            "List of expected-conclusion bucket rows. Time ordering not "
            "declared in available source."
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
