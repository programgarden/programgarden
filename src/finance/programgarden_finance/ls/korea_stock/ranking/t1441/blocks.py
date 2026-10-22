"""Pydantic models for LS Securities OpenAPI t1441 (등락율상위 / price-change ranking).

t1441 returns the Korean stock issues ranked by intraday price-change percentage,
filtered by market division (KOSPI / KOSDAQ), direction (gainers / losers /
unchanged), today vs. previous-day mode, target-exclusion bitmasks, price /
volume thresholds, and exchange division (KRX / NXT / unified). Pagination is
via the ``idx`` cursor.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``jc_num`` / ``jc_num2`` (target-exclusion bitmasks) bit-position
      semantics are NOT declared in the available source; consume as
      returned by LS.
    - Decimal scale of ``price`` / ``change`` / ``open`` / ``high`` / ``low``
      / ``value`` / ``total`` is NOT declared in available source; consume
      as returned by LS.
    - ``voldiff`` (거래량대비율) baseline (vs. previous day, vs. average,
      etc.) is NOT declared in available source; consume as returned by LS.
    - ``updaycnt`` (연속일수) counting convention (consecutive gain days,
     consecutive direction days, etc.) is NOT declared in available source.
    - ``idx`` is an opaque LS-defined paging cursor; pass back verbatim.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1441RequestHeader(BlockRequestHeader):
    """t1441 request header. Inherits the standard LS request header schema."""
    pass


class T1441ResponseHeader(BlockResponseHeader):
    """t1441 response header. Inherits the standard LS response header schema."""
    pass


class T1441InBlock(BaseModel):
    """t1441InBlock — input block for the price-change ranking screen."""

    gubun1: Literal["0", "1", "2"] = Field(
        ...,
        title="구분 (Market division)",
        description="Market division. '0' = all, '1' = KOSPI, '2' = KOSDAQ.",
        examples=["0", "1", "2"],
    )
    gubun2: Literal["0", "1", "2"] = Field(
        ...,
        title="상승하락 (Direction)",
        description="Direction. '0' = gainers (상승률), '1' = losers (하락률), '2' = unchanged (보합).",
        examples=["0", "1", "2"],
    )
    gubun3: Literal["0", "1"] = Field(
        ...,
        title="당일전일 (Day flag)",
        description="Day flag. '0' = today (당일), '1' = previous day (전일).",
        examples=["0", "1"],
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
    jc_num2: int = Field(
        default=0,
        title="대상제외2 비트마스크 (Exclusion bitmask 2)",
        description="Secondary target-exclusion bitmask. Bit-position semantics not declared in available source; consume as returned by LS. 0 means no exclusion.",
        examples=[0],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description="Exchange division. 'K' = KRX, 'N' = NXT, 'U' = unified.",
        examples=["K", "N", "U"],
    )


class T1441Request(BaseModel):
    """t1441 request envelope."""

    header: T1441RequestHeader = T1441RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1441",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1441InBlock"], T1441InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1441"
    )


class T1441OutBlock(BaseModel):
    """t1441OutBlock — continuation block (paging cursor)."""

    idx: int = Field(
        ...,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor for the next paged request. 0 when no further rows are available.",
        examples=[0],
    )


class T1441OutBlock1(BaseModel):
    """t1441OutBlock1 — per-issue price-change ranking row."""

    hname: str = Field(
        ...,
        title="한글명 (Korean name)",
        description="Korean issue name as reported by LS.",
        examples=["삼성전자"],
    )
    price: int = Field(
        ...,
        title="현재가 (Current price)",
        description="Current price. Decimal scale not declared in available source; consume as returned by LS.",
        examples=[55300],
    )
    sign: str = Field(
        ...,
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention: '1' = upper limit (상한), '2' = up (상승), '3' = unchanged (보합), '4' = lower limit (하한), '5' = down (하락).",
        examples=["1", "2", "3", "4", "5"],
    )
    change: int = Field(
        ...,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of price change versus previous close. Sign convention not declared in available source; pair with ``sign`` for direction.",
        examples=[1500, 0],
    )
    diff: float = Field(
        ...,
        title="등락율(%) (Change percent)",
        description="Percent change versus previous close.",
        examples=[2.78, -1.45, 0.0],
    )
    volume: int = Field(
        ...,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[15000000],
    )
    offerrem1: int = Field(
        ...,
        title="매도잔량 (Best ask quantity)",
        description="Quantity at the best ask price.",
        examples=[5000, 0],
    )
    offerho1: int = Field(
        ...,
        title="매도호가 (Best ask price)",
        description="Best ask price. Decimal scale not declared in available source.",
        examples=[55400, 0],
    )
    bidho1: int = Field(
        ...,
        title="매수호가 (Best bid price)",
        description="Best bid price. Decimal scale not declared in available source.",
        examples=[55300, 0],
    )
    bidrem1: int = Field(
        ...,
        title="매수잔량 (Best bid quantity)",
        description="Quantity at the best bid price.",
        examples=[3500, 0],
    )
    updaycnt: int = Field(
        ...,
        title="연속일수 (Consecutive days)",
        description="Number of consecutive days. Counting convention (e.g., consecutive gain days vs. consecutive same-direction days) not declared in available source.",
        examples=[1, 5],
    )
    jnildiff: float = Field(
        ...,
        title="전일등락율 (Previous-day change percent)",
        description="Previous trading day's percent change versus its prior close.",
        examples=[1.20, -0.55, 0.0],
    )
    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    open: int = Field(
        ...,
        title="시가 (Open price)",
        description="Session opening price.",
        examples=[54000],
    )
    high: int = Field(
        ...,
        title="고가 (High price)",
        description="Session high price.",
        examples=[55800],
    )
    low: int = Field(
        ...,
        title="저가 (Low price)",
        description="Session low price.",
        examples=[53700],
    )
    voldiff: float = Field(
        ...,
        title="거래량대비율 (Volume ratio)",
        description="Volume ratio expressed as a percentage. Comparison baseline (vs. previous day, vs. average, etc.) not declared in available source.",
        examples=[125.5, 0.0],
    )
    value: int = Field(
        ...,
        title="거래대금 (Trading value)",
        description="Cumulative trading value for the session. Currency unit and scale not declared in available source; consume as returned by LS.",
        examples=[850000],
    )
    total: int = Field(
        ...,
        title="시가총액 (Market capitalization)",
        description="Market capitalization. Currency unit and scale not declared in available source; consume as returned by LS.",
        examples=[3300000],
    )
    ex_shcode: str = Field(
        default="",
        title="거래소별단축코드 (Exchange-specific short code)",
        description="Exchange-resolved short code echoed for the issue. Format and semantics not declared in available source.",
        examples=[""],
    )


class T1441Response(BaseModel):
    """t1441 response envelope."""

    header: Optional[T1441ResponseHeader]
    cont_block: Optional[T1441OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1441OutBlock1] = Field(
        default_factory=list,
        title="등락율상위 종목 리스트 (Price-change ranking rows)",
        description="List of issues ranked by intraday price-change percentage.",
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
