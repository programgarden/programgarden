"""Pydantic models for LS Securities OpenAPI t1422 (상/하한 / upper-lower limit hit screen).

t1422 returns the list of Korean stock issues currently hitting the daily
upper or lower price limit. Filters include market division (KOSPI / KOSDAQ),
prior-day vs. today flag, target-exclusion bitmasks, price/volume ranges, and
exchange division (KRX / NXT / unified). Pagination is via the ``idx`` cursor.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``jc_num`` (target-exclusion bitmask) bit semantics are NOT declared
      in the available source; consume as returned by LS.
    - ``last`` (최종진입) value semantics not declared; opaque LS-defined.
    - ``idx`` is an opaque LS-defined paging cursor; pass back verbatim.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1422RequestHeader(BlockRequestHeader):
    """t1422 request header. Inherits the standard LS request header schema."""
    pass


class T1422ResponseHeader(BlockResponseHeader):
    """t1422 response header. Inherits the standard LS response header schema."""
    pass


class T1422InBlock(BaseModel):
    """t1422InBlock — input block for the upper-lower limit hit screen."""

    qrygb: Literal["1", "2"] = Field(
        ...,
        title="조회구분 (Query mode)",
        description="Query mode. '1' = 20 issues per page (20종목씩 조회), '2' = full list (전체조회).",
        examples=["1", "2"],
    )
    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="구분 (Market division)",
        description="Market division. '0' = all, '1' = KOSPI, '2' = KOSDAQ.",
        examples=["0", "1", "2"],
    )
    jnilgubun: Literal["0", "1"] = Field(
        ...,
        title="전일구분 (Day flag)",
        description="Day flag. '0' = today (당일), '1' = previous day (전일).",
        examples=["0", "1"],
    )
    sign: Literal["1", "4"] = Field(
        ...,
        title="상하한구분 (Limit side)",
        description="Limit side. '1' = upper limit (상한), '4' = lower limit (하한).",
        examples=["1", "4"],
    )
    jc_num: int = Field(
        default=0,
        title="대상제외 비트마스크 (Exclusion bitmask)",
        description="Target-exclusion bitmask. Bit-position semantics not declared in available source; consume as returned by LS. 0 means no exclusion.",
        examples=[0],
    )
    sprice: int = Field(
        default=0,
        title="시작가격 (Start price)",
        description="Inclusive lower bound of the price filter. 0 means no lower bound. Decimal scale not declared in available source.",
        examples=[0, 1000],
    )
    eprice: int = Field(
        default=0,
        title="종료가격 (End price)",
        description="Inclusive upper bound of the price filter. 0 means no upper bound.",
        examples=[0, 100000],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Volume threshold)",
        description="Minimum cumulative volume filter in shares. 0 means no minimum.",
        examples=[0, 10000],
    )
    idx: int = Field(
        default=0,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor. 0 on first request; pass back ``idx`` from the previous response on follow-ups. Treat as opaque LS-defined token.",
        examples=[0],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description="Exchange division. 'K' = KRX, 'N' = NXT, 'U' = unified.",
        examples=["K", "N", "U"],
    )


class T1422Request(BaseModel):
    """t1422 request envelope."""

    header: T1422RequestHeader = T1422RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1422",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1422InBlock"], T1422InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1422"
    )


class T1422OutBlock(BaseModel):
    """t1422OutBlock — continuation block (record count + paging cursor)."""

    cnt: int = Field(
        ...,
        title="CNT (Record count)",
        description="Number of rows in ``OutBlock1`` for this response.",
        examples=[0, 20],
    )
    idx: int = Field(
        ...,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor for the next paged request. 0 when no further rows are available.",
        examples=[0],
    )


class T1422OutBlock1(BaseModel):
    """t1422OutBlock1 — per-issue limit-hit row."""

    hname: str = Field(
        ...,
        title="한글명 (Korean name)",
        description="Korean issue name as reported by LS.",
        examples=["삼성전자"],
    )
    price: int = Field(
        ...,
        title="현재가 (Current price)",
        description="Current price (typically equals the upper or lower limit when the row is flagged).",
        examples=[102700, 55300],
    )
    sign: str = Field(
        ...,
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention ('1'..'5').",
        examples=["1", "4"],
    )
    change: int = Field(
        ...,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of price change versus previous close.",
        examples=[18000, 0],
    )
    diff: float = Field(
        ...,
        title="등락율(%) (Change percent)",
        description="Percent change versus previous close.",
        examples=[30.0, -30.0],
    )
    volume: int = Field(
        ...,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[15000000],
    )
    diff_vol: float = Field(
        ...,
        title="거래증가율(%) (Volume change percent)",
        description="Percent change in volume versus a comparison baseline. Baseline definition not declared in available source.",
        examples=[125.5, 0.0, -10.0],
    )
    offerrem1: int = Field(
        ...,
        title="매도잔량 (Best ask quantity)",
        description="Quantity at the best ask price.",
        examples=[5000, 0],
    )
    bidrem1: int = Field(
        ...,
        title="매수잔량 (Best bid quantity)",
        description="Quantity at the best bid price.",
        examples=[3500, 0],
    )
    last: str = Field(
        ...,
        title="최종진입 (Last-entry indicator)",
        description="LS-defined last-entry indicator. Value semantics not declared in available source; consume as returned by LS.",
        examples=[""],
    )
    lmtdaycnt: int = Field(
        ...,
        title="연속 (Consecutive limit-hit days)",
        description="Number of consecutive days the issue has hit the same limit. Counting convention not declared in available source.",
        examples=[1, 5],
    )
    jnilvolume: int = Field(
        ...,
        title="전일거래량 (Previous-day volume)",
        description="Previous trading day's traded volume in shares.",
        examples=[12000000],
    )
    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    ex_shcode: str = Field(
        default="",
        title="거래소별단축코드 (Exchange-specific short code)",
        description="Exchange-resolved short code echoed for the issue. Format and semantics not declared in available source.",
        examples=[""],
    )


class T1422Response(BaseModel):
    """t1422 response envelope."""

    header: Optional[T1422ResponseHeader]
    cont_block: Optional[T1422OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1422OutBlock1] = Field(
        default_factory=list,
        title="상/하한 종목 리스트 (Limit-hit rows)",
        description="List of issues currently hitting the requested upper / lower limit.",
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
