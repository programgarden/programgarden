"""Pydantic models for LS Securities OpenAPI t1305 (기간별주가 / Period-based stock price query).

t1305 returns period-based (daily / weekly / monthly) OHLCV bars for a
Korean stock symbol, along with net buy/sell volumes by investor type
(foreign, institutional, individual), trade strength, and relative-to-open
/ high / low direction codes.  Pagination uses the ``date`` cursor echoed
back in ``T1305OutBlock``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
``feedback_tr_field_metadata``):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``sign`` enum mapping IS declared by LS for t1305
      (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락) and is documented inline.
    - ``h_sign`` and ``l_sign`` enum mappings ARE declared by LS
      (2=상승 / 3=보합 / 5=하락; codes 1 and 4 not present) and are
      documented inline.
    - ``o_sign`` enum mapping is NOT declared in the LS source available to
      this codebase; description carries "Enum mapping not declared in
      available source".
    - Sign conventions of ``change`` / ``o_change`` / ``h_change`` /
      ``l_change`` / ``fpvolume`` / ``covolume`` / ``ppvolume`` are NOT
      declared in the source; consume as returned by LS.
    - Time ordering of ``OutBlock1`` rows is NOT declared in the source
      available to this codebase; consume as returned by LS.
    - Currency unit of price fields is NOT declared in the source; LS
      labels ``value`` and ``marketcap`` as "(단위:백만)" — that annotation
      alone is reproduced and no further currency assertion is made.
    - ``diff`` (LS scale 6.2), ``diff_vol`` (10.2), ``chdegree`` (6.2),
      ``sojinrate`` (6.2), ``changerate`` (6.2), ``o_diff`` (6.2),
      ``h_diff`` (6.2), and ``l_diff`` (6.2) are serialized as JSON
      strings by LS in example responses (e.g., ``"0.68"``, ``"163.65"``,
      ``"-74.79"``); Pydantic coerces to float.
    - ``ex_shcode`` appears in the LS spec OutBlock definition but is
      absent from the official example response; modelled as
      ``Optional[str]`` with default ``""`` so the example response
      round-trips without error.
    - ``idx`` in InBlock is labelled "사용안함 (Space)" by LS but the
      official example sends integer ``0``; modelled as ``int`` default
      ``0`` (Pydantic coercion, no semantic assertion).
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1305RequestHeader(BlockRequestHeader):
    """t1305 request header. Inherits the standard LS request header schema."""
    pass


class T1305ResponseHeader(BlockResponseHeader):
    """t1305 response header. Inherits the standard LS response header schema."""
    pass


class T1305InBlock(BaseModel):
    """t1305InBlock — input block for the period-based stock price query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code. Length 6.",
        examples=["005930", "000660", "001200"],
    )
    dwmcode: Literal[1, 2, 3] = Field(
        ...,
        title="일주월구분 (Period type)",
        description=(
            "Period-type selector. Number, length 1. "
            "1 = daily (일), "
            "2 = weekly (주), "
            "3 = monthly (월). Required."
        ),
        examples=[1, 2, 3],
    )
    date: str = Field(
        default="",
        title="날짜 (Date continuation cursor)",
        description=(
            "Continuation cursor — empty (or a single space) on the first "
            "request, then echo back ``T1305OutBlock.date`` from the "
            "previous response for paged follow-up requests. "
            "Whether the cursor value represents the last row date or a "
            "page boundary is not declared in available LS source — treat "
            "as opaque LS-defined token. Length 8."
        ),
        examples=["", "20230605", "20240101"],
    )
    idx: int = Field(
        default=0,
        title="IDX (Index)",
        description=(
            "LS spec labels this field '사용안함 (Space)', but the official "
            "LS example request sends integer 0. Modelled as int with "
            "default 0 (Pydantic coercion). Exact semantics not declared "
            "in available source. Number, length 4."
        ),
        examples=[0],
    )
    cnt: int = Field(
        ...,
        title="건수 (Row count)",
        description=(
            "Number of rows to fetch per request. LS spec: 1 or more "
            "(Number, length 4). Required."
        ),
        examples=[1, 50, 900],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        ...,
        title="거래소구분코드 (Exchange code)",
        description=(
            "Exchange selector. Length 1. "
            "'K' = KRX, "
            "'N' = NXT (next-trade), "
            "'U' = unified (통합). "
            "Any other input is treated as KRX by LS. Required."
        ),
        examples=["K", "N", "U"],
    )


class T1305Request(BaseModel):
    """t1305 request envelope."""

    header: T1305RequestHeader = T1305RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1305",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1305InBlock"], T1305InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1305"
    )


class T1305OutBlock(BaseModel):
    """t1305OutBlock — continuation block carrying the ``date`` cursor."""

    cnt: int = Field(
        default=0,
        title="CNT (Row count)",
        description=(
            "Number of rows in the accompanying OutBlock1 array as reported "
            "by LS. Number, length 4."
        ),
        examples=[0, 1, 50],
    )
    date: str = Field(
        default="",
        title="날짜 (Date continuation cursor)",
        description=(
            "Continuation cursor for the next paged request. Pass back as "
            "``T1305InBlock.date``. Empty when no further rows are available. "
            "Whether this value represents the last row date or a page "
            "boundary is not declared in available LS source — treat as "
            "opaque LS-defined token. Length 8."
        ),
        examples=["", "20230605", "20240101"],
    )
    idx: int = Field(
        default=0,
        title="IDX (Index)",
        description=(
            "Index value returned by LS in the continuation block. "
            "Exact semantics not declared in available source. "
            "Number, length 4."
        ),
        examples=[0],
    )
    ex_shcode: Optional[str] = Field(
        default="",
        title="거래소별단축코드 (Exchange-specific short code)",
        description=(
            "Exchange-specific short code returned by LS. Length 10. "
            "Absent from the official LS example response — modelled as "
            "Optional so the example round-trips without error."
        ),
        examples=["", "001200    "],
    )


class T1305OutBlock1(BaseModel):
    """t1305OutBlock1 — one period bar row (daily / weekly / monthly).

    Time ordering of rows is NOT declared in the source available to this
    codebase; consume as returned by LS.
    """

    date: str = Field(
        default="",
        title="날짜 (Bar date)",
        description=(
            "Date of the period bar as reported by LS, observed structure "
            "YYYYMMDD (8 digits). Whether the value marks the period start, "
            "end, or another boundary is not formally declared in available "
            "LS source — consume as returned by LS. Length 8."
        ),
        examples=["20230605", "20230101", "20221231"],
    )
    open: int = Field(
        default=0,
        title="시가 (Open price)",
        description=(
            "Open price for the period. Decimal scale and currency unit "
            "not declared in available source — consume as returned by LS. "
            "Length 8."
        ),
        examples=[3660, 3685, 72000],
    )
    high: int = Field(
        default=0,
        title="고가 (High price)",
        description=(
            "High price for the period. Decimal scale and currency unit "
            "not declared in available source — consume as returned by LS. "
            "Length 8."
        ),
        examples=[3750, 3800, 75000],
    )
    low: int = Field(
        default=0,
        title="저가 (Low price)",
        description=(
            "Low price for the period. Decimal scale and currency unit "
            "not declared in available source — consume as returned by LS. "
            "Length 8."
        ),
        examples=[3645, 3600, 70000],
    )
    close: int = Field(
        default=0,
        title="종가 (Close price)",
        description=(
            "Close price for the period. Decimal scale and currency unit "
            "not declared in available source — consume as returned by LS. "
            "Length 8."
        ),
        examples=[3685, 3700, 71000],
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
            "'5' = down (하락). Enum mapping is declared by LS for t1305."
        ),
        examples=["1", "2", "3", "4", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description=(
            "Magnitude of change versus previous close. Sign convention is "
            "not declared in available LS source — consume as returned by "
            "LS. Length 8."
        ),
        examples=[0, 25, -15],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Percent change)",
        description=(
            "Percent change versus previous close (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '0.68' or "
            "'-1.20'); Pydantic auto-coerces to float."
        ),
        examples=[0.0, 0.68, -1.20],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description=(
            "Cumulative traded volume in shares for the period. "
            "Length 12."
        ),
        examples=[0, 321201, 1000000],
    )
    diff_vol: float = Field(
        default=0.0,
        title="거래증가율 (Volume change rate)",
        description=(
            "Volume change rate versus the prior period (LS scale 10.2). "
            "Formula not declared in available source. LS may serialize "
            "this value as a string (e.g., '-74.79'); Pydantic auto-coerces "
            "to float."
        ),
        examples=[0.0, -74.79, 12.34],
    )
    chdegree: float = Field(
        default=0.0,
        title="체결강도 (Trade strength)",
        description=(
            "LS-defined trade strength indicator (LS scale 6.2). "
            "Formula not declared in available source. LS may serialize "
            "this value as a string (e.g., '163.65'); Pydantic auto-coerces "
            "to float."
        ),
        examples=[0.0, 163.65, 98.74],
    )
    sojinrate: float = Field(
        default=0.0,
        title="소진율 (Foreign exhaustion rate)",
        description=(
            "Foreign ownership exhaustion rate (LS scale 6.2). "
            "Formula not declared in available source. LS may serialize "
            "this value as a string (e.g., '7.17'); Pydantic auto-coerces "
            "to float."
        ),
        examples=[0.0, 7.17, 55.30],
    )
    changerate: float = Field(
        default=0.0,
        title="회전율 (Turnover rate)",
        description=(
            "Share turnover rate for the period (LS scale 6.2). "
            "Formula not declared in available source. LS may serialize "
            "this value as a string (e.g., '0.33'); Pydantic auto-coerces "
            "to float."
        ),
        examples=[0.0, 0.33, 2.50],
    )
    fpvolume: int = Field(
        default=0,
        title="외인순매수 (Foreign net buy volume)",
        description=(
            "Foreign investor net buy volume for the period in shares. "
            "Sign convention not declared in available LS source — "
            "consume as returned by LS. Length 12."
        ),
        examples=[0, 50000, -30000],
    )
    covolume: int = Field(
        default=0,
        title="기관순매수 (Institutional net buy volume)",
        description=(
            "Institutional investor net buy volume for the period in shares. "
            "Sign convention not declared in available LS source — "
            "consume as returned by LS. Length 12."
        ),
        examples=[0, 20000, -10000],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Stock code)",
        description=(
            "6-digit Korean stock code as returned by LS in the row. "
            "Length 6."
        ),
        examples=["001200", "005930", "000660"],
    )
    value: int = Field(
        default=0,
        title="누적거래대금(단위:백만) (Cumulative trade value, unit: million)",
        description=(
            "Cumulative trade value for the period. LS label: "
            "'누적거래대금(단위:백만)'. Currency unit not further declared "
            "in available source beyond LS label annotation. Length 12."
        ),
        examples=[0, 1188, 500000],
    )
    ppvolume: int = Field(
        default=0,
        title="개인순매수 (Individual net buy volume)",
        description=(
            "Individual investor net buy volume for the period in shares. "
            "Sign convention not declared in available LS source — "
            "consume as returned by LS. Length 12."
        ),
        examples=[0, 10000, -5000],
    )
    o_sign: str = Field(
        default="",
        title="시가대비구분 (Open-relative direction code)",
        description=(
            "Direction code versus the open price. Length 1. "
            "Enum mapping not declared in available source — "
            "consume as returned by LS."
        ),
        examples=["2", "3", "5"],
    )
    o_change: int = Field(
        default=0,
        title="시가대비 (Open-relative delta)",
        description=(
            "Magnitude of change versus the open price. Sign convention is "
            "not declared in available LS source — consume as returned by "
            "LS. Length 8."
        ),
        examples=[0, 25, -10],
    )
    o_diff: float = Field(
        default=0.0,
        title="시가기준등락율 (Open-relative percent change)",
        description=(
            "Percent change versus the open price (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '0.00'); "
            "Pydantic auto-coerces to float."
        ),
        examples=[0.0, 0.68, -1.20],
    )
    h_sign: str = Field(
        default="",
        title="고가대비구분 (High-relative direction code)",
        description=(
            "Direction code versus the high price. Length 1. "
            "'2' = up (상승), "
            "'3' = unchanged (보합), "
            "'5' = down (하락). "
            "Codes 1 and 4 are not present per LS declaration. "
            "Enum mapping is declared by LS for t1305."
        ),
        examples=["2", "3", "5"],
    )
    h_change: int = Field(
        default=0,
        title="고가대비 (High-relative delta)",
        description=(
            "Magnitude of change versus the high price. Sign convention is "
            "not declared in available LS source — consume as returned by "
            "LS. Length 8."
        ),
        examples=[0, 90, -50],
    )
    h_diff: float = Field(
        default=0.0,
        title="고가기준등락율 (High-relative percent change)",
        description=(
            "Percent change versus the high price (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '2.46'); "
            "Pydantic auto-coerces to float."
        ),
        examples=[0.0, 2.46, -1.33],
    )
    l_sign: str = Field(
        default="",
        title="저가대비구분 (Low-relative direction code)",
        description=(
            "Direction code versus the low price. Length 1. "
            "'2' = up (상승), "
            "'3' = unchanged (보합), "
            "'5' = down (하락). "
            "Codes 1 and 4 are not present per LS declaration. "
            "Enum mapping is declared by LS for t1305."
        ),
        examples=["2", "3", "5"],
    )
    l_change: int = Field(
        default=0,
        title="저가대비 (Low-relative delta)",
        description=(
            "Magnitude of change versus the low price. Sign convention is "
            "not declared in available LS source — consume as returned by "
            "LS. Length 8."
        ),
        examples=[0, -15, 40],
    )
    l_diff: float = Field(
        default=0.0,
        title="저가기준등락율 (Low-relative percent change)",
        description=(
            "Percent change versus the low price (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '-0.41'); "
            "Pydantic auto-coerces to float."
        ),
        examples=[0.0, -0.41, 1.10],
    )
    marketcap: int = Field(
        default=0,
        title="시가총액(단위:백만) (Market capitalization, unit: million)",
        description=(
            "Market capitalization for the period. LS label: "
            "'시가총액(단위:백만)'. Currency unit not further declared "
            "in available source beyond LS label annotation. Length 12."
        ),
        examples=[0, 356953, 5000000],
    )


class T1305Response(BaseModel):
    """t1305 response envelope."""

    header: Optional[T1305ResponseHeader]
    cont_block: Optional[T1305OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1305OutBlock1] = Field(
        default_factory=list,
        title="기간별 시세 리스트 (Period bar rows)",
        description=(
            "List of period bar rows (daily / weekly / monthly). "
            "Time ordering not declared in available source."
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
