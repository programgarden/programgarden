"""Pydantic models for LS Securities OpenAPI t1665 (Domestic Stock period-wise investor net trading chart).

t1665 returns a time series of net buy/sell quantities and amounts by investor
category (individual / foreign / institutional / their sub-categories) for the
requested market across a date range, plus the matching market index value
per row. The response carries:

    - ``OutBlock`` (``cont_block``) — input echo: market code, market name,
      exchange-mapped industry code.
    - ``OutBlock1`` (``block``) — list of per-period rows, one per business
      day / week / month per ``gubun3``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, sign convention (net buy positive vs.
      net sell positive), and time ordering of ``OutBlock1`` rows are NOT
      declared in the source available to this codebase. Quantity and
      amount fields therefore include positive, negative, and zero
      ``examples`` to reflect that net flows can take any sign.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1665.py``.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1665RequestHeader(BlockRequestHeader):
    """t1665 request header. Inherits the standard LS request header schema."""
    pass


class T1665ResponseHeader(BlockResponseHeader):
    """t1665 response header. Inherits the standard LS response header schema."""
    pass


class T1665InBlock(BaseModel):
    """t1665InBlock — input block for the period-wise investor net trading chart query."""

    market: Literal["1", "2", "3", "4", "5", "6"] = Field(
        ...,
        title="시장구분 (Market type)",
        description=(
            "Market type. '1' = KOSPI (코스피), '2' = KOSPI200 (KP200), "
            "'3' = KOSDAQ (코스닥), '4' = futures (선물), '5' = put options "
            "(풋옵션), '6' = call options (콜옵션)."
        ),
        examples=["1", "2", "3"],
    )
    upcode: str = Field(
        default="",
        title="업종코드 (Industry code)",
        description=(
            "Industry code. Length not declared in available source. Empty "
            "string when not filtering by industry."
        ),
        examples=[""],
    )
    gubun2: Literal["1", "2"] = Field(
        ...,
        title="수치구분 (Value type)",
        description="Value type. '1' = per-period value (수치), '2' = cumulative (누적).",
        examples=["1", "2"],
    )
    gubun3: Literal["1", "2", "3"] = Field(
        ...,
        title="단위구분 (Period unit)",
        description="Period unit. '1' = daily (일), '2' = weekly (주), '3' = monthly (월).",
        examples=["1", "2", "3"],
    )
    from_date: str = Field(
        ...,
        title="시작날짜 (Start date)",
        description="Start date in 'YYYYMMDD' format.",
        examples=["20260201"],
    )
    to_date: str = Field(
        ...,
        title="종료날짜 (End date)",
        description="End date in 'YYYYMMDD' format.",
        examples=["20260228"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange division code. 'K' = KRX (한국거래소), 'N' = NXT "
            "(넥스트레이드), 'U' = unified (통합). Defaults to 'K'."
        ),
        examples=["K", "N", "U"],
    )


class T1665OutBlock(BaseModel):
    """t1665OutBlock — input echo block (market metadata)."""

    mcode: str = Field(
        default="",
        title="시장코드 (Market code)",
        description="Market code echoed back by LS for the requested ``market``.",
        examples=[""],
    )
    mname: str = Field(
        default="",
        title="시장명 (Market name)",
        description="Korean market name echoed back by LS (e.g., '코스피').",
        examples=[""],
    )
    ex_upcode: str = Field(
        default="",
        title="거래소별업종코드 (Exchange-mapped industry code)",
        description="Exchange-mapped industry code echoed back by LS for the request.",
        examples=[""],
    )


class T1665OutBlock1(BaseModel):
    """t1665OutBlock1 — per-period investor net trading row.

    All ``sv_*`` fields are net traded quantities (수량). All ``sa_*`` fields
    are net traded amounts (금액). Sign convention (net buy vs. net sell),
    decimal scale of amounts, and time ordering of rows (ascending vs.
    descending) are NOT declared in the source available to this codebase;
    consume as returned by LS. Net flows can take any sign, hence positive,
    negative, and zero ``examples``.
    """

    date: str = Field(
        default="",
        title="일자 (Date)",
        description="Period date in 'YYYYMMDD' format. Time ordering not declared in available source.",
        examples=["20260201"],
    )
    sv_08: int = Field(
        default=0,
        title="개인수량 (Individual net quantity)",
        description="Net traded quantity by individual investors (개인) for the period.",
        examples=[100000, -100000, 0],
    )
    sv_17: int = Field(
        default=0,
        title="외인계수량 (Foreign aggregate net quantity)",
        description=(
            "Net traded quantity by foreign investors aggregate "
            "(외인계 = 등록 외국인 + 미등록 외국인) for the period."
        ),
        examples=[50000, -50000, 0],
    )
    sv_18: int = Field(
        default=0,
        title="기관계수량 (Institutional aggregate net quantity)",
        description="Net traded quantity by institutional investors aggregate (기관계) for the period.",
        examples=[80000, -80000, 0],
    )
    sv_01: int = Field(
        default=0,
        title="증권수량 (Securities firm net quantity)",
        description="Net traded quantity by securities firms (증권) for the period.",
        examples=[10000, -10000, 0],
    )
    sv_03: int = Field(
        default=0,
        title="투신수량 (Investment trust net quantity)",
        description="Net traded quantity by investment trusts (투신) for the period.",
        examples=[10000, -10000, 0],
    )
    sv_04: int = Field(
        default=0,
        title="은행수량 (Bank net quantity)",
        description="Net traded quantity by banks (은행) for the period.",
        examples=[5000, -5000, 0],
    )
    sv_02: int = Field(
        default=0,
        title="보험수량 (Insurance net quantity)",
        description="Net traded quantity by insurance companies (보험) for the period.",
        examples=[5000, -5000, 0],
    )
    sv_05: int = Field(
        default=0,
        title="종금수량 (Merchant bank net quantity)",
        description="Net traded quantity by merchant banks (종금) for the period.",
        examples=[1000, -1000, 0],
    )
    sv_06: int = Field(
        default=0,
        title="기금수량 (Pension/fund net quantity)",
        description="Net traded quantity by pensions and government funds (기금) for the period.",
        examples=[20000, -20000, 0],
    )
    sv_07: int = Field(
        default=0,
        title="기타수량 (Other net quantity)",
        description="Net traded quantity by 'other' investor category (기타) for the period.",
        examples=[1000, -1000, 0],
    )
    sv_00: int = Field(
        default=0,
        title="사모펀드수량 (Private fund net quantity)",
        description="Net traded quantity by private funds (사모펀드) for the period.",
        examples=[5000, -5000, 0],
    )
    sv_09: int = Field(
        default=0,
        title="등록외국인수량 (Registered foreign net quantity)",
        description="Net traded quantity by registered foreign investors (등록 외국인) for the period.",
        examples=[40000, -40000, 0],
    )
    sv_10: int = Field(
        default=0,
        title="미등록외국인수량 (Unregistered foreign net quantity)",
        description="Net traded quantity by unregistered foreign investors (미등록 외국인) for the period.",
        examples=[10000, -10000, 0],
    )
    sv_11: int = Field(
        default=0,
        title="국가수량 (Government net quantity)",
        description="Net traded quantity by the government (국가) for the period.",
        examples=[1000, -1000, 0],
    )
    sv_99: int = Field(
        default=0,
        title="기타계수량 (Other aggregate net quantity)",
        description="Net traded quantity by 'other aggregate' (기타계 = 기타 + 국가) for the period.",
        examples=[2000, -2000, 0],
    )
    sa_08: int = Field(
        default=0,
        title="개인금액 (Individual net amount)",
        description=(
            "Net traded amount by individual investors (개인) for the period. "
            "Decimal scale not declared in available source; consume as returned by LS."
        ),
        examples=[1000000000, -1000000000, 0],
    )
    sa_17: int = Field(
        default=0,
        title="외인계금액 (Foreign aggregate net amount)",
        description=(
            "Net traded amount by foreign investors aggregate (외인계 = "
            "등록 외국인 + 미등록 외국인) for the period. Decimal scale not "
            "declared in available source."
        ),
        examples=[500000000, -500000000, 0],
    )
    sa_18: int = Field(
        default=0,
        title="기관계금액 (Institutional aggregate net amount)",
        description=(
            "Net traded amount by institutional investors aggregate (기관계) "
            "for the period. Decimal scale not declared in available source."
        ),
        examples=[800000000, -800000000, 0],
    )
    sa_01: int = Field(
        default=0,
        title="증권금액 (Securities firm net amount)",
        description="Net traded amount by securities firms (증권) for the period.",
        examples=[100000000, -100000000, 0],
    )
    sa_03: int = Field(
        default=0,
        title="투신금액 (Investment trust net amount)",
        description="Net traded amount by investment trusts (투신) for the period.",
        examples=[100000000, -100000000, 0],
    )
    sa_04: int = Field(
        default=0,
        title="은행금액 (Bank net amount)",
        description="Net traded amount by banks (은행) for the period.",
        examples=[50000000, -50000000, 0],
    )
    sa_02: int = Field(
        default=0,
        title="보험금액 (Insurance net amount)",
        description="Net traded amount by insurance companies (보험) for the period.",
        examples=[50000000, -50000000, 0],
    )
    sa_05: int = Field(
        default=0,
        title="종금금액 (Merchant bank net amount)",
        description="Net traded amount by merchant banks (종금) for the period.",
        examples=[10000000, -10000000, 0],
    )
    sa_06: int = Field(
        default=0,
        title="기금금액 (Pension/fund net amount)",
        description="Net traded amount by pensions and government funds (기금) for the period.",
        examples=[200000000, -200000000, 0],
    )
    sa_07: int = Field(
        default=0,
        title="기타금액 (Other net amount)",
        description="Net traded amount by 'other' investor category (기타) for the period.",
        examples=[10000000, -10000000, 0],
    )
    sa_00: int = Field(
        default=0,
        title="사모펀드금액 (Private fund net amount)",
        description="Net traded amount by private funds (사모펀드) for the period.",
        examples=[50000000, -50000000, 0],
    )
    sa_09: int = Field(
        default=0,
        title="등록외국인금액 (Registered foreign net amount)",
        description="Net traded amount by registered foreign investors (등록 외국인) for the period.",
        examples=[400000000, -400000000, 0],
    )
    sa_10: int = Field(
        default=0,
        title="미등록외국인금액 (Unregistered foreign net amount)",
        description="Net traded amount by unregistered foreign investors (미등록 외국인) for the period.",
        examples=[100000000, -100000000, 0],
    )
    sa_11: int = Field(
        default=0,
        title="국가금액 (Government net amount)",
        description="Net traded amount by the government (국가) for the period.",
        examples=[10000000, -10000000, 0],
    )
    sa_99: int = Field(
        default=0,
        title="기타계금액 (Other aggregate net amount)",
        description="Net traded amount by 'other aggregate' (기타계 = 기타 + 국가) for the period.",
        examples=[20000000, -20000000, 0],
    )
    jisu: float = Field(
        default=0.0,
        title="시장지수 (Market index)",
        description=(
            "Market index value at the period close. Decimal scale not "
            "declared in available source; consume as returned by LS."
        ),
        examples=[2700.50, 850.25, 0.0],
    )


class T1665Request(BaseModel):
    """t1665 request envelope.

    Attributes:
        header: Request header (``tr_cd='t1665'``).
        body: InBlock payload keyed by ``'t1665InBlock'``.
        options: Rate-limit / setup options.
    """

    header: T1665RequestHeader = T1665RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1665",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1665",
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1665Response(BaseModel):
    """t1665 response envelope."""

    header: Optional[T1665ResponseHeader] = None
    cont_block: Optional[T1665OutBlock] = None
    block: list[T1665OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1665RequestHeader",
    "T1665ResponseHeader",
    "T1665InBlock",
    "T1665OutBlock",
    "T1665OutBlock1",
    "T1665Request",
    "T1665Response",
]
