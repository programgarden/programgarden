"""Pydantic models for LS Securities OpenAPI t1449 (가격대별매매비중조회 / Trading-share by price-level).

t1449 returns two response payloads for a single Korean stock symbol:

    - ``T1449OutBlock`` (single object): a current-price summary block
      carrying current price, previous-day direction code (LS-mapped enum),
      previous-day delta, percent change, day total volume, and aggregated
      buy / sell conclusion volumes.
    - ``T1449OutBlock1`` (object array): one row per price level of the
      "trading-share by price-level" distribution. Each row carries a
      conclusion price, previous-day direction code, previous-day delta,
      a per-row percent change (``tickdiff``), a per-row conclusion volume
      (``cvolume``), a per-row trading-share value (``diff``, "비중"), and
      buy / sell conclusion volumes plus the buy ratio (``msdiff``) for
      the row.

t1449 is a single-shot TR — the LS spec available to this codebase exposes
no continuation cursor (``cts_*`` / ``idx``) and no row-count input — so
``occurs_req`` is intentionally not implemented.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
``feedback_tr_field_metadata``):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``sign`` enum mapping IS declared by LS for t1449 in both
      ``t1449OutBlock`` and ``t1449OutBlock1``
      (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락); both descriptions
      embed the mapping.
    - ``dategb`` enum mapping IS declared by LS
      (1=당일 / 2=전일 / 3=당일+전일).
    - The following are NOT declared in the source available to this
      codebase and must NOT be asserted in descriptions:
        * Currency unit of price / change fields.
        * Sign convention of ``change`` (positive when up vs always
          non-negative magnitude).
        * Row ordering of ``T1449OutBlock1`` (price ascending /
          descending / trade-time / other).
        * The exact denominator used for ``T1449OutBlock1.diff`` ("비중",
          per-row trading share) — whether row volume divided by
          day-total volume, or another normalization.
        * The exact denominator used for ``T1449OutBlock1.msdiff``
          (매수비율) — whether ``msvolume / cvolume``,
          ``msvolume / (msvolume + mdvolume)``, or another formula.
        * Whether ``T1449OutBlock1.tickdiff`` ("등락율") and
          ``T1449OutBlock.diff`` ("등락율") share the same reference base.
        * The relationship between ``T1449OutBlock`` summary aggregates
          and the rows in ``T1449OutBlock1`` when ``dategb=3`` mixes
          today and previous-day data.
    - ``diff`` and ``msdiff`` and ``tickdiff`` (LS scale 6.2) are
      serialized as JSON strings by LS in example responses (e.g.,
      ``"0.68"``, ``"100.00"``, ``"-0.41"``); Pydantic coerces to float.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1449RequestHeader(BlockRequestHeader):
    """t1449 request header. Inherits the standard LS request header schema."""
    pass


class T1449ResponseHeader(BlockResponseHeader):
    """t1449 response header. Inherits the standard LS response header schema."""
    pass


class T1449InBlock(BaseModel):
    """t1449InBlock — input block for the trading-share by price-level query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code. Length 6.",
        examples=["005930", "000660", "001200"],
    )
    dategb: Literal["1", "2", "3"] = Field(
        ...,
        title="일자구분 (Date scope)",
        description=(
            "Date scope selector for the trading-share distribution. "
            "Length 1. "
            "'1' = today (당일), "
            "'2' = previous trading day (전일), "
            "'3' = today + previous trading day combined (당일+전일). "
            "Required."
        ),
        examples=["1", "2", "3"],
    )


class T1449Request(BaseModel):
    """t1449 request envelope."""

    header: T1449RequestHeader = T1449RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1449",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1449InBlock"], T1449InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1449"
    )


class T1449OutBlock(BaseModel):
    """t1449OutBlock — single current-price summary block.

    Carries the current-price quote and day-aggregate trading volumes for
    the queried symbol. Whether the aggregates reflect ``dategb=1`` /
    ``dategb=2`` / ``dategb=3`` window is not formally declared in
    available LS source — consume as returned by LS.
    """

    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description=(
            "Current price for the symbol as returned by LS. Decimal "
            "scale and currency unit not declared in available source. "
            "Length 8."
        ),
        examples=[0, 3685, 87000],
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
            "'5' = down (하락). Enum mapping is declared by LS for t1449."
        ),
        examples=["1", "2", "3", "4", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description=(
            "Magnitude of change versus previous close. Sign convention "
            "is not declared in available LS source — consume as returned "
            "by LS. Length 8."
        ),
        examples=[0, 25, -25],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Percent change)",
        description=(
            "Percent change versus previous close in % (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '0.68' or "
            "'-1.20'); Pydantic auto-coerces to float."
        ),
        examples=[0.0, 0.68, -1.20],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Trading volume)",
        description=(
            "Day-aggregate trading volume in shares as returned by LS. "
            "Length 12."
        ),
        examples=[0, 322192, 1500000],
    )
    msvolume: int = Field(
        default=0,
        title="매수체결량 (Buy conclusion volume)",
        description=(
            "Day-aggregate buy-side conclusion volume in shares as "
            "returned by LS. Length 12."
        ),
        examples=[0, 195607, 800000],
    )
    mdvolume: int = Field(
        default=0,
        title="매도체결량 (Sell conclusion volume)",
        description=(
            "Day-aggregate sell-side conclusion volume in shares as "
            "returned by LS. Length 12."
        ),
        examples=[0, 120522, 700000],
    )


class T1449OutBlock1(BaseModel):
    """t1449OutBlock1 — one trading-share row per price level.

    Row ordering of ``T1449OutBlock1`` rows is not declared in available
    LS source (price-ascending / price-descending / trade-time / other);
    consume as returned by LS.
    """

    price: int = Field(
        default=0,
        title="체결가 (Conclusion price)",
        description=(
            "Conclusion price for the row as returned by LS. Decimal "
            "scale and currency unit not declared in available source. "
            "Length 8."
        ),
        examples=[0, 3645, 3750],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Direction code versus previous close for the row. Length 1. "
            "'1' = upper limit (상한), "
            "'2' = up (상승), "
            "'3' = unchanged (보합), "
            "'4' = lower limit (하한), "
            "'5' = down (하락). Enum mapping is declared by LS for t1449."
        ),
        examples=["1", "2", "3", "4", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description=(
            "Magnitude of change versus previous close for the row. Sign "
            "convention is not declared in available LS source — consume "
            "as returned by LS. Length 8."
        ),
        examples=[0, 90, -15],
    )
    tickdiff: float = Field(
        default=0.0,
        title="등락율 (Per-row percent change)",
        description=(
            "Per-row percent change as returned by LS in the ``tickdiff`` "
            "field (LS label '등락율', scale 6.2). Reference base is not "
            "formally declared in available LS source — consume as "
            "returned by LS. LS may serialize this value as a string "
            "(e.g., '2.46' or '-0.41'); Pydantic auto-coerces to float."
        ),
        examples=[0.0, 2.46, -0.41],
    )
    cvolume: int = Field(
        default=0,
        title="체결수량 (Per-row conclusion volume)",
        description=(
            "Conclusion volume for the row in shares as returned by LS. "
            "Length 12."
        ),
        examples=[0, 147, 22107],
    )
    diff: float = Field(
        default=0.0,
        title="비중 (Per-row trading share)",
        description=(
            "Per-row trading-share value as returned by LS in the "
            "``diff`` field (LS label '비중', scale 6.2). The exact "
            "denominator (e.g., row volume divided by day-total volume "
            "or another normalization) is not formally declared in "
            "available LS source — consume as returned by LS. Note that "
            "``T1449OutBlock.diff`` carries '등락율' (percent change "
            "versus previous close) while ``T1449OutBlock1.diff`` "
            "carries '비중' (trading share); the two share a JSON key "
            "but represent different metrics. LS may serialize this "
            "value as a string (e.g., '6.86'); Pydantic auto-coerces "
            "to float."
        ),
        examples=[0.0, 0.05, 6.86],
    )
    mdvolume: int = Field(
        default=0,
        title="매도체결량 (Per-row sell conclusion volume)",
        description=(
            "Sell-side conclusion volume for the row in shares as "
            "returned by LS. Length 12."
        ),
        examples=[0, 147, 1200],
    )
    msvolume: int = Field(
        default=0,
        title="매수체결량 (Per-row buy conclusion volume)",
        description=(
            "Buy-side conclusion volume for the row in shares as "
            "returned by LS. Length 12."
        ),
        examples=[0, 22107, 800],
    )
    msdiff: float = Field(
        default=0.0,
        title="매수비율 (Per-row buy ratio)",
        description=(
            "Per-row buy ratio as returned by LS in the ``msdiff`` "
            "field (LS label '매수비율', scale 6.2). The exact "
            "denominator (e.g., ``msvolume / cvolume``, "
            "``msvolume / (msvolume + mdvolume)``, or another formula) "
            "is not formally declared in available LS source — consume "
            "as returned by LS. LS may serialize this value as a string "
            "(e.g., '100.00' or '0.00'); Pydantic auto-coerces to float."
        ),
        examples=[0.0, 100.00, 50.0],
    )


class T1449Response(BaseModel):
    """t1449 response envelope."""

    header: Optional[T1449ResponseHeader]
    out_block: Optional[T1449OutBlock] = Field(
        None,
        title="현재가 요약 블록 (Current-price summary block)",
        description=(
            "Single current-price summary block (current price, previous-"
            "day delta, percent change, and day-aggregate volumes)."
        ),
    )
    block: List[T1449OutBlock1] = Field(
        default_factory=list,
        title="가격대별 매매비중 리스트 (Per-price-level trading-share rows)",
        description=(
            "List of per-price-level trading-share rows. Row ordering "
            "not declared in available LS source — consume as returned "
            "by LS."
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
