"""Pydantic models for LS Securities OpenAPI t1471 (시간대별호가잔량추이 / per-bin bid/ask quantity history).

t1471 returns a per-time-bin history of best bid/ask price + quantity, the
buy/sell delta, the totals across the visible book, and a derived buy ratio
for a Korean stock symbol. ``gubun`` controls bin granularity (00 = 30s, 01
= 1m, 02 = 2m, 03 = 3m, ...). Pagination is via ``time``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``gubun`` covers '00' (30s) and '01'..'NN' (N minutes), but the full
      enum upper bound is NOT declared in the available source; treat as
      open-ended LS-defined codes.
    - ``msrate`` formula (buy / (buy + sell)? buy / total?) is NOT declared
      in the available source.
    - ``totsun`` (순매수 — net buy) sign convention is NOT declared.
    - ``time`` is an opaque LS-defined continuation token.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1471RequestHeader(BlockRequestHeader):
    """t1471 request header. Inherits the standard LS request header schema."""
    pass


class T1471ResponseHeader(BlockResponseHeader):
    """t1471 response header. Inherits the standard LS response header schema."""
    pass


class T1471InBlock(BaseModel):
    """t1471InBlock — input block for the per-bin bid/ask quantity history query."""

    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    gubun: str = Field(
        default="01",
        title="분구분 (Bin granularity code)",
        description=(
            "Bin granularity code. '00' = 30 seconds, '01' = 1 minute, "
            "'02' = 2 minutes, '03' = 3 minutes, ... Full enum upper bound "
            "not declared in available source; treat as open-ended LS-"
            "defined codes."
        ),
        examples=["00", "01", "05"],
    )
    time: str = Field(
        default=" ",
        title="시간 (Continuation cursor)",
        description="Continuation cursor for paged queries. Default ' ' (space) on first request; pass back ``time`` from the previous response. Treat as opaque LS-defined token.",
        examples=[" "],
    )
    cnt: str = Field(
        default="010",
        title="자료개수 (Row count)",
        description="Number of rows to request. Range 1~500 per LS source. Encoded as zero-padded string.",
        examples=["010", "500"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description="Exchange division. 'K' = KRX, 'N' = NXT, 'U' = unified.",
        examples=["K", "N", "U"],
    )


class T1471Request(BaseModel):
    """t1471 request envelope."""

    header: T1471RequestHeader = T1471RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1471",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1471InBlock"], T1471InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1471"
    )


class T1471OutBlock(BaseModel):
    """t1471OutBlock — continuation block (cursor + current-price snapshot)."""

    time: str = Field(
        ...,
        title="시간CTS (Continuation cursor)",
        description="Continuation cursor for the next paged request. Treat as opaque LS-defined token.",
        examples=[""],
    )
    price: int = Field(
        ...,
        title="현재가 (Current price)",
        description="Current price snapshot at response time.",
        examples=[79800],
    )
    sign: str = Field(
        ...,
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention ('1'..'5').",
        examples=["2", "3", "5"],
    )
    change: int = Field(
        ...,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of price change versus previous close.",
        examples=[800, 0],
    )
    diff: float = Field(
        ...,
        title="등락율(%) (Change percent)",
        description="Percent change versus previous close.",
        examples=[1.02, 0.0, -0.5],
    )
    volume: int = Field(
        ...,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[15000000],
    )


class T1471OutBlock1(BaseModel):
    """t1471OutBlock1 — per-time-bin best bid/ask + totals row."""

    time: str = Field(
        ...,
        title="체결시간 (Bin time)",
        description="Bin start time in 'HHMMSS' format. Time ordering of rows not declared in available source.",
        examples=["093000"],
    )
    preoffercha1: int = Field(
        ...,
        title="매도증감 (Best-ask quantity delta)",
        description="Change in best-ask quantity versus the previous bin. Sign convention not declared in available source.",
        examples=[100, 0, -50],
    )
    offerrem1: int = Field(
        ...,
        title="매도우선잔량 (Best-ask quantity)",
        description="Quantity at the best ask price for this bin.",
        examples=[5000],
    )
    offerho1: int = Field(
        ...,
        title="매도우선호가 (Best-ask price)",
        description="Best ask price for this bin.",
        examples=[79900],
    )
    bidho1: int = Field(
        ...,
        title="매수우선호가 (Best-bid price)",
        description="Best bid price for this bin.",
        examples=[79800],
    )
    bidrem1: int = Field(
        ...,
        title="매수우선잔량 (Best-bid quantity)",
        description="Quantity at the best bid price for this bin.",
        examples=[3500],
    )
    prebidcha1: int = Field(
        ...,
        title="매수증감 (Best-bid quantity delta)",
        description="Change in best-bid quantity versus the previous bin. Sign convention not declared in available source.",
        examples=[200, 0, -100],
    )
    totofferrem: int = Field(
        ...,
        title="총매도 (Total ask quantity)",
        description="Aggregate ask-side resting quantity across the visible book at bin time.",
        examples=[1200000],
    )
    totbidrem: int = Field(
        ...,
        title="총매수 (Total bid quantity)",
        description="Aggregate bid-side resting quantity across the visible book at bin time.",
        examples=[980000],
    )
    totsun: int = Field(
        ...,
        title="순매수 (Net resting quantity)",
        description="Net resting-quantity delta (bid minus ask, or as defined by LS). Sign convention not declared in available source.",
        examples=[0, 100000, -50000],
    )
    msrate: float = Field(
        ...,
        title="매수비율 (Buy ratio)",
        description="Derived buy-side ratio. Formula not declared in available source; consume as returned by LS.",
        examples=[0.5, 0.62],
    )
    close: int = Field(
        ...,
        title="종가 (Bin close price)",
        description="Last trade price as of the end of the bin.",
        examples=[79800],
    )


class T1471Response(BaseModel):
    """t1471 response envelope."""

    header: Optional[T1471ResponseHeader]
    cont_block: Optional[T1471OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor + current-price snapshot block.",
    )
    block: List[T1471OutBlock1] = Field(
        default_factory=list,
        title="호가잔량 리스트 (Per-bin orderbook rows)",
        description="List of per-time-bin best bid/ask + totals rows.",
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
