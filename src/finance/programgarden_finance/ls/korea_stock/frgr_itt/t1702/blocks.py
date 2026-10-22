"""Pydantic models for LS Securities OpenAPI t1702 (per-issue foreign / institutional trading trend / 외인기관종목별동향).

t1702 returns a per-day time series of investor-category net trading
(or buy / sell, depending on ``msmdgb``) for a specific Korean-market
stock. The response carries one ``OutBlock1`` (no ``OutBlock``) listing
per-day rows with the daily close + previous-close direction, change,
ratio, cumulative volume + value, and per-investor-category amount /
quantity / unit-price columns (``tjj0000``…``tjj0018``).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and time ordering of ``OutBlock1``
      rows are NOT declared in the source available to this codebase;
      consume as returned by LS. Investor-category column semantics
      (amount / quantity / unit-price) depend on ``InBlock.volvalgb``;
      the same field name carries different units across modes.
    - ``sign`` direction codes follow the standard LS stock convention
      ('1' = 상한 / '2' = 상승 / '3' = 보합 / '4' = 하한 / '5' = 하락).
    - Sign convention on per-investor columns (net buy positive vs.
      net sell positive) is NOT declared in the available source —
      [+, -, 0] examples preserve symmetry.
    - ``msmdgb='0'`` net mode aggregates buy minus sell; ``'1'`` =
      buy-only; ``'2'`` = sell-only. Source enum preserved verbatim.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1702.py``
      (``shcode='005930'`` = Samsung Electronics).
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1702RequestHeader(BlockRequestHeader):
    """t1702 request header. Inherits the standard LS request header schema."""
    pass


class T1702ResponseHeader(BlockResponseHeader):
    """t1702 response header. Inherits the standard LS response header schema."""
    pass


class T1702InBlock(BaseModel):
    """t1702InBlock — input block for per-issue foreign / institutional trading-trend query."""

    shcode: str = Field(
        default="",
        title="종목코드 (Issue code)",
        description="6-digit Korean stock short code (e.g., '005930' for Samsung Electronics).",
        examples=["005930"],
    )
    fromdt: str = Field(
        default="",
        title="시작일자 (Start date)",
        description="Range start date in 'YYYYMMDD' format.",
        examples=["20260201"],
    )
    todt: str = Field(
        default="",
        title="종료일자 (End date)",
        description="Range end date in 'YYYYMMDD' format.",
        examples=["20260228"],
    )
    volvalgb: Literal["0", "1", "2"] = Field(
        ...,
        title="금액수량구분 (Amount / quantity mode)",
        description=(
            "Amount / quantity mode. '0' = amount (금액), '1' = quantity "
            "(수량), '2' = unit price (단가). Same source enum determines "
            "the unit of every per-investor column on ``OutBlock1``."
        ),
        examples=["0", "1", "2"],
    )
    msmdgb: Literal["0", "1", "2"] = Field(
        ...,
        title="매수매도구분 (Buy / sell mode)",
        description=(
            "Buy / sell mode. '0' = net buy (순매수 = buy − sell), '1' = "
            "buy-only (매수), '2' = sell-only (매도). Source enum verbatim."
        ),
        examples=["0", "1", "2"],
    )
    gubun: Literal["0", "1"] = Field(
        ...,
        title="누적구분 (Daily / cumulative mode)",
        description="Aggregation mode. '0' = daily (일간), '1' = cumulative (누적).",
        examples=["0", "1"],
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


class T1702OutBlock1(BaseModel):
    """t1702OutBlock1 — per-day investor-category trading-trend row.

    Decimal scale, currency unit, and time ordering of rows are NOT
    declared in the source available to this codebase. The unit of
    every per-investor column (``tjj0000``…``tjj0018``) is determined
    by ``InBlock.volvalgb``: amount (currency) when '0', quantity
    (shares) when '1', unit price when '2'.
    """

    date: str = Field(
        default="",
        title="일자 (Date)",
        description="Trade date in 'YYYYMMDD' format.",
        examples=["20260228"],
    )
    close: int = Field(
        default=0,
        title="종가 (Closing price)",
        description="Closing price for the trade date. Decimal scale not declared in available source.",
        examples=[78500],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-close direction)",
        description=(
            "Direction code vs. previous close. '1' = upper limit (상한), "
            "'2' = up (상승), '3' = unchanged (보합), '4' = lower limit "
            "(하한), '5' = down (하락)."
        ),
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Change vs. previous close)",
        description="Closing-price change vs. previous trade-date close. Sign convention not declared in available source.",
        examples=[200, -150, 0],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Change ratio)",
        description="Closing-price change ratio (%) vs. previous trade-date close.",
        examples=[0.26, -0.19, 0.0],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the trade date.",
        examples=[3500000],
    )
    tjj0000: int = Field(
        default=0,
        title="사모펀드 (Private fund)",
        description=(
            "Private-fund (사모펀드) net column for the trade date. Unit "
            "depends on ``volvalgb`` (amount / quantity / unit price). "
            "Sign convention not declared in available source."
        ),
        examples=[100000, -50000, 0],
    )
    tjj0001: int = Field(
        default=0,
        title="증권 (Securities firms)",
        description="Securities-firm (증권) net column. Unit per ``volvalgb``; sign convention not declared.",
        examples=[150000, -80000, 0],
    )
    tjj0002: int = Field(
        default=0,
        title="보험 (Insurance)",
        description="Insurance-company (보험) net column.",
        examples=[120000, -60000, 0],
    )
    tjj0003: int = Field(
        default=0,
        title="투신 (Investment trust)",
        description="Investment-trust (투신) net column.",
        examples=[200000, -100000, 0],
    )
    tjj0004: int = Field(
        default=0,
        title="은행 (Bank)",
        description="Bank (은행) net column.",
        examples=[80000, -40000, 0],
    )
    tjj0005: int = Field(
        default=0,
        title="종금 (Merchant bank)",
        description="Merchant-bank (종금) net column.",
        examples=[10000, -5000, 0],
    )
    tjj0006: int = Field(
        default=0,
        title="기금 (Pension / fund)",
        description="Pension / fund (기금) net column.",
        examples=[150000, -75000, 0],
    )
    tjj0007: int = Field(
        default=0,
        title="기타법인 (Other corporate)",
        description="Other-corporate (기타법인) net column.",
        examples=[70000, -35000, 0],
    )
    tjj0008: int = Field(
        default=0,
        title="개인 (Retail / individual)",
        description="Retail / individual (개인) net column.",
        examples=[500000, -250000, 0],
    )
    tjj0009: int = Field(
        default=0,
        title="등록외국인 (Registered foreign investor)",
        description="Registered foreign-investor (등록외국인) net column.",
        examples=[400000, -200000, 0],
    )
    tjj0010: int = Field(
        default=0,
        title="미등록외국인 (Unregistered foreign investor)",
        description="Unregistered foreign-investor (미등록외국인) net column.",
        examples=[50000, -25000, 0],
    )
    tjj0011: int = Field(
        default=0,
        title="국가외 (State / others)",
        description="State / others (국가외) net column.",
        examples=[30000, -15000, 0],
    )
    tjj0018: int = Field(
        default=0,
        title="기관 (Institutional aggregate)",
        description=(
            "Institutional aggregate (기관) net column — sum of "
            "investment-trust, bank, insurance, merchant-bank, pension, "
            "and similar institutional categories per LS convention."
        ),
        examples=[800000, -400000, 0],
    )
    tjj0016: int = Field(
        default=0,
        title="외인계(등록+미등록) (Foreign aggregate)",
        description=(
            "Foreign aggregate (외인계) — registered foreign + unregistered "
            "foreign per the LS source label."
        ),
        examples=[450000, -225000, 0],
    )
    tjj0017: int = Field(
        default=0,
        title="기타계(기타+국가) (Others aggregate)",
        description=(
            "Others aggregate (기타계) — other-corporate + state per the "
            "LS source label."
        ),
        examples=[100000, -50000, 0],
    )
    value: int = Field(
        default=0,
        title="거래대금 (Trade value)",
        description="Cumulative traded value (price × volume) for the trade date. Decimal scale and currency unit not declared in available source.",
        examples=[275000000000],
    )


class T1702Request(BaseModel):
    """t1702 request envelope."""

    header: T1702RequestHeader = T1702RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1702",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1702",
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1702Response(BaseModel):
    """t1702 response envelope."""

    header: Optional[T1702ResponseHeader] = None
    block: list[T1702OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1702RequestHeader",
    "T1702ResponseHeader",
    "T1702InBlock",
    "T1702OutBlock1",
    "T1702Request",
    "T1702Response",
]
