"""Pydantic models for LS Securities OpenAPI t1631 (Korean Stock Program Trading Comprehensive Query).

t1631 returns Korean stock program trading data:
    - Eight scalar order/remainder aggregates from the (sell vs buy) ×
      (arbitrage vs non-arbitrage) × (unfilled-remaining vs ordered)
      breakdown documented in the LS spec — exposed via
      ``T1631Response.summary_block``.
    - An Object Array of program trading rows (sell / buy / net quantity
      and amount per row) — exposed via ``T1631Response.block``. The LS
      public spec does not document the meaning or ordering of the rows.

Unlike t1636, this TR has **no IDXCTS continuation** — a single response
covers either the same-day query (``dgubun='1'``) or the period query
(``dgubun='2'``) over ``[sdate, edate]``.

Field descriptions follow LS official spec wording verbatim. Korean
field labels (한글명) are appended in parentheses so AI chatbots can map
between English descriptions and Korean LS documentation. Inferred
formulas, units, or row semantics that are not in the LS public spec
are intentionally omitted — consume every value as reported by LS.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1631RequestHeader(BlockRequestHeader):
    """t1631 request header. Inherits the standard LS request header schema."""
    pass


class T1631ResponseHeader(BlockResponseHeader):
    """t1631 response header. Carries continuation flags (``tr_cont`` / ``tr_cont_key``)."""
    pass


class T1631InBlock(BaseModel):
    """t1631InBlock — input block for Korean stock program trading comprehensive query.

    Selects the market (``gubun``: 거래소 vs 코스닥), the date mode
    (``dgubun``: 당일조회 vs 기간조회), the date range (``sdate`` /
    ``edate``, may be left empty for same-day per LS official example),
    and the exchange filter (``exchgubun``).
    """

    gubun: Literal["1", "2"] = Field(
        ...,
        title="구분 (Market division)",
        description=(
            "Market division. '1' = 거래소 (exchange), '2' = 코스닥 (KOSDAQ). "
            "Required. NOTE: t1636 uses a different ``gubun`` encoding for the "
            "same market dimension — do not copy-paste t1636 inputs verbatim."
        ),
        examples=["1", "2"],
    )
    dgubun: Literal["1", "2"] = Field(
        ...,
        title="일자구분 (Date mode)",
        description=(
            "Date selection mode. '1' = 당일조회 (same-day query — sdate/edate "
            "may be left empty per LS official example), '2' = 기간조회 "
            "(period query over [sdate, edate]). Required."
        ),
        examples=["1", "2"],
    )
    sdate: str = Field(
        default="",
        title="시작일자 (Start date)",
        description=(
            "Period start date. Length 8. Leave empty when ``dgubun='1'`` "
            "(same-day query) — LS official example sends an empty string "
            "for the same-day case despite the spec marking this as Required."
        ),
        examples=[""],
    )
    edate: str = Field(
        default="",
        title="종료일자 (End date)",
        description=(
            "Period end date. Length 8. Leave empty when ``dgubun='1'`` "
            "(same-day query) — LS official example sends an empty string "
            "for the same-day case despite the spec marking this as Required."
        ),
        examples=[""],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange division code. 'K' = KRX, 'N' = NXT, 'U' = 통합 "
            "(unified). Per LS spec, any other value is treated as KRX "
            "server-side. (This client uses 'K' as the default for "
            "convenience — LS spec marks the field as Required.)"
        ),
        examples=["K", "N", "U"],
    )


class T1631Request(BaseModel):
    """t1631 full request envelope (header + body + setup options)."""

    header: T1631RequestHeader = T1631RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1631",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: Dict[Literal["t1631InBlock"], T1631InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1631",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class T1631OutBlock(BaseModel):
    """t1631OutBlock — eight scalar order/remainder aggregates.

    Documented in the LS spec as the (sell vs buy) × (arbitrage vs
    non-arbitrage) × (unfilled-remaining vs ordered) breakdown:

    - ``cdhrem`` / ``bdhrem``: 매도차익미체결잔량 / 매도비차익미체결잔량.
    - ``tcdrem`` / ``tbdrem``: 매도차익주문수량 / 매도비차익주문수량.
    - ``cshrem`` / ``bshrem``: 매수차익미체결잔량 / 매수비차익미체결잔량.
    - ``tcsrem`` / ``tbsrem``: 매수차익주문수량 / 매수비차익주문수량.

    Unlike t1636, this block is **not** a continuation marker — it carries
    actual data and is always present on a successful response.
    """

    cdhrem: int = Field(
        default=0,
        title="매도차익미체결잔량 (Sell-arbitrage unfilled remaining quantity)",
        description="Sell-arbitrage unfilled remaining quantity. Length 8.",
        examples=[0],
    )
    bdhrem: int = Field(
        default=0,
        title="매도비차익미체결잔량 (Sell-non-arbitrage unfilled remaining quantity)",
        description="Sell-non-arbitrage unfilled remaining quantity. Length 8.",
        examples=[2],
    )
    tcdrem: int = Field(
        default=0,
        title="매도차익주문수량 (Sell-arbitrage ordered quantity)",
        description="Sell-arbitrage ordered quantity. Length 8.",
        examples=[0],
    )
    tbdrem: int = Field(
        default=0,
        title="매도비차익주문수량 (Sell-non-arbitrage ordered quantity)",
        description="Sell-non-arbitrage ordered quantity. Length 8.",
        examples=[5],
    )
    cshrem: int = Field(
        default=0,
        title="매수차익미체결잔량 (Buy-arbitrage unfilled remaining quantity)",
        description="Buy-arbitrage unfilled remaining quantity. Length 8.",
        examples=[0],
    )
    bshrem: int = Field(
        default=0,
        title="매수비차익미체결잔량 (Buy-non-arbitrage unfilled remaining quantity)",
        description="Buy-non-arbitrage unfilled remaining quantity. Length 8.",
        examples=[149],
    )
    tcsrem: int = Field(
        default=0,
        title="매수차익주문수량 (Buy-arbitrage ordered quantity)",
        description="Buy-arbitrage ordered quantity. Length 8.",
        examples=[0],
    )
    tbsrem: int = Field(
        default=0,
        title="매수비차익주문수량 (Buy-non-arbitrage ordered quantity)",
        description="Buy-non-arbitrage ordered quantity. Length 8.",
        examples=[251],
    )


class T1631OutBlock1(BaseModel):
    """t1631OutBlock1 — program trading rows.

    Object Array. The LS public spec documents only the per-row field
    schema (sell / buy / net quantity and amount). The meaning of an
    individual row and the ordering of the array are not documented by
    LS — consume the array as reported.
    """

    offervolume: int = Field(
        default=0,
        title="매도수량 (Sell quantity)",
        description="Sell quantity. Length 8.",
        examples=[3, 0],
    )
    offervalue: int = Field(
        default=0,
        title="매도금액 (Sell amount)",
        description=(
            "Sell amount. Length 12. Unit conventions are not documented "
            "in the LS public spec."
        ),
        examples=[479, 1, 480],
    )
    bidvolume: int = Field(
        default=0,
        title="매수수량 (Buy quantity)",
        description="Buy quantity. Length 8.",
        examples=[102, 0],
    )
    bidvalue: int = Field(
        default=0,
        title="매수금액 (Buy amount)",
        description=(
            "Buy amount. Length 12. Unit conventions are not documented "
            "in the LS public spec (see ``offervalue``)."
        ),
        examples=[6919, 1, 6921],
    )
    volume: int = Field(
        default=0,
        title="순매수수량 (Net-buy quantity)",
        description=(
            "Net-buy quantity. Length 8. The LS public spec does not "
            "publish a server-side computation formula — consume the "
            "value as reported."
        ),
        examples=[99, 0],
    )
    value: int = Field(
        default=0,
        title="순매수금액 (Net-buy amount)",
        description=(
            "Net-buy amount. Length 12. The LS public spec does not "
            "publish a server-side computation formula — consume the "
            "value as reported."
        ),
        examples=[6440, 1, 6441],
    )


class T1631Response(BaseModel):
    """t1631 full API response envelope."""

    header: Optional[T1631ResponseHeader] = None
    summary_block: Optional[T1631OutBlock] = Field(
        default=None,
        title="t1631OutBlock (Order/remainder aggregates)",
        description=(
            "Eight scalar aggregates from the (sell vs buy) × (arbitrage "
            "vs non-arbitrage) × (unfilled-remaining vs ordered) breakdown."
        ),
    )
    block: List[T1631OutBlock1] = Field(
        default_factory=list,
        title="t1631OutBlock1 (Program trading rows)",
        description=(
            "Result rows as reported by LS. Row meaning and array ordering "
            "are not documented in the LS public spec."
        ),
    )
    status_code: Optional[int] = Field(default=None, title="HTTP status code")
    rsp_cd: str = ""
    rsp_msg: str = ""
    error_msg: Optional[str] = Field(default=None, title="Error message")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
