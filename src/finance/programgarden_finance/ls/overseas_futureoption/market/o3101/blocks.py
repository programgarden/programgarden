"""Pydantic models for LS Securities OpenAPI o3101 (Overseas futures master list query).

o3101 returns a list of overseas futures/option instrument master records.
Each row describes one listed contract: exchange, underlying, settlement price,
margin requirements, price tick, and trading session times.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Decimal scale, currency unit, multiplier, and tick-value semantics are
      NOT enumerated in the source available to this codebase. Where the
      source uses generic phrasing, the description states
      "consume as returned by LS" or "not declared in available source".
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3101.py``
      (gubun='1') plus neutral placeholder values for instrument fields.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3101RequestHeader(BlockRequestHeader):
    """o3101 request header. Inherits the standard LS request header schema."""
    pass


class O3101ResponseHeader(BlockResponseHeader):
    """o3101 response header. Inherits the standard LS response header schema."""
    pass


class O3101InBlock(BaseModel):
    """o3101InBlock — input block for the overseas futures master list query."""

    gubun: str = Field(
        ...,
        title="Input classification (입력구분)",
        description=(
            "Input classification code. Meaning of specific values not "
            "declared in available source; consume as returned by LS. "
            "Example script uses '1'."
        ),
        examples=["1"],
    )


class O3101Request(BaseModel):
    """o3101 full request envelope (header + body + setup options)."""

    header: O3101RequestHeader = Field(
        O3101RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3101",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["o3101InBlock"], O3101InBlock] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'o3101InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3101"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3101OutBlock(BaseModel):
    """o3101OutBlock — one overseas futures instrument master record.

    Decimal scale, currency unit, multiplier, and tick-value semantics are
    not declared in the source available to this codebase.
    """

    Symbol: str = Field(
        default="",
        title="Symbol code (종목코드)",
        description="LS instrument symbol code for the listed contract.",
        examples=["ESM26", "NQU26"],
    )
    SymbolNm: str = Field(
        default="",
        title="Symbol name (종목명)",
        description="Human-readable instrument name.",
        examples=["E-MINI S&P500 JUN26", "E-MINI NASDAQ JUN26"],
    )
    ApplDate: str = Field(
        default="",
        title="Batch receive date (종목배치수신일) YYYYMMDD",
        description=(
            "Date on which LS received this instrument's master data in batch "
            "(YYYYMMDD format)."
        ),
        examples=["20260101", "20260315"],
    )
    BscGdsCd: str = Field(
        default="",
        title="Underlying product code (기초상품코드)",
        description=(
            "LS code for the underlying product of the contract. "
            "Other LS-defined codes may appear; consume as returned by LS."
        ),
        examples=["ES", "NQ"],
    )
    BscGdsNm: str = Field(
        default="",
        title="Underlying product name (기초상품명)",
        description="Name of the underlying product.",
        examples=["E-MINI S&P500", "E-MINI NASDAQ"],
    )
    ExchCd: str = Field(
        default="",
        title="Exchange code (거래소코드)",
        description=(
            "LS exchange code for the listing venue. "
            "Other LS-defined codes may appear; consume as returned by LS."
        ),
        examples=["CME", "HKEX"],
    )
    ExchNm: str = Field(
        default="",
        title="Exchange name (거래소명)",
        description="Name of the listing exchange.",
        examples=["Chicago Mercantile Exchange", "Hong Kong Exchange"],
    )
    CrncyCd: str = Field(
        default="",
        title="Base currency code (기준통화코드)",
        description=(
            "ISO-style currency code for the contract's settlement currency. "
            "Consume as returned by LS."
        ),
        examples=["USD", "HKD"],
    )
    NotaCd: str = Field(
        default="",
        title="Numeral system code (진법구분코드)",
        description=(
            "Numeral system classification code used for price quotation. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["10"],
    )
    UntPrc: str = Field(
        default="",
        title="Tick price (호가단위가격)",
        description=(
            "Minimum price tick size as a string. Decimal scale and currency "
            "unit not declared in available source."
        ),
        examples=["0.25", "0.5"],
    )
    MnChgAmt: str = Field(
        default="",
        title="Minimum price change amount (최소가격변동금액)",
        description=(
            "Monetary value of one minimum price movement. "
            "Multiplier semantics not declared in available source."
        ),
        examples=["12.5", "5.0"],
    )
    RgltFctr: str = Field(
        default="",
        title="Price adjustment factor (가격조정계수)",
        description=(
            "Price adjustment factor used by LS. Semantics not declared in "
            "available source; consume as returned by LS."
        ),
        examples=["1.0"],
    )
    CtrtPrAmt: str = Field(
        default="",
        title="Per-contract amount (계약당금액)",
        description=(
            "Notional value per contract as a string. Multiplier semantics "
            "not declared in available source."
        ),
        examples=["50.0", "20.0"],
    )
    GdsCd: str = Field(
        default="",
        title="Product type code (상품구분코드)",
        description=(
            "LS product-type classification code. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["F"],
    )
    LstngYr: str = Field(
        default="",
        title="Contract year (월물(년))",
        description="Year component of the contract month (e.g., '2026').",
        examples=["2026", "2025"],
    )
    LstngM: str = Field(
        default="",
        title="Contract month (월물(월))",
        description=(
            "Month component of the contract month as returned by LS "
            "(e.g., '06' for June). Consume as returned by LS."
        ),
        examples=["06", "09"],
    )
    EcPrc: str = Field(
        default="",
        title="Settlement price (정산가격)",
        description=(
            "Previous settlement price as a string. Decimal scale not "
            "declared in available source."
        ),
        examples=["5800.25", "21300.0"],
    )
    DlStrtTm: str = Field(
        default="",
        title="Trading start time HHMMSS (거래시작시간)",
        description=(
            "Daily trading session start time in HHMMSS format. "
            "Time zone not declared in available source; consume as returned by LS."
        ),
        examples=["170000", "090000"],
    )
    DlEndTm: str = Field(
        default="",
        title="Trading end time HHMMSS (거래종료시간)",
        description=(
            "Daily trading session end time in HHMMSS format. "
            "Time zone not declared in available source; consume as returned by LS."
        ),
        examples=["160000", "153000"],
    )
    DlPsblCd: str = Field(
        default="",
        title="Tradeable classification code (거래가능구분코드)",
        description=(
            "Code indicating whether the contract is currently tradeable. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["1", "0"],
    )
    MgnCltCd: str = Field(
        default="",
        title="Margin collection classification code (증거금징수구분코드)",
        description=(
            "Margin collection type code. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["1"],
    )
    OpngMgn: str = Field(
        default="",
        title="Initial margin (개시증거금)",
        description=(
            "Initial margin requirement as a string. "
            "Currency unit and scale not declared in available source."
        ),
        examples=["12000.0", "5000.0"],
    )
    MntncMgn: str = Field(
        default="",
        title="Maintenance margin (유지증거금)",
        description=(
            "Maintenance margin requirement as a string. "
            "Currency unit and scale not declared in available source."
        ),
        examples=["11000.0", "4500.0"],
    )
    OpngMgnR: str = Field(
        default="",
        title="Initial margin rate (개시증거금율)",
        description=(
            "Initial margin rate as a string. "
            "Scale not declared in available source."
        ),
        examples=["0.05", "0.1"],
    )
    MntncMgnR: str = Field(
        default="",
        title="Maintenance margin rate (유지증거금율)",
        description=(
            "Maintenance margin rate as a string. "
            "Scale not declared in available source."
        ),
        examples=["0.04", "0.09"],
    )
    DotGb: int = Field(
        default=0,
        title="Effective decimal places (유효소수점자리수)",
        description="Number of effective decimal places LS uses for price display.",
        examples=[2, 4],
    )


class O3101Response(BaseModel):
    """o3101 full response envelope."""

    header: Optional[O3101ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: List[O3101OutBlock] = Field(
        ...,
        title="Instrument master list (출력 블록 리스트)",
        description=(
            "List of overseas futures instrument master records. "
            "Time ordering: consume as returned by LS."
        ),
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP status code (HTTP 상태 코드)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="LS response code (응답 코드)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="LS response message (응답 메시지)",
        description="LS response message text.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="Error message (오류 메시지)",
        description="Error message when an exception or HTTP error occurred. None on success.",
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        """Raw underlying response object (for debugging)."""
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
