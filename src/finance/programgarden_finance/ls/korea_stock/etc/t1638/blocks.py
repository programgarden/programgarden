"""Pydantic models for LS Securities OpenAPI t1638 (Domestic Stock per-issue order-book balance / pre-announcement ranking).

t1638 returns a ranking of issues by the requested sort criterion: market
cap weight, net buy/sell open quantity (top/bottom), buy/sell open
quantity, or buy/sell pre-announced quantity (사전공시수량). Used for
pre-market and intraday order-flow ranking analysis.

Response carries:
    - ``OutBlock`` (``block``) — list of ranking rows. Each row carries the
      issue's price, change, market-cap weight, net buy/sell open quantity,
      buy/sell open quantity, and buy/sell pre-announced quantity.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale of price / market-cap fields and time ordering of rows
      are NOT declared in the source available to this codebase; consume
      as returned by LS.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1638.py``.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1638RequestHeader(BlockRequestHeader):
    """t1638 request header. Inherits the standard LS request header schema."""
    pass


class T1638ResponseHeader(BlockResponseHeader):
    """t1638 response header. Inherits the standard LS response header schema."""
    pass


class T1638InBlock(BaseModel):
    """t1638InBlock — input block for the per-issue order-book balance / pre-announcement ranking query."""

    gubun1: Literal["1", "2"] = Field(
        ...,
        title="구분 (Market type)",
        description="Market type. '1' = KOSPI (코스피), '2' = KOSDAQ (코스닥).",
        examples=["1", "2"],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Short code)",
        description=(
            "6-digit Korean stock short code. Empty string when ranking "
            "across the whole market (default)."
        ),
        examples=[""],
    )
    gubun2: Literal["1", "2", "3", "4", "5", "6", "7"] = Field(
        ...,
        title="정렬 (Sort criterion)",
        description=(
            "Sort criterion. '1' = market-cap weight (시가총액비중), '2' = "
            "net buy open quantity top (순매수잔량 상위), '3' = net buy "
            "open quantity bottom (순매수잔량 하위), '4' = buy open "
            "quantity (매수잔량), '5' = buy pre-announced quantity "
            "(매수공시수량), '6' = sell open quantity (매도잔량), '7' = "
            "sell pre-announced quantity (매도공시수량)."
        ),
        examples=["1", "2", "4"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange division code. 'K' = KRX (한국거래소), 'N' = NXT "
            "(넥스트레이드), 'U' = unified (통합)."
        ),
        examples=["K", "N", "U"],
    )


class T1638OutBlock(BaseModel):
    """t1638OutBlock — per-issue ranking row.

    Decimal scale of price / market-cap fields and time ordering of rows
    are NOT declared in the source available to this codebase; consume as
    returned by LS. Net buy/sell open quantity (``obuyvol``) can take any
    sign — positive, negative, and zero examples preserved.
    """

    rank: int = Field(
        default=0,
        title="순위 (Rank)",
        description="Rank within the result set per the requested sort criterion (1-based).",
        examples=[1, 50],
    )
    hname: str = Field(
        default="",
        title="한글명 (Issue name)",
        description="Korean issue name.",
        examples=["삼성전자"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description="Current price. Decimal scale not declared in available source.",
        examples=[78000],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Change direction)",
        description=(
            "Change direction code vs. previous close. '1' = upper limit "
            "(상한), '2' = up (상승), '3' = unchanged (보합), '4' = lower "
            "limit (하한), '5' = down (하락)."
        ),
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Change amount)",
        description="Change amount vs. previous close.",
        examples=[500, -500, 0],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Change ratio)",
        description="Change ratio (%) vs. previous close. Decimal scale not declared in available source.",
        examples=[0.65, -0.65, 0.0],
    )
    sigatotrt: float = Field(
        default=0.0,
        title="시총비중 (Market-cap weight)",
        description="Market-cap weight (%) for the issue within its market. Decimal scale not declared in available source.",
        examples=[20.50, 1.00, 0.0],
    )
    obuyvol: int = Field(
        default=0,
        title="순매수잔량 (Net buy open quantity)",
        description=(
            "Net buy open quantity (순매수잔량 = 매수잔량 - 매도잔량). "
            "Sign convention preserved as returned by LS."
        ),
        examples=[10000, -10000, 0],
    )
    buyrem: int = Field(
        default=0,
        title="매수잔량 (Buy open quantity)",
        description="Buy-side open order quantity (매수잔량) currently on the book.",
        examples=[100000],
    )
    psgvolume: int = Field(
        default=0,
        title="매수공시수량 (Buy pre-announced quantity)",
        description="Buy-side pre-announced order quantity (사전공시수량 매수).",
        examples=[50000],
    )
    sellrem: int = Field(
        default=0,
        title="매도잔량 (Sell open quantity)",
        description="Sell-side open order quantity (매도잔량) currently on the book.",
        examples=[100000],
    )
    pdgvolume: int = Field(
        default=0,
        title="매도공시수량 (Sell pre-announced quantity)",
        description="Sell-side pre-announced order quantity (사전공시수량 매도).",
        examples=[50000],
    )
    sigatot: int = Field(
        default=0,
        title="시가총액 (Market capitalization)",
        description=(
            "Market capitalization for the issue. Decimal scale and "
            "currency unit not declared in available source; consume as "
            "returned by LS."
        ),
        examples=[500000000000000],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )


class T1638Request(BaseModel):
    """t1638 request envelope."""

    header: T1638RequestHeader = T1638RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1638",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1638",
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1638Response(BaseModel):
    """t1638 response envelope."""

    header: Optional[T1638ResponseHeader] = None
    block: list[T1638OutBlock] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1638RequestHeader",
    "T1638ResponseHeader",
    "T1638InBlock",
    "T1638OutBlock",
    "T1638Request",
    "T1638Response",
]
